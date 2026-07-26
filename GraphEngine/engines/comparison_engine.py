"""
Automatic draft→paper claim comparison orchestrator.

Flow:
  1. For each claim extracted from a document
  2. Compute its embedding via Gemini
  3. Retrieve top-K opposing claims using metadata-aware retrieval
  4. Score each match with Analyst + Verifier
  5. Compute confidence as weighted combination of retrieval + analyst + verifier
  6. Return structured comparison results
"""

import os
import asyncio
from typing import Any
from GraphEngine.utils.gemini_client import _get_client

from GraphEngine.engines.retrieval_engine import retrieve_by_claim_embedding
from GraphEngine.engines.evaluator import evaluate_async
from GraphEngine.engines.confidence_engine import compute_confidence
from GraphEngine.utils.constants import TOP_K, EMBEDDING_DIM, CHUNK_TYPE, CANDIDATE_DISTANCE_THRESHOLD


class ComparisonResult:
    """Result of comparing a claim against retrieved candidates."""

    def __init__(
        self,
        claim_id: str,
        claim_text: str,
        source_doc_type: str,
        version_id: str,
        matches: list[dict],  # [{ retrieved_id, retrieved_text, metadata, support_score, contradiction_score, verifier_status, distance }]
    ):
        self.claim_id = claim_id
        self.claim_text = claim_text
        self.source_doc_type = source_doc_type
        self.version_id = version_id
        self.matches = matches

    def to_dict(self) -> dict:
        # Strip internal engine flags before serialization so the output
        # always conforms to the ClaimMatch schema in ingestion_pipeline/schemas.py.
        _INTERNAL_KEYS = {"skipped_by_distance_filter"}
        clean_matches = [
            {k: v for k, v in m.items() if k not in _INTERNAL_KEYS}
            for m in self.matches
        ]
        return {
            "claim_id": self.claim_id,
            "claim_text": self.claim_text,
            "source_doc_type": self.source_doc_type,
            "version_id": self.version_id,
            "match_count": len(clean_matches),
            "matches": clean_matches,
        }


async def compute_claim_embedding(claim_text: str) -> list[float]:
    """Compute a Gemini embedding for a claim using the shared API client."""
    client = _get_client()  # shared client — no new HTTP session per claim
    max_retries = 3
    delay = 1

    for attempt in range(max_retries):
        try:
            response = await client.aio.models.embed_content(
                model="gemini-embedding-2",
                contents=claim_text,
            )

            if not getattr(response, "embeddings", None) or not response.embeddings:
                raise ValueError("API returned empty embeddings.")

            emb = response.embeddings[0]
            vals = getattr(emb, "values", None) or emb
            embedding = [float(v) for v in vals]

            if len(embedding) != EMBEDDING_DIM:
                raise ValueError(
                    f"Embedding dimension mismatch: got {len(embedding)}, expected {EMBEDDING_DIM}"
                )

            return embedding

        except Exception as e:
            err = str(e).lower()
            print(f"[COMPARISON] Embedding error (attempt {attempt+1}): {e}")
            if any(x in err for x in ("429", "quota", "exhausted")):
                if attempt < max_retries - 1:
                    await asyncio.sleep(delay)
                    delay *= 2
                    continue
                else:
                    raise RuntimeError("Embedding rate limit exceeded.") from e
            else:
                raise

    raise RuntimeError("Failed to compute embedding after retries.")


