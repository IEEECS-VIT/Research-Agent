# relation_engine.py
from GraphEngine.db.crud import get_edges


def infer_relation(p1: str, p2: str) -> dict:
    """
    Infer the relationship between two documents by finding the direct
    graph edge that connects them.

    Args:
        p1: source_id or target_id of the first document.
        p2: source_id or target_id of the second document.

    Returns:
        Dict with:
            relation  – "AGREE" | "DISAGREE" | "MIXED" | "unknown"
            flag      – edge flag if found, else None
            confidence – edge confidence if found, else None
    """
    edges = get_edges()

    # Look for a direct edge between p1 and p2 in either direction.
    direct = next(
        (
            e for e in edges
            if (e.source_id == p1 and e.target_id == p2)
            or (e.source_id == p2 and e.target_id == p1)
        ),
        None,
    )

    if not direct:
        return {"relation": "unknown", "flag": None, "confidence": None}

    # Derive relation from the stored flag (set by graph_engine via helpers.derive_flag).
    flag = direct.flag
    if flag == "SUPPORT":
        relation = "AGREE"
    elif flag == "CONTRADICT":
        relation = "DISAGREE"
    else:
        relation = "MIXED"

    return {
        "relation": relation,
        "flag": flag,
        "confidence": direct.confidence,
    }