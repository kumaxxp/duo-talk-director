"""Director interfaces and data types

Defines the protocol for Director implementations and evaluation results.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class DirectorStatus(str, Enum):
    """Evaluation status from Director"""

    PASS = "PASS"  # Quality OK, no intervention needed
    WARN = "WARN"  # Minor issues, but acceptable
    RETRY = "RETRY"  # Regenerate response required
    MODIFY = "MODIFY"  # Critical issue, may need to stop


@dataclass
class DirectorEvaluation:
    """Result of Director evaluation

    Attributes:
        status: Evaluation status (PASS, WARN, RETRY, MODIFY)
        reason: Human-readable explanation
        suggestion: Optional suggestion for improvement
        action: "NOOP" or "INTERVENE"
        next_instruction: Instruction to inject for next turn
        checks_passed: List of check names that passed
        checks_failed: List of check names that failed
        llm_score: Optional LLM evaluation scores (Phase 2.2)
    """

    status: DirectorStatus
    reason: str
    suggestion: Optional[str] = None
    action: str = "NOOP"
    next_instruction: Optional[str] = None
    checks_passed: list[str] = field(default_factory=list)
    checks_failed: list[str] = field(default_factory=list)
    llm_score: Optional["LLMEvaluationScore"] = None


class DirectorProtocol(ABC):
    """Protocol for Director implementations

    Director monitors dialogue quality and can:
    - Evaluate responses for quality issues
    - Request regeneration (RETRY)
    - Inject instructions for next turn (INTERVENE)
    """

    @abstractmethod
    def evaluate_response(
        self,
        speaker: str,
        response: str,
        topic: str,
        history: list[dict],
        turn_number: int,
    ) -> DirectorEvaluation:
        """Evaluate a generated response

        Args:
            speaker: Character name ("やな" or "あゆ")
            response: Generated response text
            topic: Conversation topic
            history: Previous turns as list of {speaker, content}
            turn_number: Current turn number (0-indexed)

        Returns:
            DirectorEvaluation with status and details
        """
        pass

    @abstractmethod
    def commit_evaluation(
        self,
        response: str,
        evaluation: DirectorEvaluation,
    ) -> None:
        """Commit accepted response to Director's internal state

        Called when evaluation.status is PASS or WARN.
        Used for tracking topic state, novelty history, etc.

        Args:
            response: The accepted response
            evaluation: The evaluation result
        """
        pass

    @abstractmethod
    def reset_for_new_session(self) -> None:
        """Reset state for a new dialogue session

        Clears topic state, novelty history, etc.
        """
        pass


@dataclass
class LLMEvaluationScore:
    """LLM-based 5-axis evaluation scores (Phase 2.2)

    Attributes:
        character_consistency: Character setting consistency (0.0-1.0)
        topic_novelty: Topic freshness and variety (0.0-1.0)
        relationship_quality: Sibling relationship expression (0.0-1.0)
        naturalness: Natural dialogue flow (0.0-1.0)
        concreteness: Information specificity (0.0-1.0)
        overall_score: Weighted average of all metrics (0.0-1.0)
        issues: List of detected problems
        strengths: List of good points
    """

    character_consistency: float
    topic_novelty: float
    relationship_quality: float
    naturalness: float
    concreteness: float
    overall_score: float = 0.0
    issues: list[str] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)

    def __post_init__(self):
        """Calculate overall_score if not provided"""
        if self.overall_score == 0.0:
            # Weighted average (same weights as duo-talk-evaluation)
            self.overall_score = (
                self.character_consistency * 0.25
                + self.topic_novelty * 0.20
                + self.relationship_quality * 0.25
                + self.naturalness * 0.15
                + self.concreteness * 0.15
            )


@dataclass
class CheckResult:
    """Result of a single static check

    Attributes:
        name: Check name (e.g., "tone_check", "praise_check")
        passed: Whether the check passed
        status: Suggested DirectorStatus if failed
        reason: Explanation if failed
        details: Additional details (e.g., matched patterns)
    """

    name: str
    passed: bool
    status: DirectorStatus = DirectorStatus.PASS
    reason: str = ""
    details: dict = field(default_factory=dict)
