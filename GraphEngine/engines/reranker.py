# reranker.py
from typing import Any


def rerank(
    results: dict,
    top_n: int = 8,
) -> list[tuple[str, float, dict]]:
    """
    Sort ChromaDB results by cosine distance (ascending = most similar first)
    and return the top_n results as (text, distance, metadata) triples.

    Args:
        results: Raw dict returned by retrieval_engine.retrieve_chunks / retrieve_cross_type.
                 Expected keys: documents[0], distances[0], metadatas[0].
        top_n:   How many top results to keep after sorting.

    Returns:
        List of (text, distance, metadata) triples, sorted best-first.
    """
    docs: list[str] = results["documents"][0]
    scores: list[float] = results["distances"][0]
    metas: list[dict[str, Any]] = results["metadatas"][0]

    # ChromaDB cosine distance: 0 = identical, 2 = opposite.
    # Sort ascending so the most relevant chunks come first.
    paired = sorted(zip(docs, scores, metas), key=lambda x: x[1])

    return paired[:top_n]