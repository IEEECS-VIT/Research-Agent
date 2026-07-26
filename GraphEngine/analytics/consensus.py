"""Consensus and instability analytics over the semantic graph."""

from __future__ import annotations

from collections import Counter, defaultdict

import networkx as nx

from GraphEngine.analytics.reliability import compute_claim_reliability, compute_paper_trust_score
from GraphEngine.analytics.traversal import find_review_required_claims


def find_consensus_papers(graph: nx.DiGraph, threshold: float = 0.7) -> list[dict]:
    """Return papers/nodes that exceed a simple trust threshold."""
    candidates = []
    for node_id, attrs in graph.nodes(data=True):
        node_type = attrs.get("node_type")
        if node_type == "paper" or str(node_id).startswith("paper"):
            score = compute_paper_trust_score(graph, node_id)
            if score >= threshold:
                candidates.append({"paper_id": node_id, "trust_score": score})
    return sorted(candidates, key=lambda item: item["trust_score"], reverse=True)


def find_unstable_claims(graph: nx.DiGraph, threshold: float = 0.55) -> list[dict]:
    """Return claims with low reliability or review-required state."""
    unstable = []
    review_required = set(find_review_required_claims(graph))

    for node_id, attrs in graph.nodes(data=True):
        if attrs.get("node_type") == "claim" or node_id in review_required:
            reliability = compute_claim_reliability(graph, node_id)
            if reliability < threshold or node_id in review_required:
                unstable.append({"claim_id": node_id, "reliability": reliability})

    return sorted(unstable, key=lambda item: item["reliability"])


def consensus_breakdown(graph: nx.DiGraph) -> dict[str, int]:
    """Count relation types as a simple consensus proxy."""
    counts = Counter()
    for _, _, data in graph.edges(data=True):
        counts[data.get("relation_type", "MIXED")] += 1
    return dict(counts)
