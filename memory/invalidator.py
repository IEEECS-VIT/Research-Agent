import os
import logging
from datetime import datetime, timezone
from typing import Optional
from dataclasses import dataclass

import chromadb
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s"
)
logger = logging.getLogger("invalidation")

# --- Configuration ---
CHROMA_PATH = "./chroma_db"
COMP_RECORDS_COLLECTION = "comparison_records"
META_FLAGS_COLLECTION = "meta_flags"

@dataclass
class InvalidationReport:
    invalidated_paper_id: str
    reason: str
    affected_record_ids: list[str]
    affected_draft_claims: list[str]
    affected_meta_flag_ids: list[str]
    tombstoned_at: str
    total_affected: int

def get_chroma_client() -> chromadb.Client:
    return chromadb.PersistentClient(path=CHROMA_PATH)

# --- Atomic Updates ---
def tombstone_record(
    collection: chromadb.Collection,
    record_id: str,
    paper_id: str,
    reason: str,
    timestamp: str
) -> bool:
    """Marks a single record as inactive. Never deletes."""
    try:
        result = collection.get(ids=[record_id], include=["metadatas"])
        if not result["ids"]:
            return False

        meta = result["metadatas"][0]
        if meta.get("active") == "False":
            return False

        meta.update({
            "active": "False",
            "invalidated_at": timestamp,
            "invalidation_reason": f"{paper_id} tombstoned — {reason}"
        })

        collection.update(ids=[record_id], metadatas=[meta])
        logger.info(f"Tombstoned record: {record_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to tombstone {record_id}: {e}")
        return False

def tombstone_meta_flags_for_paper(
    chroma_client: chromadb.Client,
    paper_id: str,
    reason: str,
    timestamp: str
) -> list[str]:
    """Invalidates all MetaFlags linked to a specific paper."""
    try:
        col = chroma_client.get_or_create_collection(name=META_FLAGS_COLLECTION)
        res = col.get(where={"source_b": paper_id}, include=["metadatas"])
    except Exception as e:
        logger.error(f"MetaFlag access error: {e}")
        return []

    affected = []
    for flag_id, meta in zip(res["ids"], res["metadatas"]):
        if meta.get("active") == "False": continue
        
        meta.update({
            "active": "False",
            "status": "TOMBSTONED",
            "invalidated_at": timestamp,
            "invalidation_reason": f"{paper_id} tombstoned — {reason}"
        })
        col.update(ids=[flag_id], metadatas=[meta])
        affected.append(flag_id)
    
    return affected

# --- Core Invalidation Engine ---
def invalidate_paper(paper_id: str, reason: str, chroma_client: Optional[chromadb.Client] = None) -> InvalidationReport:
    """Performs full paper tombstoning and returns audit report."""
    client = chroma_client or get_chroma_client()
    ts = datetime.now(timezone.utc).isoformat()

    try:
        comp_col = client.get_or_create_collection(name=COMP_RECORDS_COLLECTION)
        res = comp_col.get(where={"paper_id": paper_id}, include=["metadatas"])
    except Exception as e:
        logger.error(f"Query failed: {e}")
        return InvalidationReport(paper_id, reason, [], [], [], ts, 0)

    affected_recs, affected_claims = [], []
    for rid, meta in zip(res["ids"], res["metadatas"]):
        if tombstone_record(comp_col, rid, paper_id, reason, ts):
            affected_recs.append(rid)
            claim_id = meta.get("draft_claim_id", "unknown")
            if claim_id not in affected_claims: affected_claims.append(claim_id)

    affected_flags = tombstone_meta_flags_for_paper(client, paper_id, reason, ts)

    return InvalidationReport(
        invalidated_paper_id=paper_id,
        reason=reason,
        affected_record_ids=affected_recs,
        affected_draft_claims=affected_claims,
        affected_meta_flag_ids=affected_flags,
        tombstoned_at=ts,
        total_affected=len(affected_recs) + len(affected_flags)
    )

# --- Cascade Logic ---

def invalidate_paper_section(
    paper_id: str,
    flagged_section: str,
    reason: str,
    chroma_client: Optional[chromadb.Client] = None
) -> InvalidationReport:
    """Tombstones downstream sections when a parent section (e.g. methodology) is RED."""
    DOWNSTREAM_MAP = {
        "methodology": ["results", "discussion", "conclusion"],
        "abstract": ["introduction"],
        "introduction": []
    }

    downstream = DOWNSTREAM_MAP.get(flagged_section, [])
    client = chroma_client or get_chroma_client()
    ts = datetime.now(timezone.utc).isoformat()
    affected_recs, affected_claims = [], []

    try:
        comp_col = client.get_or_create_collection(name=COMP_RECORDS_COLLECTION)
        for section in downstream:
            res = comp_col.get(
                where={"$and": [{"paper_id": paper_id}, {"section": section}]},
                include=["metadatas"]
            )
            for rid, meta in zip(res["ids"], res["metadatas"]):
                full_reason = f"Section '{flagged_section}' RED — downstream '{section}' invalidated. {reason}"
                if tombstone_record(comp_col, rid, paper_id, full_reason, ts):
                    affected_recs.append(rid)
                    claim_id = meta.get("draft_claim_id", "unknown")
                    if claim_id not in affected_claims: affected_claims.append(claim_id)
    except Exception as e:
        logger.error(f"Section cascade failed: {e}")

    return InvalidationReport(paper_id, f"Cascade: {flagged_section}", affected_recs, affected_claims, [], ts, len(affected_recs))

def get_active_records_for_draft(draft_claim_id: str, chroma_client: Optional[chromadb.Client] = None) -> list[dict]:
    """Filters out tombstoned records for the UI layer."""
    client = chroma_client or get_chroma_client()
    try:
        col = client.get_or_create_collection(name=COMP_RECORDS_COLLECTION)
        res = col.get(
            where={"$and": [{"draft_claim_id": draft_claim_id}, {"active": "True"}]},
            include=["metadatas", "documents"]
        )
        return [{"record_id": rid, "document": doc, **meta} for rid, meta, doc in zip(res["ids"], res["metadatas"], res["documents"])]
    except Exception:
        return []

if __name__ == "__main__":
    report = invalidate_paper("paper_001", "Methodology RED flag — fabrication detected")
    print(f"Invalidated {report.total_affected} total artifacts for {report.invalidated_paper_id}")