"""Reconstruct a temporary NetworkX graph from SQLite edges and nodes.

SQLite remains the source of truth. The reconstructed graph is read-only and
is intended for analytics, traversal, and debugging only.
"""

from __future__ import annotations

from typing import Any

import networkx as nx

from GraphEngine.db.connection import SessionLocal
from GraphEngine.db.models import Node, Edge
from GraphEngine.utils.helpers import infer_semantic_dimensions


def build_graph_from_sqlite() -> nx.DiGraph:
    """Build a directed NetworkX graph from the current SQLite state."""
    graph = nx.DiGraph()
    db = SessionLocal()
    try:
        nodes = db.query(Node).all()
        edges = db.query(Edge).all()

        for node in nodes:
            graph.add_node(
                node.node_id,
                node_type=node.node_type,
                version_id=node.version_id,
            )

        for edge in edges:
            inferred = infer_semantic_dimensions(
                flag=edge.flag,
                confidence=edge.confidence,
                verifier_status=edge.verifier_status,
            )
            relation_type = edge.relation_type or inferred.get("relation_type")
            confidence_state = edge.confidence_state or inferred.get("confidence_state")
            verifier_state = edge.verifier_state or inferred.get("verifier_state")

            graph.add_node(edge.source_id)
            graph.add_node(edge.target_id)
            graph.add_edge(
                edge.source_id,
                edge.target_id,
                source_id=edge.source_id,
                target_id=edge.target_id,
                support_score=edge.support_score,
                contradiction_score=edge.contradiction_score,
                confidence=edge.confidence,
                relation_type=relation_type,
                confidence_state=confidence_state,
                verifier_state=verifier_state,
                verifier_status=edge.verifier_status,
                flag=edge.flag,
                user_override=bool(edge.user_override),
                edge_id=edge.id,
            )

        return graph
    finally:
        db.close()


def graph_to_edge_records(graph: nx.DiGraph) -> list[dict[str, Any]]:
    """Return edge records from a graph as plain dictionaries."""
    records: list[dict[str, Any]] = []
    for source, target, data in graph.edges(data=True):
        record = dict(data)
        record.setdefault("source_id", source)
        record.setdefault("target_id", target)
        records.append(record)
    return records
