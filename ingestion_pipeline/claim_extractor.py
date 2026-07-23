import os
import re
from typing import Literal

from pydantic import BaseModel, Field

from GraphEngine.utils.gemini_client import generate_json_async


class Claim(BaseModel):
    claim_id: str | None = None
    assertion: str
    subject: str | None = None
    context: str | None = None


class DraftClaimItem(BaseModel):
    assertion: str = Field(min_length=15)
    subject: str | None = None


class DraftClaimsResponse(BaseModel):
    claims: list[DraftClaimItem] = Field(min_length=1)


_PAPER_MARKERS = (
    "we found",
    "we show",
    "we demonstrate",
    "suggest",
    "indicate",
    "show that",
    "results show",
    "our results",
    "we propose",
    "we observe",
    "found that",
)

_DRAFT_MARKERS = (
    "however",
    "although",
    "while",
    "despite",
    "limitation",
    "advantage",
    "benefit",
    "drawback",
    "cannot",
    "does not",
    "improves",
    "reduces",
    "suggests",
    "argues",
    "claims",
    "contrary",
    "unlike",
    "compared to",
    "in contrast",
    "on the other hand",
    "critics",
    "problem",
    "issue",
    "evidence",
    "because",
    "therefore",
    "significant",
    " outperform",
    " underperform",
)

_DRAFT_SYSTEM_PROMPT = """You extract atomic, independently verifiable research claims from a user's draft document.

Rules:
- Split the text into separate claims. Do NOT merge supporting and contradicting points into one claim.
- Each claim must be one specific assertion that could be checked against a research paper.
- Include positive claims (support) AND critical or limiting claims (contradictions, caveats, disagreements).
- Preserve numbers, model names, and methodological details when present.
- Skip headings, boilerplate, and vague filler with no checkable content.
- Return 3-12 claims when the section has enough substance; fewer only if the section is very short.
- Write assertions as standalone sentences (no bullet prefixes)."""


def _split_sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[\.\?!])\s+", text.strip()) if s.strip()]


def _dedupe_claims(claims: list[Claim]) -> list[Claim]:
    seen: set[str] = set()
    unique: list[Claim] = []
    for claim in claims:
        key = " ".join(claim.assertion.lower().split())
        if key in seen or len(key) < 20:
            continue
        seen.add(key)
        unique.append(claim)
    return unique


def extract_claims_heuristic(
    chunk_text: str,
    *,
    source_type: Literal["draft", "paper"] = "paper",
    section_name: str | None = None,
) -> list[Claim]:
    """Rule-based claim extraction used for papers and as a draft fallback."""
    if not chunk_text or not chunk_text.strip():
        return []

    markers = _DRAFT_MARKERS if source_type == "draft" else _PAPER_MARKERS
    min_len = 25 if source_type == "draft" else 30
    max_claims = int(os.getenv("MAX_HEURISTIC_CLAIMS_PER_SECTION", "12"))

    sentences = _split_sentences(chunk_text)
    claims: list[Claim] = []

    for sentence in sentences:
        sentence_l = sentence.lower()
        if len(sentence) >= min_len and any(marker in sentence_l for marker in markers):
            claims.append(
                Claim(
                    assertion=sentence.strip(),
                    subject=None,
                    context=f"section: {section_name}" if section_name else None,
                )
            )

    if source_type == "draft" and len(claims) < 3:
        for sentence in sentences:
            if len(sentence) >= min_len:
                claims.append(
                    Claim(
                        assertion=sentence.strip(),
                        subject=None,
                        context=f"section: {section_name}" if section_name else None,
                    )
                )
            if len(claims) >= max_claims:
                break

    if not claims and sentences:
        claims.append(
            Claim(
                assertion=sentences[0].strip(),
                subject=None,
                context=f"section: {section_name}" if section_name else None,
            )
        )

    return _dedupe_claims(claims)[:max_claims]


async def extract_draft_claims_llm(
    section_name: str,
    raw_text: str,
    summary: str | None = None,
) -> list[Claim]:
    """Use Gemini to extract multiple atomic claims from draft section text."""
    text_source = raw_text.strip() or (summary or "").strip()
    if not text_source:
        return []

    snippet = text_source[:8000]
    summary_hint = (summary or "").strip()[:1500]

    prompt = f"""{_DRAFT_SYSTEM_PROMPT}

Section name: {section_name}

Section summary (context only):
{summary_hint or "[none]"}

Section text:
{snippet}

Return JSON with a "claims" array. Each item needs "assertion" and optional "subject"."""

    parsed = await generate_json_async(
        prompt,
        DraftClaimsResponse,
        label="CLAIM-EXTRACTOR",
        temperature=0.2,
    )

    if not parsed:
        print(f"[CLAIM-EXTRACTOR] LLM failed for section `{section_name}`; using heuristic fallback.")
        return extract_claims_heuristic(
            text_source,
            source_type="draft",
            section_name=section_name,
        )

    claims = [
        Claim(
            assertion=item["assertion"].strip(),
            subject=item.get("subject"),
            context=f"section: {section_name}",
        )
        for item in parsed.get("claims", [])
        if isinstance(item, dict) and item.get("assertion")
    ]

    claims = _dedupe_claims(claims)
    if claims:
        print(f"[CLAIM-EXTRACTOR] Section `{section_name}`: extracted {len(claims)} draft claims via LLM.")
        return claims

    return extract_claims_heuristic(text_source, source_type="draft", section_name=section_name)


async def extract_claims_from_section(
    section_name: str,
    raw_text: str,
    summary: str,
    source_type: Literal["draft", "paper"],
) -> list[Claim]:
    """Extract claims from one document section.

    Drafts: LLM on raw text (summary as hint) for multiple atomic claims.
    Papers: lightweight heuristics on section summary.
    """
    if source_type == "draft":
        if not os.getenv("GEMINI_API_KEY"):
            print("[CLAIM-EXTRACTOR] GEMINI_API_KEY missing; using draft heuristic fallback.")
            return extract_claims_heuristic(
                raw_text or summary,
                source_type="draft",
                section_name=section_name,
            )
        return await extract_draft_claims_llm(section_name, raw_text, summary)

    return extract_claims_heuristic(summary, source_type="paper", section_name=section_name)


async def extract_claims_from_chunk(chunk_text: str) -> list[Claim]:
    """Backward-compatible helper: heuristic extraction on a single text chunk."""
    return extract_claims_heuristic(chunk_text, source_type="paper")
