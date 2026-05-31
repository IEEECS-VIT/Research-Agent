# analyst.py
import os
from typing import Any

from pydantic import BaseModel, Field

from GraphEngine.utils.gemini_client import generate_json_sync


class AnalystScores(BaseModel):
    support_score: float = Field(ge=0.0, le=1.0)
    contradiction_score: float = Field(ge=0.0, le=1.0)


_NEUTRAL = {"support_score": 0.5, "contradiction_score": 0.5}


def analyze(
    chunk_a: str,
    chunk_b: str,
    meta_a: dict[str, Any] | None = None,
    meta_b: dict[str, Any] | None = None,
) -> dict[str, float]:
    """
    Analyse two text chunks for support and contradiction signals.

    Uses Gemini with structured output to score semantic alignment.

    Args:
        chunk_a: Text from document A (e.g. draft claim).
        chunk_b: Text from document B (e.g. matching paper claim).
        meta_a:  Metadata for chunk_a: doc_id, section_name, source_type, etc.
        meta_b:  Metadata for chunk_b.

    Returns:
        Dict with:
            support_score        – float in [0, 1]
            contradiction_score  – float in [0, 1]
    """
    if not os.getenv("GEMINI_API_KEY"):
        print("[ANALYST] GEMINI_API_KEY not set. Returning neutral scores.")
        return dict(_NEUTRAL)

    prompt = f"""Analyze the semantic relationship between these two claims:

CLAIM A (Reference):
{chunk_a[:500]}

CLAIM B (Candidate):
{chunk_b[:500]}

Score the relationship on two dimensions:
1. support_score: How much does B support or agree with A? (0 = no support, 1 = strong support)
2. contradiction_score: How much does B contradict or disagree with A? (0 = no contradiction, 1 = strong contradiction)

Return a JSON object with exactly these two fields as floats between 0.0 and 1.0."""

    parsed = generate_json_sync(
        prompt,
        AnalystScores,
        label="ANALYST",
        temperature=0.3,
    )

    if not parsed:
        print("[ANALYST] All retries exhausted. Using neutral scores.")
        return dict(_NEUTRAL)

    try:
        support = float(parsed.get("support_score", 0.5))
        contradiction = float(parsed.get("contradiction_score", 0.5))
        support = max(0.0, min(1.0, support))
        contradiction = max(0.0, min(1.0, contradiction))
        return {
            "support_score": support,
            "contradiction_score": contradiction,
        }
    except (TypeError, ValueError) as e:
        print(f"[ANALYST] Invalid score values: {e}. Using neutral scores.")
        return dict(_NEUTRAL)
