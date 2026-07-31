# retrieval_engine.py
import os
from pinecone import Pinecone
from GraphEngine.utils.constants import TOP_K, CHUNK_TYPE
from app.core.config import get_settings

_pc = None
_index = None

def _get_index():
    """Get or create the Pinecone index, lazy-loaded on first use."""
    global _pc, _index
    if _index is None:
        settings = get_settings()
        if not settings.pinecone_api_key:
            raise ValueError("PINECONE_API_KEY is not set.")
        _pc = Pinecone(api_key=settings.pinecone_api_key)
        _index = _pc.Index(settings.pinecone_index_name)
    return _index


def _build_pinecone_filter(
    source_type: str | None = None,
    chunk_type: str | None = None,
    version_id: str | None = None,
) -> dict | None:
    """Build a Pinecone metadata filter.

    Pinecone supports MongoDB-like query operators ($eq, $in).
    """
    conditions = []

    if source_type:
        conditions.append({"source_type": {"$eq": source_type}})
    if chunk_type:
        conditions.append({"content_type": {"$eq": chunk_type}})
    if version_id:
        conditions.append({"version_id": {"$eq": version_id}})

    if not conditions:
        return None
    if len(conditions) == 1:
        return conditions[0]
    return {"$and": conditions}


def retrieve_chunks(
    query_embedding: list[float],
    source_type: str | None = None,
    chunk_type: str | None = CHUNK_TYPE,
    version_id: str | None = None,
    n_results: int = TOP_K,
) -> dict:
    """
    Query Pinecone with metadata-aware cosine similarity retrieval.

    This function wraps Pinecone's API but returns data in the same format
    expected by the original ChromaDB implementation to avoid breaking changes.

    Args:
        query_embedding: Pre-computed Gemini embedding vector (dim=3072).
        source_type:     Filter by "source_type": "draft" or "paper" (or None to skip).
        chunk_type:      Filter by "content_type": "summary" or "raw_text" (or None for both).
        version_id:      Filter by "version_id" (or None to skip).
        n_results:       Number of nearest neighbours to return.

    Returns:
        Raw ChromaDB-style result dict with keys:
            documents   – list[list[str]]
            metadatas   – list[list[dict]]
            distances   – list[list[float]]
            ids         – list[list[str]]
    """
    filter_clause = _build_pinecone_filter(
        source_type=source_type,
        chunk_type=chunk_type,
        version_id=version_id,
    )

    index = _get_index()
    
    query_kwargs = {
        "vector": query_embedding,
        "top_k": n_results,
        "include_metadata": True
    }
    if filter_clause:
        query_kwargs["filter"] = filter_clause

    response = index.query(**query_kwargs)
    
    # Translate Pinecone response back to ChromaDB format
    documents = []
    metadatas = []
    distances = []
    ids = []
    
    for match in response.get("matches", []):
        meta = match.get("metadata", {})
        # ChromaDB distance = 1 - cosine_similarity (for cosine metric)
        # Pinecone returns similarity score, so distance = 1 - score
        dist = 1.0 - match.get("score", 0.0)
        
        documents.append(meta.get("text", ""))
        metadatas.append(meta)
        distances.append(dist)
        ids.append(match.get("id"))
        
    return {
        "documents": [documents],
        "metadatas": [metadatas],
        "distances": [distances],
        "ids": [ids]
    }


def retrieve_cross_type(
    query_embedding: list[float],
    source_doc_type: str,
    chunk_type: str | None = CHUNK_TYPE,
    version_id: str | None = None,
    n_results: int = TOP_K,
) -> dict:
    """
    Enforce cross-type retrieval (Draft → Paper or Paper → Draft).

    Given the source document's type, this always queries the *opposite* type
    so that draft↔draft and paper↔paper comparisons are impossible.
    """
    if source_doc_type not in ("draft", "paper"):
        raise ValueError("source_doc_type must be 'draft' or 'paper'.")

    target_type = "paper" if source_doc_type == "draft" else "draft"
    return retrieve_chunks(
        query_embedding=query_embedding,
        source_type=target_type,
        chunk_type=chunk_type,
        version_id=version_id,
        n_results=n_results,
    )


def retrieve_by_claim_embedding(
    claim_embedding: list[float],
    source_doc_type: str,
    query_version_id: str | None = None,
    chunk_type: str | None = CHUNK_TYPE,
    n_results: int = TOP_K,
) -> dict:
    """
    Retrieve top-K candidate claims/chunks for a given claim embedding.
    """
    return retrieve_cross_type(
        query_embedding=claim_embedding,
        source_doc_type=source_doc_type,
        chunk_type=chunk_type,
        version_id=query_version_id,
        n_results=n_results,
    )