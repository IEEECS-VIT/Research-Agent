# Input:  verdict + contradiction_severity + confidence (from analyst_llm.py)
#         OR logic_llm_output (from contradiction_verifier.py)
# Output: Flag string — GREEN | YELLOW | ORANGE | RED | ESCALATE

import logging
from dataclasses import dataclass

logger = logging.getLogger("flag_generator")

# Thresholds
HIGH_CONFIDENCE  = 0.85
MID_CONFIDENCE   = 0.70


# Flag Result 
@dataclass
class FlagResult:
    flag:   str    # GREEN | YELLOW | ORANGE | RED | ESCALATE
    reason: str    # human-readable explanation of why this flag was assigned


# Core Flag Logic 
def generate_flag(
    verdict: str,
    contradiction_severity: str,
    confidence: float
) -> str:
    """
    Assigns a flag color based on verdict, severity, and confidence.
    This function is purely deterministic — no LLM calls.

    Rules:
    ┌─────────────────────────────────────────────────────────────────┐
    │ confidence < 0.70                → ESCALATE (always)            │
    │ support    + confidence >= 0.85  → GREEN                        │
    │ support    + confidence 0.70-0.84→ YELLOW                       │
    │ neutral    + any valid confidence→ YELLOW                       │
    │ contradict + minor  + conf>=0.70 → ORANGE                       │
    │ contradict + direct + conf>=0.85 → RED                          │
    │ contradict + direct + conf<0.85  → ORANGE (not enough certainty)│
    │ anything unrecognized            → ESCALATE                     │
    └─────────────────────────────────────────────────────────────────┘

    Returns flag string only. Use generate_flag_with_reason() for audit trail.
    """
    result = generate_flag_with_reason(verdict, contradiction_severity, confidence)
    return result.flag


def generate_flag_with_reason(
    verdict: str,
    contradiction_severity: str,
    confidence: float
) -> FlagResult:
    """
    Same logic as generate_flag() but returns FlagResult with reason.
    Use this when you need the audit trail.
    """

    # Gate 1 — confidence floor
    if confidence < MID_CONFIDENCE:
        return FlagResult(
            flag="ESCALATE",
            reason=f"Confidence {confidence:.2f} below floor {MID_CONFIDENCE}. "
                   f"Human review required."
        )

    # Gate 2 — support verdicts
    if verdict == "support":
        if confidence >= HIGH_CONFIDENCE:
            return FlagResult(
                flag="GREEN",
                reason=f"Strong support. confidence={confidence:.2f} >= {HIGH_CONFIDENCE}."
            )
        else:
            return FlagResult(
                flag="YELLOW",
                reason=f"Weak support. confidence={confidence:.2f} between "
                       f"{MID_CONFIDENCE} and {HIGH_CONFIDENCE}."
            )

    # Gate 3 — neutral verdict
    if verdict == "neutral":
        return FlagResult(
            flag="YELLOW",
            reason=f"Neutral relationship. confidence={confidence:.2f}."
        )

    # Gate 4 — contradiction verdicts
    if verdict == "contradict":
        if contradiction_severity == "direct":
            if confidence >= HIGH_CONFIDENCE:
                return FlagResult(
                    flag="RED",
                    reason=f"Direct contradiction confirmed. "
                           f"confidence={confidence:.2f} >= {HIGH_CONFIDENCE}."
                )
            else:
                # Direct contradiction but not certain enough for RED
                return FlagResult(
                    flag="ORANGE",
                    reason=f"Direct contradiction suspected but confidence "
                           f"{confidence:.2f} below {HIGH_CONFIDENCE}. "
                           f"Downgraded to ORANGE."
                )

        if contradiction_severity == "minor":
            return FlagResult(
                flag="ORANGE",
                reason=f"Minor contradiction. confidence={confidence:.2f}."
            )

        # contradiction_severity is null or unrecognized
        return FlagResult(
            flag="ESCALATE",
            reason=f"Contradiction detected but severity='{contradiction_severity}' "
                   f"is unresolved. Escalating."
        )

    # Gate 5 — unrecognized verdict
    logger.warning(f"Unrecognized verdict: '{verdict}'. Escalating.")
    return FlagResult(
        flag="ESCALATE",
        reason=f"Unrecognized verdict: '{verdict}'."
    )


