# confidence_engine.py

# Weights must sum to 1.0.
_W_RETRIEVAL = 0.4
_W_ANALYST = 0.3
_W_VERIFIER = 0.3

_VERIFIER_SCORE_MAP: dict[str, float] = {
    "CONFIRMED": 1.0,
    "SCOPE_MISMATCH": 0.5,
    "REJECTED": 0.0,
}


def verifier_score(status: str) -> float:
    """Map a verifier status string to a numeric score in [0, 1]."""
    return _VERIFIER_SCORE_MAP.get(status, 0.0)


def compute_confidence(
    rerank_distance: float,
    analyst_strength: float,
    verifier_status: str,
) -> float:
    """
    Compute a combined confidence score in [0, 1].

    Args:
        rerank_distance:  Cosine distance from ChromaDB (0 = identical, 2 = opposite).
                          Converted to similarity by: similarity = 1 - (distance / 2).
        analyst_strength: Max of support_score and contradiction_score from analyst.
        verifier_status:  "CONFIRMED" | "SCOPE_MISMATCH" | "REJECTED".

    Returns:
        Weighted confidence float in [0, 1].
    """
    # Convert cosine distance → similarity so that small distance = high score.
    retrieval_sim = max(0.0, 1.0 - (rerank_distance / 2.0))

    return (
        _W_RETRIEVAL * retrieval_sim
        + _W_ANALYST * analyst_strength
        + _W_VERIFIER * verifier_score(verifier_status)
    )