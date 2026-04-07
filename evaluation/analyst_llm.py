
#Input:  Reranked chunks from Phase 1/2 (JSON file on disk)
#Output: ComparisonRecord per chunk comparison


import os
import json
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional
from dataclasses import dataclass, asdict

from groq import Groq
from dotenv import load_dotenv

load_dotenv()

#Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s"
)
logger = logging.getLogger("analyst_llm")

#Constants
GROQ_MODEL         = "llama-3.3-70b-versatile"
CONFIDENCE_FLOOR   = 0.70   # below this → escalate, skip Logic LLM
VAGUE_PHRASES      = ["might", "possibly", "could be", "unclear",
                       "seems", "perhaps", "not sure", "may indicate"]
PENALTY_PER_PHRASE = 0.08


# Data Contract 
@dataclass
class ComparisonRecord:
    record_id:                str
    draft_claim_id:           str
    draft_claim_text:         str
    paper_id:                 str
    paper_claim_text:         str
    verdict:                  str          # support | contradict | neutral
    contradiction_severity:   str          # minor | direct | null
    flag:                     str          # GREEN | YELLOW | ORANGE | RED | ESCALATE
    confidence:               float
    logic_llm_output:         Optional[str]  # filled by contradiction_verifier.py
    reasoning:                str
    active:                   bool
    created_at:               str
    invalidated_at:           Optional[str]


# Groq Client 
def get_groq_client() -> Groq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "GROQ_API_KEY not found. Add it to your .env file."
        )
    return Groq(api_key=api_key)


# Confidence Sanity Gate
def apply_sanity_gate(raw_confidence: float, reasoning: str) -> float:
    """
    Penalize self-reported confidence when reasoning contains vague language.
    LLMs frequently report high confidence on uncertain outputs.
    Each vague phrase deducts PENALTY_PER_PHRASE from raw confidence.
    """
    reasoning_lower = reasoning.lower()
    penalty = sum(
        PENALTY_PER_PHRASE
        for phrase in VAGUE_PHRASES
        if phrase in reasoning_lower
    )
    adjusted = max(0.0, raw_confidence - penalty)

    if penalty > 0:
        logger.info(
            f"Confidence penalized: {raw_confidence:.2f} → {adjusted:.2f} "
            f"(penalty={penalty:.2f})"
        )
    return adjusted


#Core LLM Call
def call_analyst_llm(
    client: Groq,
    draft_claim: str,
    paper_claim: str
) -> dict:
    """
    Calls the Analyst LLM with a strict structured output prompt.
    Returns a parsed dict with verdict, severity, confidence, reasoning.
    Raises ValueError if the response cannot be parsed.
    """

    system_prompt = """You are a research alignment analyst.
Your job is to compare two academic claims and determine their relationship.

You must respond ONLY with a valid JSON object. No explanation outside the JSON.
No markdown. No preamble. Just the JSON.

Required format:
{
  "verdict": "<support | contradict | neutral>",
  "contradiction_severity": "<minor | direct | null>",
  "confidence": <float between 0.0 and 1.0>,
  "reasoning": "<one sentence explaining your verdict>"
}

Rules:
- verdict = "support"     → new claim agrees with or reinforces draft claim
- verdict = "contradict"  → new claim opposes draft claim
- verdict = "neutral"     → no meaningful relationship
- contradiction_severity:
    "direct"  → if A is true, B logically cannot be true
    "minor"   → tension exists but both could be partially true
    "null"    → use when verdict is support or neutral
- confidence: be conservative. If you are guessing, score below 0.70.
- reasoning: one sentence only. If uncertain, say so explicitly."""

    user_prompt = f"""DRAFT CLAIM:
{draft_claim}

PAPER CLAIM:
{paper_claim}

Evaluate these two claims and return the JSON."""

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt}
            ],
            temperature=0.1,   # low temp for determinism
            max_tokens=300
        )
    except Exception as e:
        logger.error(f"Groq API call failed: {e}")
        raise

    raw_text = response.choices[0].message.content.strip()
    logger.debug(f"Raw LLM response: {raw_text}")

    # Strip markdown fences if model adds them despite instructions
    if raw_text.startswith("```"):
        raw_text = raw_text.split("```")[1]
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
        raw_text = raw_text.strip()

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM JSON response: {raw_text}")
        raise ValueError(f"LLM returned non-JSON output: {e}") from e

    # Validate required fields
    required_fields = ["verdict", "contradiction_severity", "confidence", "reasoning"]
    for field in required_fields:
        if field not in parsed:
            raise ValueError(f"LLM response missing required field: '{field}'")

    # Validate verdict value
    valid_verdicts = {"support", "contradict", "neutral"}
    if parsed["verdict"] not in valid_verdicts:
        raise ValueError(f"Invalid verdict: '{parsed['verdict']}'")

    # Validate confidence range
    if not (0.0 <= float(parsed["confidence"]) <= 1.0):
        raise ValueError(f"Confidence out of range: {parsed['confidence']}")

    return parsed


