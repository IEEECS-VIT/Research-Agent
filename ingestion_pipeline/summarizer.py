import os
import json
import asyncio
import random
import traceback
from google.genai import types
from pydantic import BaseModel
from dotenv import load_dotenv

from ingestion_pipeline.docling_parser import extract_sections
from ingestion_pipeline.schemas import SectionSummary
from GraphEngine.utils.gemini_client import (
    is_retryable_gemini_error,
    _get_client,
)

load_dotenv(override=True)

# NOTE: Lazy-create the genai client inside functions to avoid import-time
# failures when `GEMINI_API_KEY` is not present. This makes the app import
#able even when the key is missing and surfaces clear errors at request-time.
MODEL_NAME = "gemini-2.5-flash-lite"

# We use a Pydantic schema to force the LLM to output a clean, parsable JSON array
class GeneratedSummary(BaseModel):
    section_name: str
    summary: str

SYSTEM_PROMPT = """You are a highly capable research paper analyst. 
You will be provided with a JSON array containing sections of a document.
For EACH section, read the text and generate a concise 3-5 sentence summary.
Preserve key claims, methodologies, and exact numbers.
Return your output STRICTLY matching the requested JSON schema."""


def _fallback_summary(text_snippet: str) -> str:
    cleaned_text = " ".join(text_snippet.split())
    if not cleaned_text:
        return "[Summary unavailable: empty section text]"

    sentences = []
    for chunk in cleaned_text.replace("?", ".").replace("!", ".").split("."):
        sentence = chunk.strip()
        if sentence:
            sentences.append(sentence)
        if len(sentences) == 3:
            break

    if not sentences:
        return cleaned_text[:400] + ("..." if len(cleaned_text) > 400 else "")

    summary = ". ".join(sentences)
    if len(cleaned_text) > len(summary):
        summary += "."
    return summary[:600]

async def batch_summarise_sections(sections: list[dict]) -> list[SectionSummary]:
    print(f"[SUMMARIZER] Preparing concurrent summarization for {len(sections)} sections...")

    client = _get_client()

    max_retries = 5
    base_delay = 3

    # Limit concurrent summarization calls to avoid quota exhaustion.
    # Tune via SUMMARIZE_MAX_CONCURRENT env var (default 5).
    max_concurrent = int(os.getenv("SUMMARIZE_MAX_CONCURRENT", "5"))
    sem = asyncio.Semaphore(max_concurrent)

    async def _summarise_one(sec: dict, idx: int) -> tuple[int, SectionSummary]:
        """Summarize a single section with retries. Returns (original_index, result)."""
        text_snippet = sec["raw_text"][:8000]
        prompt_content = (
            f"{SYSTEM_PROMPT}\n\nSection:\n"
            f"{json.dumps({'section_name': sec['section_name'], 'text': text_snippet})}"
        )
        summary_text = _fallback_summary(text_snippet)

        async with sem:
            for attempt in range(max_retries):
                try:
                    print(
                        f"[SUMMARIZER] Section `{sec['section_name']}` call "
                        f"(attempt {attempt + 1})"
                    )
                    response = await client.aio.models.generate_content(
                        model=MODEL_NAME,
                        contents=prompt_content,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            response_schema=GeneratedSummary,
                            temperature=0.2,
                        ),
                    )

                    # Defensive parse
                    try:
                        response_json = json.loads(response.text)
                        summary_text = (
                            response_json.get("summary")
                            or response_json.get("text")
                            or "[Summary Missing]"
                        )
                    except Exception:
                        summary_text = response.text or "[Summary Missing]"

                    break

                except Exception as e:
                    print(
                        f"[SUMMARIZER] Error summarizing section "
                        f"`{sec['section_name']}`: {e}"
                    )
                    if is_retryable_gemini_error(e) and attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                        await asyncio.sleep(delay)
                        continue

                    if not is_retryable_gemini_error(e):
                        traceback.print_exc()
                        raise

                    print(
                        f"[SUMMARIZER] Falling back to extractive summary for "
                        f"section `{sec['section_name']}` after repeated Gemini errors"
                    )
                    break

        return idx, SectionSummary(
            section_name=sec["section_name"],
            raw_text=sec["raw_text"],
            summary=summary_text,
        )

    # Fire all section summarizations concurrently; gather preserves insertion order
    # but we use explicit index tuples to guarantee deterministic output ordering.
    indexed_results = await asyncio.gather(
        *[_summarise_one(sec, i) for i, sec in enumerate(sections)]
    )

    # Sort by original index so the section order matches the document structure.
    final_results = [result for _, result in sorted(indexed_results, key=lambda t: t[0])]

    print(f"[SUMMARIZER] Completed summarization for {len(final_results)} sections.")
    return final_results


async def run_pipeline(file_path: str) -> list[SectionSummary]:
    try:
        # extract_sections() calls docling's converter.convert() which is a
        # blocking CPU/IO-bound operation (PDF parsing). Run it in a thread-pool
        # executor so it does not stall the FastAPI async event loop.
        loop = asyncio.get_running_loop()
        sections = await loop.run_in_executor(None, extract_sections, file_path)

        if not sections:
            return []

        results = await batch_summarise_sections(sections)
        return results
    except Exception as e:
        print(f"[PIPELINE] Pipeline failure: {e}")
        traceback.print_exc()
        raise
