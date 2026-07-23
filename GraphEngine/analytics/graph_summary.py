"""Graph summary/statistics helpers."""

from __future__ import annotations

import networkx as nx


def graph_summary(graph: nx.DiGraph) -> dict:
    """Return a compact summary of graph semantics and size."""
    total_nodes = graph.number_of_nodes()
    total_edges = graph.number_of_edges()

    contradiction_count = 0
    low_confidence_count = 0
    verifier_mismatch_count = 0
    confidences = []
    degrees = dict(graph.degree())
    isolated_claim_count = 0

    for _, _, data in graph.edges(data=True):
        confidences.append(float(data.get("confidence", 0.0) or 0.0))
        if data.get("relation_type") == "CONTRADICT":
            contradiction_count += 1
        if data.get("confidence_state") == "LOW_CONFIDENCE":
            low_confidence_count += 1
        if data.get("verifier_state") == "SCOPE_MISMATCH":
            verifier_mismatch_count += 1

    for node_id, attrs in graph.nodes(data=True):
        if attrs.get("node_type") == "claim" and degrees.get(node_id, 0) == 0:
            isolated_claim_count += 1

    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
    average_node_degree = sum(degrees.values()) / len(degrees) if degrees else 0.0
    contradiction_density = contradiction_count / total_edges if total_edges else 0.0
    low_confidence_density = low_confidence_count / total_edges if total_edges else 0.0
    verifier_mismatch_density = verifier_mismatch_count / total_edges if total_edges else 0.0

    try:
        connectivity = nx.is_weakly_connected(graph) if total_nodes > 0 else False
    except nx.NetworkXPointlessConcept:
        connectivity = False

    cluster_count = nx.number_weakly_connected_components(graph) if total_nodes > 0 else 0

    return {
        "total_nodes": total_nodes,
        "total_edges": total_edges,
        "contradiction_count": contradiction_count,
        "low_confidence_count": low_confidence_count,
        "verifier_mismatch_count": verifier_mismatch_count,
        "average_confidence": avg_confidence,
        "contradiction_density": contradiction_density,
        "low_confidence_density": low_confidence_density,
        "verifier_mismatch_density": verifier_mismatch_density,
        "average_node_degree": average_node_degree,
        "graph_connectivity": connectivity,
        "cluster_count": cluster_count,
        "isolated_claim_count": isolated_claim_count,
    }