# Main Evaluation Function
def evaluate_claim_pair(
    client: Groq,
    draft_claim_id: str,
    draft_claim_text: str,
    paper_id: str,
    paper_claim_text: str
) -> ComparisonRecord:
    """
    Evaluates one draft claim against one paper claim.
    Returns a ComparisonRecord. Flag will be ESCALATE if confidence too low.
    logic_llm_output is None here — filled later by contradiction_verifier.py.
    """

    logger.info(
        f"Evaluating: draft_claim={draft_claim_id} vs paper={paper_id}"
    )

    try:
        llm_output = call_analyst_llm(client, draft_claim_text, paper_claim_text)
    except (ValueError, Exception) as e:
        logger.warning(f"LLM call failed for {draft_claim_id} vs {paper_id}: {e}")
        # Return a safe escalation record on failure
        return ComparisonRecord(
            record_id=str(uuid.uuid4()),
            draft_claim_id=draft_claim_id,
            draft_claim_text=draft_claim_text,
            paper_id=paper_id,
            paper_claim_text=paper_claim_text,
            verdict="unknown",
            contradiction_severity="null",
            flag="ESCALATE",
            confidence=0.0,
            logic_llm_output=None,
            reasoning=f"LLM call failed: {str(e)}",
            active=True,
            created_at=datetime.now(timezone.utc).isoformat(),
            invalidated_at=None
        )

    raw_confidence = float(llm_output["confidence"])
    reasoning      = llm_output["reasoning"]
    verdict        = llm_output["verdict"]
    severity       = llm_output["contradiction_severity"]

    # Apply sanity gate
    adjusted_confidence = apply_sanity_gate(raw_confidence, reasoning)

    # Determine flag — delegate to flag_generator
    from flag_generator import generate_flag
    flag = generate_flag(verdict, severity, adjusted_confidence)

    logger.info(
        f"Result → verdict={verdict}, severity={severity}, "
        f"confidence={adjusted_confidence:.2f}, flag={flag}"
    )

    return ComparisonRecord(
        record_id=str(uuid.uuid4()),
        draft_claim_id=draft_claim_id,
        draft_claim_text=draft_claim_text,
        paper_id=paper_id,
        paper_claim_text=paper_claim_text,
        verdict=verdict,
        contradiction_severity=severity,
        flag=flag,
        confidence=adjusted_confidence,
        logic_llm_output=None,   # filled by contradiction_verifier.py
        reasoning=reasoning,
        active=True,
        created_at=datetime.now(timezone.utc).isoformat(),
        invalidated_at=None
    )


#Batch Runner
def run_evaluation_from_json(
    reranked_json_path: str,
    draft_claim_id: str,
    draft_claim_text: str
) -> list[ComparisonRecord]:
    """
    Loads reranked chunks from Phase 1/2 JSON file.
    Runs evaluate_claim_pair for each chunk.
    Returns list of ComparisonRecords.

    Expected JSON format from Phase 1/2:
    [
        {
            "paper_id": "paper_001",
            "chunk_id": "chunk_042",
            "section":  "methodology",
            "text":     "...",
            "score":    0.87
        },
        ...
    ]
    """

    logger.info(f"Loading reranked chunks from: {reranked_json_path}")

    if not os.path.exists(reranked_json_path):
        raise FileNotFoundError(
            f"Reranked JSON not found at: {reranked_json_path}"
        )

    with open(reranked_json_path, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    if not isinstance(chunks, list) or len(chunks) == 0:
        raise ValueError("Reranked JSON must be a non-empty list of chunk dicts.")

    client = get_groq_client()
    records = []

    for i, chunk in enumerate(chunks):
        required_chunk_fields = ["paper_id", "text"]
        for field in required_chunk_fields:
            if field not in chunk:
                logger.warning(f"Chunk {i} missing '{field}' — skipping.")
                continue

        record = evaluate_claim_pair(
            client=client,
            draft_claim_id=draft_claim_id,
            draft_claim_text=draft_claim_text,
            paper_id=chunk["paper_id"],
            paper_claim_text=chunk["text"]
        )
        records.append(record)

    logger.info(f"Evaluation complete. {len(records)} records generated.")
    return records


# Entry Point
if __name__ == "__main__":
    # Quick smoke test — replace paths and claim with real values
    TEST_JSON_PATH    = "data/reranked_chunks.json"
    TEST_CLAIM_ID     = "claim_001"
    TEST_CLAIM_TEXT   = (
        "Daily low-dose aspirin reduces cardiovascular risk in adults over 50."
    )

    records = run_evaluation_from_json(
        reranked_json_path=TEST_JSON_PATH,
        draft_claim_id=TEST_CLAIM_ID,
        draft_claim_text=TEST_CLAIM_TEXT
    )

    for r in records:
        print(json.dumps(asdict(r), indent=2))