async def compare_claim_against_candidates(
    claim_id: str,
    claim_text: str,
    claim_embedding: list[float],
    source_doc_type: str,
    version_id: str,
    retrieved_results: dict,
) -> ComparisonResult:
    """Score a claim against retrieved candidates using Analyst + Verifier.

    Args:
        claim_id: Unique ID for the claim.
        claim_text: Assertion text.
        claim_embedding: Pre-computed embedding.
        source_doc_type: "draft" or "paper".
        version_id: Document version.
        retrieved_results: Return value from retrieve_by_claim_embedding().

    Returns:
        ComparisonResult with matches scored and verified.
    """
    matches = []

    if not retrieved_results.get("documents") or not retrieved_results["documents"][0]:
        print(f"[COMPARISON] No candidates retrieved for claim {claim_id}.")
        return ComparisonResult(
            claim_id=claim_id,
            claim_text=claim_text,
            source_doc_type=source_doc_type,
            version_id=version_id,
            matches=[],
        )

    documents = retrieved_results["documents"][0]
    metadatas = retrieved_results["metadatas"][0]
    distances = retrieved_results["distances"][0]
    ids = retrieved_results["ids"][0]

    loop = asyncio.get_running_loop()  # still used by retrieve_by_claim_embedding below
    total_matches = len(documents)
    print(
        f"[COMPARISON] Claim {claim_id}: scoring {total_matches} candidates concurrently..."
    )

    # ── Concurrent candidate scoring ──────────────────────────────────────
    # Each candidate is scored in its own coroutine so all TOP_K candidates
    # for a given claim are evaluated in parallel instead of sequentially.
    # A None return signals a scoring failure for that candidate.
    async def _score_candidate(
        doc: str, meta: dict, dist: float, rid: str
    ) -> dict | None:
        try:
            # ── Distance pre-filter ────────────────────────────────────────
            # If the cosine distance is above the threshold the candidate is
            # too dissimilar to be worth an LLM call. Return a cheap default
            # record so it is still visible in the graph but clearly flagged.
            if dist > CANDIDATE_DISTANCE_THRESHOLD:
                confidence = compute_confidence(
                    rerank_distance=dist,
                    analyst_strength=0.5,
                    verifier_status="SCOPE_MISMATCH",
                )
                return {
                    "retrieved_id": rid,
                    "retrieved_text": doc[:500],
                    "metadata": meta,
                    "cosine_distance": dist,
                    "support_score": 0.5,
                    "contradiction_score": 0.5,
                    "verifier_status": "SCOPE_MISMATCH",
                    "confidence": confidence,
                    "skipped_by_distance_filter": True,
                }

            # Native async call — no thread-pool executor needed.
            evaluation = await evaluate_async(claim_text, doc, meta_a=None, meta_b=meta)
            analyst_strength = max(
                evaluation.get("support_score", 0.0),
                evaluation.get("contradiction_score", 0.0),
            )
            confidence = compute_confidence(
                rerank_distance=dist,
                analyst_strength=analyst_strength,
                verifier_status=evaluation["verifier_status"],
            )
            return {
                "retrieved_id": rid,
                "retrieved_text": doc[:500],
                "metadata": meta,
                "cosine_distance": dist,
                "support_score": evaluation["support_score"],
                "contradiction_score": evaluation["contradiction_score"],
                "verifier_status": evaluation["verifier_status"],
                "confidence": confidence,
                "skipped_by_distance_filter": False,
            }
        except Exception as exc:
            print(f"[COMPARISON] Error scoring candidate {rid}: {exc}")
            return None

    scored = await asyncio.gather(
        *[
            _score_candidate(doc, meta, dist, rid)
            for doc, meta, dist, rid in zip(documents, metadatas, distances, ids)
        ]
    )

    # Filter out failed candidates (None values)
    matches = [m for m in scored if m is not None]
    skipped = sum(1 for m in matches if m.get("skipped_by_distance_filter"))
    llm_scored = len(matches) - skipped
    print(
        f"[COMPARISON] Claim {claim_id}: {llm_scored} LLM-scored, "
        f"{skipped} distance-filtered (threshold={CANDIDATE_DISTANCE_THRESHOLD}), "
        f"{total_matches - len(matches)} failed."
    )

    return ComparisonResult(
        claim_id=claim_id,
        claim_text=claim_text,
        source_doc_type=source_doc_type,
        version_id=version_id,
        matches=matches,
    )


