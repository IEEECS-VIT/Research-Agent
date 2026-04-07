import os
import json
import uuid
import logging
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from typing import Optional

import chromadb
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s"
)
logger = logging.getLogger("contradiction_verifier")

# --- Configuration ---
GROQ_MODEL = "llama-3.3-70b-versatile"
CHROMA_PATH = "./chroma_db"
META_FLAGS_COLLECTION = "meta_flags"
COMP_RECORDS_COLLECTION = "comparison_records"
VALID_LOGIC_OUTPUTS = {"CONFIRMED", "REJECTED", "SCOPE_MISMATCH"}

@dataclass
class ComparisonRecord:
    record_id: str
    draft_claim_id: str
    draft_claim_text: str
    paper_id: str
    paper_claim_text: str
    verdict: str
    contradiction_severity: str
    flag: str
    confidence: float
    logic_llm_output: Optional[str]
    reasoning: str
    active: bool
    created_at: str
    invalidated_at: Optional[str]

@dataclass
class MetaFlag:
    id: str
    source_a: str 
    source_b: str 
    claim_a: str 
    claim_b: str 
    comparison_record_id: str
    contradiction_type: str 
    verified_by: str 
    logic_llm_output: str 
    confidence: float
    flag_color: str
    created_at: str
    status: str 
    active: bool

# --- Client Initializers ---
def get_groq_client() -> Groq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError("GROQ_API_KEY not found in .env file.")
    return Groq(api_key=api_key)

def get_chroma_client() -> chromadb.Client:
    return chromadb.PersistentClient(path=CHROMA_PATH)

def get_or_create_collection(client: chromadb.Client, name: str) -> chromadb.Collection:
    return client.get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"}
    )

# --- Logic Core ---
def call_logic_llm(client: Groq, claim_a: str, claim_b: str) -> str:
    """Verifies logical incompatibility between two research claims."""
    system_prompt = (
        "You are a logical contradiction verifier for academic research. "
        "Output EXACTLY ONE WORD: CONFIRMED | REJECTED | SCOPE_MISMATCH. "
        "CONFIRMED: Incompatible constructs/results. "
        "REJECTED: No contradiction found. "
        "SCOPE_MISMATCH: Different populations or contexts."
    )
    user_prompt = f"Statement A: {claim_a}\n\nStatement B: {claim_b}\n\nVerdict:"

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.0,
            max_tokens=10
        )
        raw_output = response.choices[0].message.content.strip().upper().replace(".", "")
        
        if raw_output not in VALID_LOGIC_OUTPUTS:
            logger.warning(f"Unexpected LLM output: {raw_output}. Defaulting to SCOPE_MISMATCH.")
            return "SCOPE_MISMATCH"
        return raw_output
    except Exception as e:
        logger.error(f"Logic LLM API call failed: {e}")
        raise

# --- Persistence Layers ---
def store_meta_flag(chroma_client: chromadb.Client, meta_flag: MetaFlag) -> None:
    collection = get_or_create_collection(chroma_client, META_FLAGS_COLLECTION)
    
    metadata = asdict(meta_flag)
    metadata["active"] = str(metadata["active"]) # Chroma requirement
    
    collection.add(
        ids=[meta_flag.id],
        documents=[f"A: {meta_flag.claim_a} | B: {meta_flag.claim_b}"],
        metadatas=[metadata]
    )
    logger.info(f"MetaFlag persisted: {meta_flag.id}")

def store_comparison_record(chroma_client: chromadb.Client, record: ComparisonRecord) -> None:
    collection = get_or_create_collection(chroma_client, COMP_RECORDS_COLLECTION)
    
    metadata = asdict(record)
    metadata["active"] = str(metadata["active"])
    metadata["logic_llm_output"] = record.logic_llm_output or "null"
    metadata["invalidated_at"] = record.invalidated_at or "null"

    collection.add(
        ids=[record.record_id],
        documents=[f"D: {record.draft_claim_text} | P: {record.paper_claim_text}"],
        metadatas=[metadata]
    )

def map_contradiction_type(severity: str) -> str:
    return {"direct": "direct_opposition", "minor": "minor_tension"}.get(severity, "none")

# --- Pipeline Execution ---
def verify_and_store(
    record: ComparisonRecord, 
    groq_client: Groq, 
    chroma_client: chromadb.Client
) -> ComparisonRecord:
    """Orchestrates verification, flag updating, and storage."""
    from flag_generator import flag_requires_logic_llm, upgrade_flag_after_verification

    if not flag_requires_logic_llm(record.flag):
        store_comparison_record(chroma_client, record)
        return record

    try:
        logic_output = call_logic_llm(groq_client, record.draft_claim_text, record.paper_claim_text)
        record.logic_llm_output = logic_output

        flag_res = upgrade_flag_after_verification(record.flag, logic_output, record.confidence)
        record.flag = flag_res.flag

        if logic_output == "CONFIRMED":
            m_flag = MetaFlag(
                id=f"MF_{uuid.uuid4().hex[:8].upper()}",
                source_a="draft",
                source_b=record.paper_id,
                claim_a=record.draft_claim_text,
                claim_b=record.paper_claim_text,
                comparison_record_id=record.record_id,
                contradiction_type=map_contradiction_type(record.contradiction_severity),
                verified_by="logic_llm",
                logic_llm_output=logic_output,
                confidence=record.confidence,
                flag_color=record.flag,
                created_at=datetime.now(timezone.utc).isoformat(),
                status="ACTIVE",
                active=True
            )
            store_meta_flag(chroma_client, m_flag)

    except Exception as e:
        logger.error(f"Pipeline error for {record.record_id}: {e}")
        record.flag, record.logic_llm_output = "ESCALATE", "ERROR"

    store_comparison_record(chroma_client, record)
    return record

def run_verification_batch(records: list[ComparisonRecord]) -> list[ComparisonRecord]:
    groq_client = get_groq_client()
    chroma_client = get_chroma_client()
    return [verify_and_store(r, groq_client, chroma_client) for r in records]

if __name__ == "__main__":
    # Smoke test implementation
    test_recs = [
        ComparisonRecord(
            record_id=str(uuid.uuid4()),
            draft_claim_id="cl_01",
            draft_claim_text="Aspirin reduces CV risk in over 50s.",
            paper_id="pa_01",
            paper_claim_text="Aspirin increases bleeding risk with no CV benefit in over 50s.",
            verdict="contradict",
            contradiction_severity="direct",
            flag="RED",
            confidence=0.88,
            logic_llm_output=None,
            reasoning="Direct opposition on efficacy.",
            active=True,
            created_at=datetime.now(timezone.utc).isoformat(),
            invalidated_at=None
        )
    ]
    results = run_verification_batch(test_recs)
    print(json.dumps([asdict(r) for r in results], indent=2))