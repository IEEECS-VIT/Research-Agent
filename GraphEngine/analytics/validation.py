"""Integrity checks for the semantic-state graph."""

from __future__ import annotations

from collections import Counter

import networkx as nx

from GraphEngine.analytics.graph_builder import build_graph_from_sqlite
from GraphEngine.utils.constants import SUPPORT_THRESHOLD, CONTRADICT_THRESHOLD

VALID_RELATIONS = {"SUPPORT", "CONTRADICT", "MIXED"}
VALID_CONFIDENCE_STATES = {"HIGH_CONFIDENCE", "LOW_CONFIDENCE", "REVIEW_REQUIRED"}
VALID_VERIFIER_STATES = {"CONFIRMED", "REJECTED", "SCOPE_MISMATCH"}


def validate_graph_integrity(graph: nx.DiGraph | None = None) -> dict:
    """Validate semantic state consistency for a reconstructed graph.

    Returns a summary dict with `valid`, `errors`, and `warnings`.
    """
    if graph is None:
        graph = build_graph_from_sqlite()

    errors: list[str] = []
    warnings: list[str] = []

    # Node checks
    seen_nodes = set()
    for node_id, attrs in graph.nodes(data=True):
        if node_id in seen_nodes:
            errors.append(f"duplicate node id: {node_id}")
        seen_nodes.add(node_id)

        if not node_id:
            errors.append("empty node id")

        if attrs.get("node_type") is None:
            warnings.append(f"missing node_type for {node_id}")

    # Edge checks
    seen_pairs = set()
    for source, target, data in graph.edges(data=True):
        pair = (source, target)
        if pair in seen_pairs:
            errors.append(f"duplicate edge: {source}->{target}")
        seen_pairs.add(pair)

        relation = data.get("relation_type")
        confidence_state = data.get("confidence_state")
        verifier_state = data.get("verifier_state")
        confidence = data.get("confidence")
        support = data.get("support_score")
        contradiction = data.get("contradiction_score")

        # Allow legacy rows that only have flag/verifier_status by inferring semantics.
        if relation is None or confidence_state is None or verifier_state is None:
            from GraphEngine.utils.helpers import infer_semantic_dimensions

            inferred = infer_semantic_dimensions(
                flag=data.get("flag"),
                confidence=confidence,
                verifier_status=data.get("verifier_status"),
            )
            relation = relation or inferred.get("relation_type")
            confidence_state = confidence_state or inferred.get("confidence_state")
            verifier_state = verifier_state or inferred.get("verifier_state")

        if relation not in VALID_RELATIONS:
            errors.append(f"invalid relation_type on {source}->{target}: {relation}")
        if confidence_state not in VALID_CONFIDENCE_STATES:
            errors.append(f"invalid confidence_state on {source}->{target}: {confidence_state}")
        if verifier_state not in VALID_VERIFIER_STATES:
            errors.append(f"invalid verifier_state on {source}->{target}: {verifier_state}")

        if confidence is None or not isinstance(confidence, (int, float)):
            errors.append(f"invalid confidence on {source}->{target}: {confidence}")
        elif confidence < 0.0 or confidence > 1.0:
            errors.append(f"confidence out of range on {source}->{target}: {confidence}")

        if support is not None and (support < 0.0 or support > 1.0):
            errors.append(f"support_score out of range on {source}->{target}: {support}")
        if contradiction is not None and (contradiction < 0.0 or contradiction > 1.0):
            errors.append(f"contradiction_score out of range on {source}->{target}: {contradiction}")

        # Semantic consistency rules
        if confidence_state == "LOW_CONFIDENCE" and confidence is not None and confidence > 0.5:
            errors.append(f"LOW_CONFIDENCE with confidence > threshold on {source}->{target}: {confidence}")
        if confidence_state == "HIGH_CONFIDENCE" and confidence is not None and confidence < 0.5:
            errors.append(f"HIGH_CONFIDENCE with confidence < threshold on {source}->{target}: {confidence}")

        # Backward compatibility check: legacy flag should match new semantics when present
        legacy_flag = data.get("flag")
        if legacy_flag:
            if relation == "CONTRADICT" and "CONTRADICT" not in legacy_flag:
                warnings.append(f"legacy flag mismatch on {source}->{target}")
            if relation == "SUPPORT" and "SUPPORT" not in legacy_flag:
                warnings.append(f"legacy flag mismatch on {source}->{target}")

    # Orphaned node check against edge usage
    edge_nodes = set()
    for source, target, _ in graph.edges(data=True):
        edge_nodes.add(source)
        edge_nodes.add(target)

    orphans = [node for node in graph.nodes if node not in edge_nodes]
    if orphans:
        warnings.append(f"orphaned nodes: {len(orphans)}")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }


def validate_sqlite_edge_counts() -> dict:
    """Quick SQLite-level sanity summary for duplicate edge detection."""
    graph = build_graph_from_sqlite()
    counts = Counter((source, target) for source, target in graph.edges())
    duplicates = [pair for pair, count in counts.items() if count > 1]
    return {
        "edge_count": graph.number_of_edges(),
        "duplicate_edges": duplicates,
        "valid": len(duplicates) == 0,
    }
