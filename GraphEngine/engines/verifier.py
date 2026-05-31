# verifier.py
import os
from typing import Any, Literal

from pydantic import BaseModel

from GraphEngine.utils.gemini_client import generate_json_sync

# Valid verifier status values consumed by confidence_engine.py
VERIFIER_STATUSES = ("CONFIRMED", "SCOPE_MISMATCH", "REJECTED")
VerifierStatus = Literal["CONFIRMED", "SCOPE_MISMATCH", "REJECTED"]


class VerifierResult(BaseModel):
    status: VerifierStatus


def verify(
    chunk_a: str,
    chunk_b: str,
    meta_a: dict[str, Any] | None = None,
    meta_b: dict[str, Any] | None = None,
) -> str:
    """
    Verify the logical relationship between two chunks.

    Uses Gemini to check for scope mismatches, methodological differences,
    and direct logical incompatibility.

    Args:
        chunk_a: Text from document A (e.g. draft claim).
        chunk_b: Text from document B (e.g. matching paper claim).
        meta_a:  Metadata for chunk_a (doc_id, section_name, source_type, …).
        meta_b:  Metadata for chunk_b.

    Returns:
        One of: "CONFIRMED", "SCOPE_MISMATCH", "REJECTED"

        - CONFIRMED: The claims address the same phenomenon with compatible scope.
        - SCOPE_MISMATCH: The claims address different populations, methods, or contexts.
        - REJECTED: The claims are logically incompatible (direct contradiction).
    """
    if not os.getenv("GEMINI_API_KEY"):
        print("[VERIFIER] GEMINI_API_KEY not set. Returning SCOPE_MISMATCH.")
        return "SCOPE_MISMATCH"

    if meta_a and meta_b:
        section_a = meta_a.get("section_name", "")
        section_b = meta_b.get("section_name", "")
        if section_a and section_b and section_a != section_b:
            pass

    prompt = f"""Verify the logical relationship between these two research claims:

CLAIM A (Reference):
{chunk_a[:500]}

CLAIM B (Candidate):
{chunk_b[:500]}

Determine if they are logically compatible. Consider:
- Are they addressing the same phenomenon or different ones?
- Do they use compatible methodologies or populations?
- Are there direct logical contradictions?

Return a JSON object with a single field "status" set to one of:
- "CONFIRMED": The claims are logically compatible and addressable together.
- "SCOPE_MISMATCH": The claims address different scopes (populations, methods, contexts).
- "REJECTED": The claims are directly logically incompatible."""

    parsed = generate_json_sync(
        prompt,
        VerifierResult,
        label="VERIFIER",
        temperature=0.3,
    )

    if not parsed:
        print("[VERIFIER] All retries exhausted. Returning SCOPE_MISMATCH for review.")
        return "SCOPE_MISMATCH"

    status = str(parsed.get("status", "SCOPE_MISMATCH")).upper()
    if status in VERIFIER_STATUSES:
        return status

    print(f"[VERIFIER] Unknown status: {status}. Returning SCOPE_MISMATCH.")
    return "SCOPE_MISMATCH"
