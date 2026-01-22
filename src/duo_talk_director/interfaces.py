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
    """

    status: DirectorStatus
    reason: str
    suggestion: Optional[str] = None
    action: str = "NOOP"
    next_instruction: Optional[str] = None
    checks_passed: list[str] = field(default_factory=list)
    checks_failed: list[str] = field(default_factory=list)


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
