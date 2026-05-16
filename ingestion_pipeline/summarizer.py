import os
import json
import asyncio
import traceback
from google import genai
from google.genai import types
from pydantic import BaseModel
from dotenv import load_dotenv

from ingestion_pipeline.docling_parser import extract_sections
from ingestion_pipeline.schemas import SectionSummary

load_dotenv(override=True)

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY not found in .env")

client = genai.Client(api_key=api_key)
MODEL_NAME = "gemini-2.5-flash-lite"

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

async def batch_summarise_sections(sections: list[dict]) -> list[SectionSummary]:
    print(f"[SUMMARIZER] Preparing Single-Shot Batch prompt for {len(sections)} sections...")
    
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
            print(f"[SUMMARIZER] Executing API Call (Attempt {attempt + 1}/{max_retries}) using {MODEL_NAME}...")
            response = await client.aio.models.generate_content(
                model=MODEL_NAME,
                contents=prompt_content,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=BatchSummaryResponse,
                    temperature=0.2,
                )
            )
            
            # Parse the structured response
            response_json = json.loads(response.text)
            generated_summaries = response_json.get("summaries", [])
            
            # Create a lookup dictionary from the LLM output
            summary_lookup = {item["section_name"]: item["summary"] for item in generated_summaries}
            
            # Reconstruct the final list combining raw text and new summaries
            final_results = []
            for sec in sections:
                name = sec["section_name"]
                summary_text = summary_lookup.get(name, "[Summary Generation Failed]")
                
                final_results.append(SectionSummary(
                    section_name=name,
                    raw_text=sec["raw_text"],
                    summary=summary_text
                ))
                
            print(f"[SUMMARIZER] Single-Shot Generation Complete! Extracted {len(final_results)} summaries.")
            return final_results
            
        except Exception as e:
            err_str = str(e).lower()
            print(f"[SUMMARIZER] API Error on attempt {attempt + 1}: {type(e).__name__} - {e}")
            
            if "quota" in err_str or "429" in err_str or "exhausted" in err_str:
                if attempt < max_retries - 1:
                    print(f"[SUMMARIZER] -> Rate limit hit. Google API is in timeout. Waiting {delay} seconds before retry...")
                    await asyncio.sleep(delay)
                    delay += 15 # Increment delay slightly for subsequent retries just in case
                else:
                    print(f"[SUMMARIZER] -> FATAL: Max retries exceeded.")
                    raise RuntimeError(f"Max retries exceeded due to rate limits. Please check your API quota.") from e
            else:
                # If it's a parsing error or a non-429 error from Google, fail loudly
                traceback.print_exc()
                raise

    return []

async def run_pipeline(file_path: str) -> list[SectionSummary]:
    try:
        sections = extract_sections(file_path)
        if not sections:
            return []
            
        results = await batch_summarise_sections(sections)
        return results
    except Exception as e:
        print(f"[PIPELINE] Pipeline failure: {e}")
        traceback.print_exc()
        raise