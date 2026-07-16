"""Reusable traversal and filtering utilities for the semantic graph."""

from __future__ import annotations

from typing import Iterable

import networkx as nx


def filter_edges(
    graph: nx.DiGraph,
    relation_type: str | None = None,
    confidence_state: str | None = None,
    verifier_state: str | None = None,
) -> list[dict]:
    """Return edges matching the provided semantic filters."""
    matches: list[dict] = []
    for source, target, data in graph.edges(data=True):
        if relation_type and data.get("relation_type") != relation_type:
            continue
        if confidence_state and data.get("confidence_state") != confidence_state:
            continue
        if verifier_state and data.get("verifier_state") != verifier_state:
            continue
        matches.append({"source_id": source, "target_id": target, **data})
    return matches


def get_high_confidence_contradictions(graph: nx.DiGraph) -> list[dict]:
    return filter_edges(
        graph,
        relation_type="CONTRADICT",
        confidence_state="HIGH_CONFIDENCE",
    )


def get_low_confidence_edges(graph: nx.DiGraph) -> list[dict]:
    return filter_edges(graph, confidence_state="LOW_CONFIDENCE")


def get_scope_mismatches_for_paper(graph: nx.DiGraph, paper_id: str | None = None) -> list[dict]:
    edges = filter_edges(graph, verifier_state="SCOPE_MISMATCH")
    if paper_id is None:
        return edges
    return [edge for edge in edges if paper_id in (edge.get("source_id", ""), edge.get("target_id", ""))]


def find_review_required_claims(graph: nx.DiGraph) -> list[str]:
    claims: set[str] = set()
    for source, target, data in graph.edges(data=True):
        if data.get("confidence_state") == "REVIEW_REQUIRED":
            claims.add(source)
            claims.add(target)
    return sorted(claims)


def find_claim_neighbors(graph: nx.DiGraph, claim_id: str, edge_filters: dict | None = None) -> list[dict]:
    """Return inbound and outbound neighbors for a claim with optional semantic filters."""
    edge_filters = edge_filters or {}
    neighbors: list[dict] = []

    for source, target, data in graph.in_edges(claim_id, data=True):
        if _matches_filters(data, edge_filters):
            neighbors.append({"source_id": source, "target_id": target, **data})

    for source, target, data in graph.out_edges(claim_id, data=True):
        if _matches_filters(data, edge_filters):
            neighbors.append({"source_id": source, "target_id": target, **data})

    return neighbors


def _matches_filters(data: dict, edge_filters: dict) -> bool:
    relation_type = edge_filters.get("relation_type")
    confidence_state = edge_filters.get("confidence_state")
    verifier_state = edge_filters.get("verifier_state")

    if relation_type and data.get("relation_type") != relation_type:
        return False
    if confidence_state and data.get("confidence_state") != confidence_state:
        return False
    if verifier_state and data.get("verifier_state") != verifier_state:
        return False
    return True
