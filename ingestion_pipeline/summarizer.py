import asyncio
import time
import os
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted
from dotenv import load_dotenv

from docling_parser import extract_sections
from schemas import SectionSummary

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY not found in .env")

genai.configure(api_key=api_key)

# gemini-2.0-flash-lite has a higher free-tier quota than gemini-2.0-flash
# swap back to "gemini-2.0-flash" once you enable billing
MODEL_NAME = "models/gemini-1.5-flash-8b"
model = genai.GenerativeModel(MODEL_NAME)

SYSTEM_PROMPT = """You are a research paper analyst.
Summarise the section clearly and concisely in 3-6 sentences.
Preserve key claims, methods, and numbers exactly as stated.
Output plain text only — no bullet points, no headers."""

SECTION_HINTS = {
    "abstract":                    "Capture the problem, method, and main result.",
    "introduction":                "Capture the motivation, research gap, and stated contribution.",
    "related_work":                "Capture key prior works and how this paper differs.",
    "background":                  "Capture key concepts and definitions introduced.",
    "methodology":                 "Capture the experimental design, datasets, and approach.",
    "data_processing_pipelines":   "Capture the data ingestion and preprocessing steps.",
    "graphbased_cybersecurity_models": "Capture how RDF/knowledge graphs are structured.",
    "graph_based_cybersecurity_models": "Capture how RDF/knowledge graphs are structured.",
    "structuring_security_event_logs_in_rdf_triple_stores": "Capture the RDF structuring process.",
    "converting_data_to_rdf_knowledge_graph": "Capture the RDF triple generation steps.",
    "handling_and_identification_of_pii_in_rdf_knowledge_graphs": "Capture the PII detection and anonymisation approach.",
    "sparql_query":                "Capture what this query does and what it returns.",
    "results":                     "Capture specific numerical results and comparisons.",
    "preliminary_evaluation":      "Capture evaluation method, metrics, and key scores.",
    "discussion":                  "Capture interpretations, limitations, and implications.",
    "discussion_and_conclusions":  "Capture main takeaways, limitations, and future work.",
    "conclusion":                  "Capture main takeaways and future directions.",
}

# Sections with no analytical value — skip them entirely
SKIP_SECTIONS = {
    "references", "acknowledgement", "acknowledgements",
    "json_logs_from_network_security_groups",
    "txt_firewall_logs",
    "csv_email_security_logs",
}

MAX_INPUT_CHARS = 6000
# Delay between each API call — critical on free tier (15 RPM limit)
INTER_REQUEST_DELAY = 2   # seconds; increase to 10 if still hitting 429


def build_prompt(section_name: str, text: str) -> str:
    hint = SECTION_HINTS.get(section_name.lower(), "Summarise the key points of this section.")
    return (
        f"{SYSTEM_PROMPT}\n\n"
        f"Section: {section_name.replace('_', ' ').title()}\n"
        f"Focus: {hint}\n\n"
        f"---\n{text[:MAX_INPUT_CHARS]}\n---\n\n"
        f"Write the summary now:"
    )


def _call_with_retry(prompt: str, max_retries: int = 4) -> str:
    """
    Synchronous call with exponential backoff.
    Handles per-minute 429s gracefully. Daily quota exhaustion (limit: 0)
    will keep failing — in that case you need to wait or enable billing.
    """
    delay = 15  # start at 15s, double each retry
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt)
            return response.text.strip()
        except ResourceExhausted as e:
            err = str(e)
            if "PerDay" in err or "limit: 0" in err:
                # Daily quota gone — no point retrying
                raise RuntimeError(
                    f"Daily free-tier quota exhausted for {MODEL_NAME}. "
                    "Enable billing at aistudio.google.com or wait until tomorrow."
                ) from e
            if attempt < max_retries - 1:
                print(f"    Rate limit hit, waiting {delay}s before retry {attempt + 1}...")
                time.sleep(delay)
                delay *= 2
            else:
                raise
    raise RuntimeError("Max retries exceeded")


async def summarise_section(section_name: str, text: str) -> str:
    if not text.strip():
        return "[Empty section]"
    try:
        return await asyncio.to_thread(
            _call_with_retry,
            build_prompt(section_name, text),
        )
    except Exception as e:
        return f"[Error: {str(e)}]"


async def summarise_all(sections: list[dict]) -> list[SectionSummary]:
    """
    Process sections SEQUENTIALLY with a delay between each call.
    Concurrent calls on the free tier burns through the per-minute quota instantly.
    """
    results = []
    total = len(sections)

    for i, sec in enumerate(sections):
        name = sec["section_name"]

        if name in SKIP_SECTIONS:
            print(f"  [{i+1}/{total}] Skipping: {name}")
            results.append(SectionSummary(
                section_name=name,
                raw_text=sec["raw_text"],
                summary=f"[Skipped — {name}]",
            ))
            continue

        print(f"  [{i+1}/{total}] Summarising: {name}...")
        summary = await summarise_section(name, sec["raw_text"])
        results.append(SectionSummary(
            section_name=name,
            raw_text=sec["raw_text"],
            summary=summary,
        ))

        # Pause between calls to stay under the free-tier rate limit
        if i < total - 1:
            await asyncio.sleep(INTER_REQUEST_DELAY)

    return results


async def run_pipeline(file_path: str) -> list[SectionSummary]:
    sections = extract_sections(file_path)
    print(f"Extracted {len(sections)} sections. Starting summarisation...")
    return await summarise_all(sections)