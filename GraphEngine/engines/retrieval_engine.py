# retrieval_engine.py
import os
import chromadb
from chromadb.config import Settings
from GraphEngine.utils.constants import TOP_K, CHROMA_DB_PATH, COLLECTION_NAME, CHUNK_TYPE


class _DummyEmbeddingFunction:
    """
    ChromaDB requires an embedding function at collection-open time even when
    we supply our own pre-computed embeddings at query time.
    Must match the one used in the ingestion pipeline's isolated worker.
    """
    def __call__(self, input):
        return [[0.0] * 3072 for _ in input]

    def name(self):
        return "gemini-dummy"


# Lazy-loaded Chroma client and collection to avoid startup failures.
_client = None
_collection = None


def _get_client():
    """Get or create the persistent Chroma client."""
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(
            path=CHROMA_DB_PATH,
            settings=Settings(anonymized_telemetry=False)
        )
    return _client


def _get_collection():
    """Get or create the collection, lazy-loaded on first use."""
    global _collection
    if _collection is None:
        client = _get_client()
        _collection = client.get_collection(
            name=COLLECTION_NAME,
            embedding_function=_DummyEmbeddingFunction()
        )
    return _collection


def _build_where_clause(
    source_type: str | None = None,
    chunk_type: str | None = None,
    version_id: str | None = None,
) -> dict | None:
    """Build a ChromaDB where clause with metadata filters.

    Args:
        source_type: "draft" or "paper" or None to skip.
        chunk_type:  "summary" or "raw_text" or None to skip.
        version_id:  Document version ID or None to skip.

    Returns:
        A where clause dict suitable for Chroma queries, or None if no filters.
    """
    conditions = []

    if source_type:
        conditions.append({"source_type": source_type})
    if chunk_type:
        conditions.append({"content_type": chunk_type})
    if version_id:
        conditions.append({"version_id": version_id})

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
    Query ChromaDB with metadata-aware cosine similarity retrieval.

    Uses Chroma's default cosine distance metric to find top-K nearest neighbours
    subject to optional metadata filters.

    Args:
        query_embedding: Pre-computed Gemini embedding vector (dim=3072).
        source_type:     Filter by "source_type": "draft" or "paper" (or None to skip).
        chunk_type:      Filter by "content_type": "summary" or "raw_text" (or None for both).
        version_id:      Filter by "version_id" (or None to skip).
        n_results:       Number of nearest neighbours to return.

    Returns:
        Raw ChromaDB result dict with keys:
            documents   – list[list[str]]
            metadatas   – list[list[dict]]
            distances   – list[list[float]]
            ids         – list[list[str]]
    """
    where_clause = _build_where_clause(
        source_type=source_type,
        chunk_type=chunk_type,
        version_id=version_id,
    )

    query_kwargs: dict = dict(
        query_embeddings=[query_embedding],
        n_results=n_results,
        include=["documents", "metadatas", "distances"],
    )
    if where_clause:
        query_kwargs["where"] = where_clause

    collection = _get_collection()
    return collection.query(**query_kwargs)


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

    Args:
        query_embedding: Embedding of a chunk from the source document.
        source_doc_type: "draft" or "paper" — the type of the query document.
        chunk_type:      "summary" | "raw_text" | None.
        version_id:      Optional version ID to filter by (e.g., to query only a specific version).
        n_results:       Number of neighbours to return.
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

    This is the primary retrieval API for claim-level reasoning. It enforces
    cross-type retrieval (Draft → Paper or vice versa) and supports version-aware
    filtering. Uses cosine similarity via Chroma's default distance metric.

    Example usage:
        # Given a claim from a draft document, find supporting/contradicting claims
        # from papers in the same version:
        result = retrieve_by_claim_embedding(
            claim_embedding=gemini_embedding_vector,
            source_doc_type="draft",
            query_version_id="3",
            chunk_type="summary",
            n_results=15
        )

    Args:
        claim_embedding:  Pre-computed Gemini embedding (dim=3072).
        source_doc_type:  "draft" or "paper" — the source document type.
        query_version_id: Filter to only chunks from this version (or None for all versions).
        chunk_type:       "summary" or "raw_text" or None for both.
        n_results:        Number of top-K results.

    Returns:
        ChromaDB query result dict with keys:
            documents   – list[list[str]]  (chunk texts)
            metadatas   – list[list[dict]] (chunk metadata including doc_id, version_id, section_name)
            distances   – list[list[float]] (cosine distances, 0 = identical, 2 = opposite)
            ids         – list[list[str]]  (chunk IDs)
    """
    return retrieve_cross_type(
        query_embedding=claim_embedding,
        source_doc_type=source_doc_type,
        chunk_type=chunk_type,
        version_id=query_version_id,
        n_results=n_results,
    )