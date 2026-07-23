# helpers.py
from GraphEngine.utils.constants import (
    SUPPORT_THRESHOLD,
    CONTRADICT_THRESHOLD
)


def derive_relation_type(support: float, contradict: float) -> str:
    """Determine the semantic relation between two claims.

    Returns one of: 'CONTRADICT', 'SUPPORT', 'MIXED'
    """
    if contradict >= CONTRADICT_THRESHOLD:
        return "CONTRADICT"

    if support >= SUPPORT_THRESHOLD:
        return "SUPPORT"

    return "MIXED"


def derive_confidence_state(confidence: float, verifier_status: str | None = None, low_conf_threshold: float = 0.5) -> str:
    """Map a numeric confidence and verifier hints into a discrete confidence state.

    Returns one of: 'HIGH_CONFIDENCE', 'LOW_CONFIDENCE', 'REVIEW_REQUIRED'
    """
    if confidence is None:
        return "REVIEW_REQUIRED"

    # If verifier raised scope mismatch, mark for review
    if isinstance(verifier_status, str) and verifier_status.upper() == "SCOPE_MISMATCH":
        return "REVIEW_REQUIRED"

    if confidence < low_conf_threshold:
        return "LOW_CONFIDENCE"

    return "HIGH_CONFIDENCE"


def derive_verifier_state(verifier_status: str | None) -> str:
    """Normalize verifier statuses into a discrete verifier_state.

    Expected outputs: 'CONFIRMED', 'REJECTED', 'SCOPE_MISMATCH'
    """
    if not verifier_status:
        return "CONFIRMED"

    vs = verifier_status.upper()
    if vs in ("REJECTED", "REFUTED"):
        return "REJECTED"
    if vs == "SCOPE_MISMATCH":
        return "SCOPE_MISMATCH"
    return "CONFIRMED"


def map_semantics_to_flag(relation_type: str | None, confidence_state: str | None) -> str | None:
    """Backward-compatibility helper that synthesizes the deprecated `flag` value
    from the new semantic dimensions. This is transitional and should be removed
    after consumers migrate.
    """
    if relation_type is None and confidence_state is None:
        return None

    parts = []
    if confidence_state:
        parts.append(confidence_state)
    if relation_type:
        parts.append(relation_type)

    return "_".join(parts)


def infer_relation_type_from_flag(flag: str | None) -> str | None:
    """Best-effort legacy flag parser for relation type."""
    if not flag:
        return None

    upper = flag.upper()
    if "CONTRADICT" in upper:
        return "CONTRADICT"
    if "SUPPORT" in upper:
        return "SUPPORT"
    if "MIXED" in upper:
        return "MIXED"
    return None


def infer_confidence_state_from_flag(flag: str | None, confidence: float | None = None, low_conf_threshold: float = 0.5) -> str | None:
    """Best-effort legacy flag parser for confidence state."""
    if flag:
        upper = flag.upper()
        if "LOW_CONFIDENCE" in upper:
            return "LOW_CONFIDENCE"
        if "HIGH_CONFIDENCE" in upper:
            return "HIGH_CONFIDENCE"
        if "REVIEW_REQUIRED" in upper:
            return "REVIEW_REQUIRED"

    if confidence is None:
        return None

    return "LOW_CONFIDENCE" if confidence < low_conf_threshold else "HIGH_CONFIDENCE"


def infer_verifier_state_from_flag(flag: str | None, verifier_status: str | None = None) -> str | None:
    """Legacy verifier-state inference prefers the explicit verifier_status."""
    if verifier_status:
        return derive_verifier_state(verifier_status)

    if not flag:
        return None

    upper = flag.upper()
    if "SCOPE_MISMATCH" in upper:
        return "SCOPE_MISMATCH"
    if "REJECTED" in upper:
        return "REJECTED"
    if "CONFIRMED" in upper:
        return "CONFIRMED"
    return None


def infer_semantic_dimensions(
    flag: str | None = None,
    confidence: float | None = None,
    verifier_status: str | None = None,
    low_conf_threshold: float = 0.5,
) -> dict[str, str | None]:
    """Normalize semantic dimensions from either legacy or current fields."""
    relation_type = infer_relation_type_from_flag(flag)
    confidence_state = infer_confidence_state_from_flag(flag, confidence, low_conf_threshold)
    verifier_state = infer_verifier_state_from_flag(flag, verifier_status)

    return {
        "relation_type": relation_type,
        "confidence_state": confidence_state,
        "verifier_state": verifier_state,
    }