import os
import json
import asyncio
import logging
from io import BytesIO
from google import genai
from google.genai import types
from pydantic import BaseModel
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

from ingestion_pipeline.docling_parser import (
    extract_document_content,
    inject_image_summaries,
    split_sections,
)
from ingestion_pipeline.schemas import SectionSummary

load_dotenv(override=True)

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY not found in .env")

client = genai.Client(api_key=api_key)
MODEL_NAME = "gemini-2.5-flash-lite"
IMAGE_MODEL_NAME = os.getenv("GEMINI_IMAGE_MODEL", MODEL_NAME)
IMAGE_SUMMARY_FALLBACK = "[Image summary unavailable: vision model quota or access limit reached.]"

# We use a Pydantic schema to force the LLM to output a clean, parsable JSON array
class GeneratedSummary(BaseModel):
    section_name: str
    summary: str

class BatchSummaryResponse(BaseModel):
    summaries: list[GeneratedSummary]

SYSTEM_PROMPT = """You are a highly capable research paper analyst. 
You will be provided with a JSON array containing sections of a document.
For EACH section, read the text and generate a concise 3-5 sentence summary.
Preserve key claims, methodologies, and exact numbers.
Return your output STRICTLY matching the requested JSON schema."""

IMAGE_SUMMARY_PROMPT = """Summarize this research-paper image for raw-text ingestion.
Write 2-3 compact academic sentences: more informative than a caption, but not a long analysis.
Mention visible chart trends, axes, labels, equations, architecture blocks, important numbers, and relationships when legible.
If the image is decorative or unclear, state the most likely purpose briefly."""

def _pil_image_to_png_bytes(image) -> bytes:
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()

async def summarise_image(image, image_index: int) -> str:
    max_retries = 2
    delay = 5

    for attempt in range(max_retries):
        try:
            logger.info(
                "Summarizing image %d (Attempt %d/%d) using %s...",
                image_index, attempt + 1, max_retries, IMAGE_MODEL_NAME
            )
            image_bytes = _pil_image_to_png_bytes(image)
            response = await client.aio.models.generate_content(
                model=IMAGE_MODEL_NAME,
                contents=[
                    IMAGE_SUMMARY_PROMPT,
                    types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
                ],
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    max_output_tokens=220,
                )
            )

            summary = (response.text or "").strip()
            if not summary:
                raise ValueError("Vision model returned an empty image summary.")

            return f"[Image summary: {summary}]"
        except Exception as e:
            logger.warning(
                "Image %d failed on attempt %d: %s - %s",
                image_index, attempt + 1, type(e).__name__, e
            )
            if attempt < max_retries - 1:
                await asyncio.sleep(delay)
                delay += 5

    logger.warning(
        "Continuing without generated summary for image %d.", image_index
    )
    return IMAGE_SUMMARY_FALLBACK

async def summarise_images(images: list) -> list[str]:
    if not images:
        return []

    summaries = []
    logger.info("Found %d extracted images to summarize.", len(images))
    for image_index, image in enumerate(images, start=1):
        summaries.append(await summarise_image(image, image_index))
        await asyncio.sleep(1)

    return summaries

async def batch_summarise_sections(sections: list[dict]) -> list[SectionSummary]:
    logger.info("Preparing Single-Shot Batch prompt for %d sections...", len(sections))
    
    # Prepare the payload mapping
    payload_data = []
    for sec in sections:
        text_snippet = sec["raw_text"][:8000] 
        payload_data.append({
            "section_name": sec["section_name"],
            "text": text_snippet
        })

    prompt_content = f"{SYSTEM_PROMPT}\n\nDocument Sections Data:\n{json.dumps(payload_data)}"
    
    max_retries = 4
    # PIVOT: Started delay at 45s to safely clear Google's ~33s Free Tier timeout lock
    delay = 45 

    for attempt in range(max_retries):
        try:
            logger.info("Executing API Call (Attempt %d/%d) using %s...", attempt + 1, max_retries, MODEL_NAME)
            response = await client.aio.models.generate_content(
                model=MODEL_NAME,
                contents=prompt_content,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=BatchSummaryResponse,
                    temperature=0.2,
                )
            )
            
            response_json = json.loads(response.text)
            generated_summaries = response_json.get("summaries", [])
            
            summary_lookup = {item["section_name"]: item["summary"] for item in generated_summaries}
            
            final_results = []
            for sec in sections:
                name = sec["section_name"]
                summary_text = summary_lookup.get(name, "[Summary Generation Failed]")
                
                final_results.append(SectionSummary(
                    section_name=name,
                    raw_text=sec["raw_text"],
                    summary=summary_text
                ))
                
            logger.info("Single-Shot Generation Complete! Extracted %d summaries.", len(final_results))
            return final_results
            
        except Exception as e:
            err_str = str(e).lower()
            logger.warning("API Error on attempt %d: %s - %s", attempt + 1, type(e).__name__, e)
            
            if "quota" in err_str or "429" in err_str or "exhausted" in err_str:
                if attempt < max_retries - 1:
                    logger.warning("Rate limit hit. Google API is in timeout. Waiting %d seconds before retry...", delay)
                    await asyncio.sleep(delay)
                    delay += 15
                else:
                    logger.error("FATAL: Max retries exceeded.")
                    raise RuntimeError(f"Max retries exceeded due to rate limits. Please check your API quota.") from e
            else:
                logger.error("Non-retryable error.", exc_info=True)
                raise

    return []

async def run_pipeline(file_path: str) -> list[SectionSummary]:
    try:
        parsed_content = extract_document_content(file_path)
        image_summaries = await summarise_images(parsed_content.images)
        raw_text = inject_image_summaries(parsed_content.full_text, image_summaries)
        sections = split_sections(raw_text)
        if not sections:
            return []
            
        results = await batch_summarise_sections(sections)
        return results
    except Exception as e:
        logger.error("Pipeline failure: %s", e, exc_info=True)
        raise