# Post-Logic-LLM Upgrade 
def upgrade_flag_after_verification(
    current_flag: str,
    logic_llm_output: str,
    confidence: float
) -> FlagResult:
    """
    Called by contradiction_verifier.py after Logic LLM runs.
    Adjusts the flag based on verification result.

    logic_llm_output options:
        CONFIRMED      → contradiction is real, keep or upgrade flag
        REJECTED       → contradiction was false, downgrade to YELLOW
        SCOPE_MISMATCH → different populations/contexts, escalate

    Only called when current_flag is ORANGE or RED.
    """

    if logic_llm_output == "CONFIRMED":
        # Verification confirmed — keep current flag
        logger.info(f"Logic LLM confirmed contradiction. Flag stays: {current_flag}")
        return FlagResult(
            flag=current_flag,
            reason=f"Contradiction verified by Logic LLM. Flag confirmed: {current_flag}."
        )

    if logic_llm_output == "REJECTED":
        # False contradiction detected — downgrade
        logger.info(
            f"Logic LLM rejected contradiction. Downgrading {current_flag} → YELLOW."
        )
        return FlagResult(
            flag="YELLOW",
            reason=f"Logic LLM rejected contradiction claim. "
                   f"Downgraded from {current_flag} to YELLOW."
        )

    if logic_llm_output == "SCOPE_MISMATCH":
        # Different populations/contexts — escalate
        logger.info(
            f"Logic LLM detected scope mismatch. Escalating {current_flag}."
        )
        return FlagResult(
            flag="ESCALATE",
            reason=f"Logic LLM detected scope mismatch (different populations "
                   f"or contexts). Human review required."
        )

    # Unrecognized output from Logic LLM — escalate safely
    logger.warning(
        f"Unrecognized Logic LLM output: '{logic_llm_output}'. Escalating."
    )
    return FlagResult(
        flag="ESCALATE",
        reason=f"Unrecognized Logic LLM output: '{logic_llm_output}'."
    )


# Utility
def flag_requires_logic_llm(flag: str) -> bool:
    """
    Returns True if this flag should be sent to the Logic LLM for verification.
    Only ORANGE and RED flags need verification.
    """
    return flag in {"ORANGE", "RED"}


def flag_display(flag: str) -> str:
    """Returns a human-readable label with emoji for UI display."""
    display_map = {
        "GREEN":    "🟢 GREEN — Supports draft",
        "YELLOW":   "🟡 YELLOW — Neutral or weak support",
        "ORANGE":   "🟠 ORANGE — Minor contradiction",
        "RED":      "🔴 RED — Direct contradiction",
        "ESCALATE": "⚠️  ESCALATE — Requires human review"
    }
    return display_map.get(flag, f"❓ UNKNOWN FLAG: {flag}")


# Entry Point
if __name__ == "__main__":
    # Smoke test — covers all branches
    test_cases = [
        ("support",    "null",   0.91),   # → GREEN
        ("support",    "null",   0.75),   # → YELLOW
        ("neutral",    "null",   0.80),   # → YELLOW
        ("contradict", "minor",  0.73),   # → ORANGE
        ("contradict", "direct", 0.88),   # → RED
        ("contradict", "direct", 0.78),   # → ORANGE (not certain enough for RED)
        ("support",    "null",   0.55),   # → ESCALATE (below floor)
        ("contradict", "null",   0.75),   # → ESCALATE (severity unresolved)
    ]

    print("=== Flag Generation Smoke Test ===\n")
    for verdict, severity, conf in test_cases:
        result = generate_flag_with_reason(verdict, severity, conf)
        print(
            f"verdict={verdict:<12} severity={severity:<8} "
            f"conf={conf:.2f} → {flag_display(result.flag)}"
        )
        print(f"  reason: {result.reason}\n")

    print("\n=== Post-Verification Upgrade Test ===\n")
    upgrade_cases = [
        ("RED",    "CONFIRMED"),
        ("ORANGE", "REJECTED"),
        ("RED",    "SCOPE_MISMATCH"),
    ]
    for flag, logic_output in upgrade_cases:
        result = upgrade_flag_after_verification(flag, logic_output, 0.88)
        print(
            f"flag={flag:<8} logic_llm={logic_output:<16} "
            f"→ {flag_display(result.flag)}"
        )
        print(f"  reason: {result.reason}\n")