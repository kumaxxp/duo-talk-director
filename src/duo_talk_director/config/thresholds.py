"""Threshold configuration for LLM-based Director (Phase 2.2)

Defines thresholds for determining PASS/WARN/RETRY status.
"""

from dataclasses import dataclass

from ..interfaces import DirectorStatus, LLMEvaluationScore


@dataclass
class ThresholdConfig:
    """Threshold configuration for status determination.

    Attributes:
        retry_overall: Overall score below this triggers RETRY
        retry_character: character_consistency below this triggers RETRY
        retry_relationship: relationship_quality below this triggers RETRY
        warn_overall: Overall score below this triggers WARN (if above retry)
    """

    retry_overall: float = 0.4
    retry_character: float = 0.3
    retry_relationship: float = 0.3
    warn_overall: float = 0.6


def determine_status(
    score: LLMEvaluationScore,
    config: ThresholdConfig,
) -> DirectorStatus:
    """Determine Director status from LLM evaluation score.

    Priority:
    1. Critical individual metrics (character, relationship) trigger RETRY
    2. Overall score thresholds (RETRY < WARN < PASS)

    Args:
        score: LLMEvaluationScore with 5-axis scores
        config: ThresholdConfig with threshold values

    Returns:
        DirectorStatus (PASS, WARN, or RETRY)
    """
    # Individual metric critical failures
    if score.character_consistency < config.retry_character:
        return DirectorStatus.RETRY

    if score.relationship_quality < config.retry_relationship:
        return DirectorStatus.RETRY

    # Overall score thresholds
    if score.overall_score < config.retry_overall:
        return DirectorStatus.RETRY

    if score.overall_score < config.warn_overall:
        return DirectorStatus.WARN

    return DirectorStatus.PASS


def build_reason(
    score: LLMEvaluationScore,
    status: DirectorStatus,
) -> str:
    """Build human-readable reason string for evaluation.

    Args:
        score: LLMEvaluationScore with metrics
        status: Determined DirectorStatus

    Returns:
        Reason string explaining the evaluation
    """
    parts = [f"LLM evaluation: overall={score.overall_score:.2f}"]

    # Add metric breakdown
    metrics = [
        f"char={score.character_consistency:.2f}",
        f"novelty={score.topic_novelty:.2f}",
        f"rel={score.relationship_quality:.2f}",
        f"nat={score.naturalness:.2f}",
        f"conc={score.concreteness:.2f}",
    ]
    parts.append(f"({', '.join(metrics)})")

    # Add issues if any
    if score.issues:
        issues_text = "; ".join(score.issues[:3])  # Limit to 3
        parts.append(f"Issues: {issues_text}")

    # Add status-specific message
    if status == DirectorStatus.RETRY:
        parts.insert(0, "[RETRY]")
    elif status == DirectorStatus.WARN:
        parts.insert(0, "[WARN]")
    else:
        parts.insert(0, "[PASS]")

    return " ".join(parts)
