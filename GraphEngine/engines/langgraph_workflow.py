import asyncio
import os
from typing import List
from concurrent.futures import ThreadPoolExecutor

from GraphEngine.engines.comparison_engine import (
    compute_claim_embedding,
    compare_claim_against_candidates,
)
from GraphEngine.engines.retrieval_engine import retrieve_by_claim_embedding
from GraphEngine.db.crud import bulk_upsert_edges
from GraphEngine.utils.helpers import (
    derive_relation_type,
    derive_confidence_state,
    derive_verifier_state,
    map_semantics_to_flag,
)

# Configuration from environment / defaults
MAX_WORKERS = int(os.getenv("LANGGRAPH_MAX_WORKERS", "4"))
LOW_CONF_THRESHOLD = float(os.getenv("LOW_CONF_THRESHOLD", "0.5"))


async def _compare_single_claim(claim: dict, source_doc_type: str, version_id: str, chunk_type=None, n_results=None):
    claim_id = claim.get("claim_id") or claim.get("id") or "0"
    claim_text = claim.get("assertion", "")

    if not claim_text or not claim_text.strip():
        return None

    if n_results is None:
        n_results = int(os.getenv("COMPARISON_TOP_K", "15"))

    try:
        print(f"[LANGGRAPH-WORKFLOW] Embedding claim {claim_id}...")
        # 1. Embedding (async)
        emb = await compute_claim_embedding(claim_text)

        # 2. Retrieval (blocking chroma client) — run in threadpool
        loop = asyncio.get_running_loop()
        # Cross-type alignment: search all opposite-type chunks, not only the
        # uploading document's version_id (rolling version between draft/paper
        # would otherwise hide prior uploads).
        retrieved = await loop.run_in_executor(
            None,
            lambda: retrieve_by_claim_embedding(
                emb,
                source_doc_type,
                query_version_id=None,
                n_results=n_results,
            ),
        )

        candidate_count = len(retrieved.get("documents", [[]])[0] or [])
        print(
            f"[LANGGRAPH-WORKFLOW] Scoring claim {claim_id}: "
            f"{candidate_count} candidates x 1 LLM call (unified evaluator)..."
        )

        # 3. Scoring & verification (async)
        result = await compare_claim_against_candidates(
            claim_id=claim_id,
            claim_text=claim_text,
            claim_embedding=emb,
            source_doc_type=source_doc_type,
            version_id=version_id,
            retrieved_results=retrieved,
        )

        print(f"[LANGGRAPH-WORKFLOW] Finished claim {claim_id} ({len(result.matches)} matches scored).")
        return result

    except Exception as e:
        print(f"[LANGGRAPH-WORKFLOW] Error processing claim {claim_id}: {e}")
        return None


async def run_langgraph_workflow(claims: List[dict], source_doc_type: str, version_id: str, persist: bool = True) -> List:
    """
    Orchestrate claim-level comparison in parallel and persist edges after
    the full document workflow completes.

    Returns a list of ComparisonResult-like objects.
    """
    if not claims:
        return []

    total = len(claims)
    print(f"[LANGGRAPH-WORKFLOW] Starting comparison for {total} claims (workers={MAX_WORKERS})...")

    sem = asyncio.Semaphore(MAX_WORKERS)
    completed = 0

    async def sem_task(claim, index):
        nonlocal completed
        async with sem:
            print(f"[LANGGRAPH-WORKFLOW] Claim {index}/{total} started.")
            result = await _compare_single_claim(claim, source_doc_type, version_id)
            completed += 1
            print(f"[LANGGRAPH-WORKFLOW] Progress: {completed}/{total} claims done.")
            return result

    tasks = [asyncio.create_task(sem_task(c, i + 1)) for i, c in enumerate(claims)]
    results = await asyncio.gather(*tasks)

    # Filter out failed/None results
    comparison_results = [r for r in results if r is not None]

    # Compute flags and persist edges only after whole workflow completes
    if persist and comparison_results:
        # ── Build the full edge record list in memory (pure Python, no I/O) ──
        edge_records: list[tuple[str, str, dict]] = []
        for result in comparison_results:
            for match in result.matches:
                source_claim_id = result.claim_id or "unknown"
                target_claim_id = match.get("retrieved_id", "")

                support = match.get("support_score", 0.0)
                contradict = match.get("contradiction_score", 0.0)
                confidence = match.get("confidence", 0.0)

                relation = derive_relation_type(support, contradict)
                verifier_state = derive_verifier_state(match.get("verifier_status"))
                confidence_state = derive_confidence_state(
                    confidence, match.get("verifier_status"), LOW_CONF_THRESHOLD
                )
                legacy_flag = map_semantics_to_flag(relation, confidence_state)

                edge_records.append((
                    source_claim_id,
                    target_claim_id,
                    {
                        "support_score": support,
                        "contradiction_score": contradict,
                        "confidence": confidence,
                        "verifier_status": match.get("verifier_status", "CONFIRMED"),
                        "relation_type": relation,
                        "confidence_state": confidence_state,
                        "verifier_state": verifier_state,
                        "flag": legacy_flag,
                        "user_override": False,
                    },
                ))

        # ── Single bulk DB write off the event loop via run_in_executor ──
        # bulk_upsert_edges opens ONE session and commits ALL edges in ONE
        # transaction instead of N separate round-trips.
        if edge_records:
            loop = asyncio.get_running_loop()
            edge_count = await loop.run_in_executor(
                None,
                bulk_upsert_edges,
                edge_records,
            )
            print(f"[LANGGRAPH-WORKFLOW] Persisted {edge_count}/{len(edge_records)} edges in one transaction.")

    return comparison_results
