"""Synthetic semantic claim graph generator for stress tests."""

from __future__ import annotations

import random
import uuid
from dataclasses import dataclass

import networkx as nx

from GraphEngine.utils.helpers import derive_confidence_state


@dataclass
class SyntheticGraphConfig:
    num_claims: int = 50
    num_papers: int = 10
    contradiction_rate: float = 0.2
    low_confidence_rate: float = 0.15
    scope_mismatch_rate: float = 0.1
    cluster_count: int = 3
    seed: int | None = 42


def generate_synthetic_claim_graph(config: SyntheticGraphConfig | None = None) -> nx.DiGraph:
    """Generate a directed synthetic graph for stress testing."""
    config = config or SyntheticGraphConfig()
    rng = random.Random(config.seed)
    graph = nx.DiGraph()

    papers = [f"paper_{uuid.uuid4().hex[:8]}" for _ in range(config.num_papers)]
    claims = [f"claim_{uuid.uuid4().hex[:8]}" for _ in range(config.num_claims)]

    for paper in papers:
        graph.add_node(paper, node_type="paper", version_id="synthetic")
    for claim in claims:
        graph.add_node(claim, node_type="claim", version_id="synthetic")

    # Add a base set of support edges from claims to papers.
    for claim in claims:
        paper = rng.choice(papers)
        confidence = round(rng.uniform(0.55, 0.98), 3)
        confidence_state = derive_confidence_state(confidence)
        graph.add_edge(
            claim,
            paper,
            support_score=round(rng.uniform(0.55, 0.95), 3),
            contradiction_score=round(rng.uniform(0.0, 0.2), 3),
            confidence=confidence,
            relation_type="SUPPORT",
            confidence_state=confidence_state,
            verifier_state="CONFIRMED",
            verifier_status="CONFIRMED",
            flag="HIGH_CONFIDENCE_SUPPORT",
            user_override=False,
        )

    # Contradiction clusters.
    cluster_size = max(2, len(claims) // max(1, config.cluster_count))
    for cluster_start in range(0, len(claims), cluster_size):
        cluster = claims[cluster_start: cluster_start + cluster_size]
        if len(cluster) < 2:
            continue
        for i, source in enumerate(cluster[:-1]):
            target = cluster[i + 1]
            contradiction = rng.random() < config.contradiction_rate
            low_conf = rng.random() < config.low_confidence_rate
            scope_mismatch = rng.random() < config.scope_mismatch_rate
            relation_type = "CONTRADICT" if contradiction else "MIXED"
            confidence = round(rng.uniform(0.15, 0.92), 3)
            verifier_state = "SCOPE_MISMATCH" if scope_mismatch else ("REJECTED" if contradiction else "CONFIRMED")
            confidence_state = derive_confidence_state(confidence, verifier_state)
            if low_conf and confidence <= 0.5:
                confidence_state = "LOW_CONFIDENCE"
            graph.add_edge(
                source,
                target,
                support_score=round(rng.uniform(0.0, 0.8), 3),
                contradiction_score=round(rng.uniform(0.45, 0.98), 3) if contradiction else round(rng.uniform(0.0, 0.35), 3),
                confidence=confidence,
                relation_type=relation_type,
                confidence_state=confidence_state,
                verifier_state=verifier_state,
                verifier_status=verifier_state,
                flag=f"{confidence_state}_{relation_type}",
                user_override=False,
            )

    # A few noisy / redundant edges.
    for _ in range(max(1, config.num_claims // 10)):
        source = rng.choice(claims)
        target = rng.choice(claims + papers)
        if source == target:
            continue
        confidence = round(rng.uniform(0.05, 0.6), 3)
        relation_type = rng.choice(["SUPPORT", "CONTRADICT", "MIXED"])
        verifier_state = rng.choice(["CONFIRMED", "REJECTED", "SCOPE_MISMATCH"])
        confidence_state = derive_confidence_state(confidence, verifier_state)
        graph.add_edge(
            source,
            target,
            support_score=round(rng.uniform(0.0, 1.0), 3),
            contradiction_score=round(rng.uniform(0.0, 1.0), 3),
            confidence=confidence,
            relation_type=relation_type,
            confidence_state=confidence_state,
            verifier_state=verifier_state,
            verifier_status=verifier_state,
            flag=f"{confidence_state}_{relation_type}",
            user_override=False,
        )

    return graph
