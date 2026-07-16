"""evaluator.py – Unified Analyst + Verifier in a single LLM call.

Replaces the two-call pattern (analyst.py → verifier.py) with one
structured Gemini request that returns support_score,
contradiction_score, and verifier_status simultaneously.

This halves the number of LLM calls per claim-candidate pair.
"""

from __future__ import annotations

import os
from typing import Any, Literal

from pydantic import BaseModel, Field

from GraphEngine.utils.gemini_client import generate_json_sync, generate_json_async


# ---------------------------------------------------------------------------
# Combined output schema
# ---------------------------------------------------------------------------

class CombinedEvaluation(BaseModel):
    support_score: float = Field(
        ge=0.0,
        le=1.0,
        description="How strongly Claim B supports or agrees with Claim A (0 = none, 1 = strong).",
    )
    contradiction_score: float = Field(
        ge=0.0,
        le=1.0,
        description="How strongly Claim B contradicts or disagrees with Claim A (0 = none, 1 = strong).",
    )
    verifier_status: Literal["CONFIRMED", "SCOPE_MISMATCH", "REJECTED"] = Field(
        description=(
            "CONFIRMED – same scope and logically compatible. "
            "SCOPE_MISMATCH – different populations, methods, or contexts. "
            "REJECTED – directly logically incompatible."
        ),
    )


# Fallback returned when the LLM call fails entirely.
_NEUTRAL: dict[str, Any] = {
    "support_score": 0.5,
    "contradiction_score": 0.5,
    "verifier_status": "SCOPE_MISMATCH",
}

_PROMPT_TEMPLATE = """\
Evaluate the semantic and logical relationship between these two research claims.

CLAIM A (Reference):
{claim_a}

CLAIM B (Candidate):
{claim_b}

Provide ALL of the following in your JSON response:

1. support_score (float 0.0–1.0): How much does Claim B support or agree with Claim A?
2. contradiction_score (float 0.0–1.0): How much does Claim B contradict or disagree with Claim A?
3. verifier_status (string): One of —
   - "CONFIRMED"      → the claims address the same phenomenon with compatible scope.
   - "SCOPE_MISMATCH" → the claims address different populations, methods, or contexts.
   - "REJECTED"       → the claims are directly logically incompatible.

Return a single JSON object with exactly these three fields.\
"""


def evaluate(
    chunk_a: str,
    chunk_b: str,
    meta_a: dict[str, Any] | None = None,
    meta_b: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Score and verify two research claims in one LLM call.

    Replaces the separate ``analyze()`` + ``verify()`` calls with a single
    structured Gemini request, halving per-candidate LLM cost.

    Args:
        chunk_a: Text from document A (draft claim or chunk).
        chunk_b: Text from document B (paper candidate chunk).
        meta_a:  Optional metadata for chunk_a (doc_id, section_name, …).
        meta_b:  Optional metadata for chunk_b.

    Returns:
        Dict with keys:
            support_score        – float in [0, 1]
            contradiction_score  – float in [0, 1]
            verifier_status      – "CONFIRMED" | "SCOPE_MISMATCH" | "REJECTED"
    """
    if not os.getenv("GEMINI_API_KEY"):
        print("[EVALUATOR] GEMINI_API_KEY not set. Returning neutral evaluation.")
        return dict(_NEUTRAL)

    prompt = _PROMPT_TEMPLATE.format(
        claim_a=chunk_a[:500],
        claim_b=chunk_b[:500],
    )

    parsed = generate_json_sync(
        prompt,
        CombinedEvaluation,
        label="EVALUATOR",
        temperature=0.3,
    )

    if not parsed:
        print("[EVALUATOR] All retries exhausted. Using neutral evaluation.")
        return dict(_NEUTRAL)

    try:
        support = float(parsed.get("support_score", 0.5))
        contradiction = float(parsed.get("contradiction_score", 0.5))
        status = str(parsed.get("verifier_status", "SCOPE_MISMATCH")).upper()

        # Clamp scores to valid range
        support = max(0.0, min(1.0, support))
        contradiction = max(0.0, min(1.0, contradiction))

        # Validate verifier_status
        valid_statuses = ("CONFIRMED", "SCOPE_MISMATCH", "REJECTED")
        if status not in valid_statuses:
            print(f"[EVALUATOR] Unknown verifier_status '{status}'. Defaulting to SCOPE_MISMATCH.")
            status = "SCOPE_MISMATCH"

        return {
            "support_score": support,
            "contradiction_score": contradiction,
            "verifier_status": status,
        }

    except (TypeError, ValueError) as exc:
        print(f"[EVALUATOR] Invalid values in parsed response: {exc}. Using neutral evaluation.")
        return dict(_NEUTRAL)

async def evaluate_async(
    chunk_a: str,
    chunk_b: str,
    meta_a: dict[str, Any] | None = None,
    meta_b: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Async version of evaluate() — calls Gemini directly without run_in_executor.

    Preferred over the sync variant when called from an async context (e.g.
    inside asyncio.gather) because it never blocks an OS thread.

    Returns the same dict shape as evaluate():
        support_score        – float in [0, 1]
        contradiction_score  – float in [0, 1]
        verifier_status      – "CONFIRMED" | "SCOPE_MISMATCH" | "REJECTED"
    """
    if not os.getenv("GEMINI_API_KEY"):
        print("[EVALUATOR] GEMINI_API_KEY not set. Returning neutral evaluation.")
        return dict(_NEUTRAL)

    prompt = _PROMPT_TEMPLATE.format(
        claim_a=chunk_a[:500],
        claim_b=chunk_b[:500],
    )

    parsed = await generate_json_async(
        prompt,
        CombinedEvaluation,
        label="EVALUATOR",
        temperature=0.3,
    )

    if not parsed:
        print("[EVALUATOR] All retries exhausted. Using neutral evaluation.")
        return dict(_NEUTRAL)

    try:
        support = float(parsed.get("support_score", 0.5))
        contradiction = float(parsed.get("contradiction_score", 0.5))
        status = str(parsed.get("verifier_status", "SCOPE_MISMATCH")).upper()

        support = max(0.0, min(1.0, support))
        contradiction = max(0.0, min(1.0, contradiction))

        valid_statuses = ("CONFIRMED", "SCOPE_MISMATCH", "REJECTED")
        if status not in valid_statuses:
            print(f"[EVALUATOR] Unknown verifier_status '{status}'. Defaulting to SCOPE_MISMATCH.")
            status = "SCOPE_MISMATCH"

        return {
            "support_score": support,
            "contradiction_score": contradiction,
            "verifier_status": status,
        }

    except (TypeError, ValueError) as exc:
        print(f"[EVALUATOR] Invalid values in parsed response: {exc}. Using neutral evaluation.")
        return dict(_NEUTRAL)