async def compare_document(
    claims: list[dict],
    source_doc_type: str,
    version_id: str,
    chunk_type: str | None = CHUNK_TYPE,
    n_results: int = TOP_K,
) -> list[ComparisonResult]:
    """Orchestrate automatic comparison of all claims in a document.

    Args:
        claims: List of claim dicts with fields: { claim_id, assertion, subject, context }.
        source_doc_type: "draft" or "paper".
        version_id: Document version ID.
        chunk_type: "summary" or "raw_text" or None.
        n_results: Top-K candidates to retrieve.

    Returns:
        List of ComparisonResult objects, one per claim.
    """
    if not claims:
        print("[COMPARISON] No claims to compare.")
        return []

    print(f"[COMPARISON] Comparing {len(claims)} claims for doc type={source_doc_type}, version={version_id}...")

    comparison_results = []

    for claim in claims:
        claim_id = claim.get("claim_id") or str(len(comparison_results))
        claim_text = claim.get("assertion", "")

        if not claim_text or not claim_text.strip():
            print(f"[COMPARISON] Skipping empty claim {claim_id}.")
            continue

        try:
            # 1. Compute embedding
            claim_embedding = await compute_claim_embedding(claim_text)

            # 2. Retrieve top-K
            retrieved = retrieve_by_claim_embedding(
                claim_embedding=claim_embedding,
                source_doc_type=source_doc_type,
                query_version_id=None,
                chunk_type=chunk_type,
                n_results=n_results,
            )

            # 3. Score and verify
            result = await compare_claim_against_candidates(
                claim_id=claim_id,
                claim_text=claim_text,
                claim_embedding=claim_embedding,
                source_doc_type=source_doc_type,
                version_id=version_id,
                retrieved_results=retrieved,
            )

            comparison_results.append(result)

            # Gentle rate-limit compliance
            await asyncio.sleep(0.1)

        except Exception as e:
            print(f"[COMPARISON] Error comparing claim {claim_id}: {e}")
            # Add partial result with no matches
            comparison_results.append(
                ComparisonResult(
                    claim_id=claim_id,
                    claim_text=claim_text,
                    source_doc_type=source_doc_type,
                    version_id=version_id,
                    matches=[],
                )
            )

    print(f"[COMPARISON] Completed comparison for {len(comparison_results)} claims.")
    return comparison_results


def persist_comparison_edges(comparison_results: list["ComparisonResult"], source_doc_id: str) -> int:
    """Persist comparison results as edges in the graph database.
    
    Args:
        comparison_results: List of ComparisonResult objects.
        source_doc_id: The document ID of the source (so we can generate claim IDs).
    
    Returns:
        Number of edges persisted.
    """
    try:
        from GraphEngine.db.crud import upsert_edge
    except ImportError:
        print("[COMPARISON] GraphEngine.db not available. Skipping edge persistence.")
        return 0
    
    edge_count = 0
    for result in comparison_results:
        for match in result.matches:
            source_claim_id = f"{source_doc_id}_{result.claim_id}"
            target_claim_id = match.get("retrieved_id", "")
            from GraphEngine.utils.helpers import (
                derive_relation_type,
                derive_confidence_state,
                derive_verifier_state,
                map_semantics_to_flag,
            )

            support = match.get("support_score", 0.0)
            contradict = match.get("contradiction_score", 0.0)
            confidence = match.get("confidence", 0.0)

            relation = derive_relation_type(support, contradict)
            verifier_state = derive_verifier_state(match.get("verifier_status"))
            confidence_state = derive_confidence_state(confidence, match.get("verifier_status"))

            edge_data = {
                "support_score": support,
                "contradiction_score": contradict,
                "confidence": confidence,
                "verifier_status": match.get("verifier_status", "CONFIRMED"),

                "relation_type": relation,
                "confidence_state": confidence_state,
                "verifier_state": verifier_state,

                "flag": map_semantics_to_flag(relation, confidence_state),
                "user_override": False,
            }
            
            if upsert_edge(source_claim_id, target_claim_id, edge_data):
                edge_count += 1
    
    print(f"[COMPARISON] Persisted {edge_count} edges to graph database.")
    return edge_count
