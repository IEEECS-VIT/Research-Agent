"""Graph clustering and region discovery helpers."""

from __future__ import annotations

from collections import Counter, defaultdict

import networkx as nx

from GraphEngine.analytics.traversal import get_low_confidence_edges, get_high_confidence_contradictions


def find_contradiction_clusters(graph: nx.DiGraph) -> list[list[str]]:
    """Find connected components in the contradiction subgraph."""
    contradiction_edges = get_high_confidence_contradictions(graph)
    subgraph = nx.Graph()
    for edge in contradiction_edges:
        subgraph.add_edge(edge["source_id"], edge["target_id"])
    return [sorted(list(component)) for component in nx.connected_components(subgraph)]


def find_low_confidence_regions(graph: nx.DiGraph) -> list[dict]:
    """Return groups of nodes that participate in low-confidence edges."""
    regions = defaultdict(set)
    for edge in get_low_confidence_edges(graph):
        regions[edge.get("relation_type", "MIXED")].add(edge["source_id"])
        regions[edge.get("relation_type", "MIXED")].add(edge["target_id"])

    return [
        {"relation_type": relation_type, "nodes": sorted(nodes), "count": len(nodes)}
        for relation_type, nodes in regions.items()
    ]


def find_verifier_failure_patterns(graph: nx.DiGraph) -> dict[str, int]:
    """Count verifier states across all edges."""
    counts = Counter()
    for _, _, data in graph.edges(data=True):
        state = data.get("verifier_state") or data.get("verifier_status") or "UNKNOWN"
        counts[state] += 1
    return dict(counts)
