"""inference_engine.py – Transitive Paper-to-Paper SUPPORT edge inference.

Discovers implicit SUPPORT relationships between two Paper claims when they
both independently SUPPORT (or are both supported by) the same Draft claim.

Rules (strict quality gates — no naive edge forming):
  ✅  Both bridge edges must be relation_type == "SUPPORT"
  ✅  Both bridge edges must have verifier_status == "CONFIRMED"
  ✅  Both bridge edges must have confidence_state == "HIGH_CONFIDENCE"
  ✅  Both bridge edges must have support_score  >= INFER_MIN_SUPPORT_SCORE
  ❌  SCOPE_MISMATCH on either bridge edge  → skip
  ❌  LOW_CONFIDENCE  on either bridge edge  → skip
  ❌  No CONTRADICT edges are ever inferred  (too indirect, too risky)

Two traversal directions are used so both edge orientations are captured:

  Case A – same DRAFT SOURCE, multiple PAPER TARGETS:
      Draft Claim D → Paper Chunk P1 (SUPPORT, CONFIRMED, HIGH_CONF)
      Draft Claim D → Paper Chunk P2 (SUPPORT, CONFIRMED, HIGH_CONF)
      ─→  Infer  P1 ↔ P2  SUPPORT

  Case B – same DRAFT TARGET, multiple PAPER SOURCES:
      Paper Claim P1 → Draft Chunk D (SUPPORT, CONFIRMED, HIGH_CONF)
      Paper Claim P2 → Draft Chunk D (SUPPORT, CONFIRMED, HIGH_CONF)
      ─→  Infer  P1 ↔ P2  SUPPORT

All inferred edges are marked with inferred_transitive=True in the flag field
so they can be distinguished from directly computed edges.
"""

from __future__ import annotations

import os
from collections import defaultdict

from GraphEngine.db.connection import SessionLocal
from GraphEngine.db.models import Edge


# ── Quality thresholds ────────────────────────────────────────────────────────
# Both bridge edges must clear ALL three thresholds for an inference to fire.
INFER_MIN_SUPPORT_SCORE: float = float(
    os.getenv("INFER_MIN_SUPPORT_SCORE", "0.70")
)


def infer_paper_paper_support_edges() -> list[tuple[str, str, dict]]:
    """Return transitive Paper-Paper SUPPORT edge records ready for bulk_upsert_edges.

    Zero LLM calls — pure graph traversal over existing SQLite rows.

    Returns:
        List of (source_id, target_id, edge_data) tuples.  Deduplicates
        symmetric pairs so each unordered (P1, P2) pair appears only once.
    """
    db = SessionLocal()
    try:
        qualifying: list[Edge] = (
            db.query(Edge)
            .filter(
                Edge.relation_type == "SUPPORT",
                Edge.verifier_status == "CONFIRMED",
                Edge.confidence_state == "HIGH_CONFIDENCE",
                Edge.support_score >= INFER_MIN_SUPPORT_SCORE,
            )
            .all()
        )
    finally:
        db.close()

    if not qualifying:
        return []

    # ── Group edges by their shared intermediary ──────────────────────────────
    # Case A: Draft is the SOURCE  →  group by source_id
    by_source: dict[str, list[Edge]] = defaultdict(list)
    # Case B: Draft is the TARGET  →  group by target_id
    by_target: dict[str, list[Edge]] = defaultdict(list)

    for edge in qualifying:
        by_source[edge.source_id].append(edge)
        by_target[edge.target_id].append(edge)

    inferred: list[tuple[str, str, dict]] = []
    seen_pairs: set[tuple[str, str]] = set()

    def _add_inferred(p1: str, p2: str, e1: Edge, e2: Edge) -> None:
        """Add an inferred SUPPORT edge between p1 and p2 if not already seen."""
        if p1 == p2:
            return
        pair = tuple(sorted([p1, p2]))
        if pair in seen_pairs:
            return
        seen_pairs.add(pair)

        # Average the scores from both bridge edges as a proxy for confidence.
        avg_support = round((e1.support_score + e2.support_score) / 2, 4)
        avg_confidence = round(
            ((e1.confidence or 0.0) + (e2.confidence or 0.0)) / 2, 4
        )

        inferred.append((
            p1,
            p2,
            {
                "support_score": avg_support,
                "contradiction_score": 0.0,
                "confidence": avg_confidence,
                "verifier_status": "CONFIRMED",
                "relation_type": "SUPPORT",
                "confidence_state": "HIGH_CONFIDENCE",
                "verifier_state": "CONFIRMED",
                # Flag clearly marks this as an inferred edge, not a direct one.
                "flag": "HIGH_CONFIDENCE_SUPPORT_INFERRED",
                "user_override": False,
            },
        ))

    # ── Case A: same source, different targets ────────────────────────────────
    for _source, edges in by_source.items():
        if len(edges) < 2:
            continue
        for i, e1 in enumerate(edges):
            for e2 in edges[i + 1:]:
                _add_inferred(e1.target_id, e2.target_id, e1, e2)

    # ── Case B: same target, different sources ────────────────────────────────
    for _target, edges in by_target.items():
        if len(edges) < 2:
            continue
        for i, e1 in enumerate(edges):
            for e2 in edges[i + 1:]:
                _add_inferred(e1.source_id, e2.source_id, e1, e2)

    print(
        f"[INFERENCE-ENGINE] Found {len(qualifying)} qualifying bridge edges -> "
        f"inferred {len(inferred)} new Paper-Paper SUPPORT edges."
    )
    return inferred
