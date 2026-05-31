# graph_engine.py
from GraphEngine.db.crud import create_edge
from GraphEngine.utils.helpers import (
    derive_relation_type,
    derive_confidence_state,
    derive_verifier_state,
    map_semantics_to_flag,
)


def add_graph_edge(edge):
    relation = derive_relation_type(edge.support_score, edge.contradiction_score)
    confidence_state = derive_confidence_state(edge.confidence)
    verifier_state = derive_verifier_state(edge.verifier_status)

    # Build payload with new semantic dimensions and legacy flag for compatibility
    payload = {
        "source_id": edge.source_id,
        "target_id": edge.target_id,
        "support_score": edge.support_score,
        "contradiction_score": edge.contradiction_score,
        "confidence": edge.confidence,
        "relation_type": relation,
        "confidence_state": confidence_state,
        "verifier_state": verifier_state,
        "verifier_status": edge.verifier_status,
        "flag": map_semantics_to_flag(relation, confidence_state),
        "user_override": False,
    }

    create_edge(payload)

    return {
        "message": "edge added",
        "relation_type": relation,
        "confidence_state": confidence_state,
        "verifier_state": verifier_state,
    }