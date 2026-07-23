"""Heuristic reliability / trust scoring for claims and papers."""

from __future__ import annotations

from collections import Counter, defaultdict

import networkx as nx


def compute_claim_reliability(graph: nx.DiGraph, claim_id: str) -> float:
    """Return a heuristic reliability score in [0, 1] for a claim."""
    incident = list(graph.in_edges(claim_id, data=True)) + list(graph.out_edges(claim_id, data=True))
    if not incident:
        return 0.5

    confidence_values = []
    penalties = 0.0
    for _, _, data in incident:
        confidence_values.append(float(data.get("confidence", 0.0) or 0.0))
        if data.get("relation_type") == "CONTRADICT":
            penalties += 0.15
        if data.get("confidence_state") == "LOW_CONFIDENCE":
            penalties += 0.1
        if data.get("verifier_state") == "REJECTED":
            penalties += 0.2
        if data.get("verifier_state") == "SCOPE_MISMATCH":
            penalties += 0.1

    avg_confidence = sum(confidence_values) / len(confidence_values)
    score = avg_confidence - penalties / max(1, len(incident))
    return max(0.0, min(1.0, score))


def compute_paper_trust_score(graph: nx.DiGraph, paper_id: str) -> float:
    """Aggregate trust score for a paper/node using incident edge semantics."""
    incidents = []
    incidents.extend(list(graph.in_edges(paper_id, data=True)))
    incidents.extend(list(graph.out_edges(paper_id, data=True)))

    if not incidents:
        return 0.5

    reliability_scores = []
    for source, target, data in incidents:
        other = source if target == paper_id else target
        reliability_scores.append(compute_claim_reliability(graph, other))

    # Penalize trust for inconsistent neighborhoods
    contradiction_count = sum(1 for _, _, d in incidents if d.get("relation_type") == "CONTRADICT")
    verifier_failures = sum(1 for _, _, d in incidents if d.get("verifier_state") in {"REJECTED", "SCOPE_MISMATCH"})
    low_conf_count = sum(1 for _, _, d in incidents if d.get("confidence_state") == "LOW_CONFIDENCE")

    base = sum(reliability_scores) / len(reliability_scores)
    penalty = (contradiction_count * 0.05) + (verifier_failures * 0.08) + (low_conf_count * 0.03)
    return max(0.0, min(1.0, base - penalty))
