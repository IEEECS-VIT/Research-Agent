# relation_engine.py
from GraphEngine.db.crud import get_edge_direct


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
    # Targeted SQLite WHERE query — O(1) indexed lookup instead of full
    # table scan + Python iteration over all edges.
    direct = get_edge_direct(p1, p2)

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