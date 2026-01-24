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
        rag_summary: Optional RAG summary (Phase 3.1)
    """

    status: DirectorStatus
    reason: str
    suggestion: Optional[str] = None
    action: str = "NOOP"
    next_instruction: Optional[str] = None
    checks_passed: list[str] = field(default_factory=list)
    checks_failed: list[str] = field(default_factory=list)
    llm_score: Optional["LLMEvaluationScore"] = None
    rag_summary: Optional["RAGSummary"] = None


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


@dataclass
class RAGFactEntry:
    """Single fact entry for RAG logging (Phase 3.1)

    Attributes:
        tag: Fact category (STYLE, SCENE, REL)
        text: Fact content (max 50 chars)
        source: Source of the fact (persona_rules, session_state)
        fact_id: Unique identifier for the fact
    """

    tag: str
    text: str
    source: str
    fact_id: str = ""


@dataclass
class RAGLogEntry:
    """RAG log entry for a single evaluation attempt (Phase 3.1)

    Attributes:
        enabled: Whether RAG was enabled for this evaluation
        triggered_by: What triggered RAG (e.g., blocked_props, prohibited_terms)
        blocked_props: List of blocked props detected
        facts: List of RAGFactEntry
        latency_ms: Time taken for RAG search in milliseconds
        would_inject: Whether RAG would inject facts (Phase 3.2 preview)
    """

    enabled: bool = True
    triggered_by: list[str] = field(default_factory=list)
    blocked_props: list[str] = field(default_factory=list)
    facts: list[RAGFactEntry] = field(default_factory=list)
    latency_ms: float = 0.0
    would_inject: bool = False  # Phase 3.2 preview: True if injection would trigger

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "enabled": self.enabled,
            "triggered_by": self.triggered_by,
            "blocked_props": self.blocked_props,
            "facts": [
                {"tag": f.tag, "text": f.text, "source": f.source, "id": f.fact_id}
                for f in self.facts
            ],
            "latency_ms": self.latency_ms,
            "would_inject": self.would_inject,
        }


@dataclass
class RAGSummary:
    """RAG summary for DirectorEvaluation (Phase 3.1)

    Lightweight summary - facts content is NOT duplicated here.

    Attributes:
        facts_count: Number of facts retrieved
        sources: Count by source (e.g., {"persona_rules": 2, "session_state": 1})
        top_tags: List of tags used (e.g., ["STYLE", "SCENE", "REL"])
        used_for_attempts: Which attempts used RAG (e.g., [1, 2])
    """

    facts_count: int = 0
    sources: dict[str, int] = field(default_factory=dict)
    top_tags: list[str] = field(default_factory=list)
    used_for_attempts: list[int] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "facts_count": self.facts_count,
            "sources": self.sources,
            "top_tags": self.top_tags,
            "used_for_attempts": self.used_for_attempts,
        }


@dataclass
class InjectionDecision:
    """Decision details for RAG injection (Phase 3.2.1 P1.5)

    Tracks why injection was triggered for debugging and analysis.

    Attributes:
        would_inject: Whether injection would/did trigger
        reasons: List of trigger reasons (e.g., ["prohibited_terms", "tone_violation"])
        predicted_blocked_props: Blocked props detected in topic (proactive)
        detected_addressing_violation: Addressing violation detected in topic
        detected_tone_violation: Tone violation detected in topic
        facts_injected: Number of facts actually injected
    """

    would_inject: bool = False
    reasons: list[str] = field(default_factory=list)
    predicted_blocked_props: list[str] = field(default_factory=list)
    detected_addressing_violation: bool = False
    detected_tone_violation: bool = False
    facts_injected: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "would_inject": self.would_inject,
            "reasons": self.reasons,
            "predicted_blocked_props": self.predicted_blocked_props,
            "detected_addressing_violation": self.detected_addressing_violation,
            "detected_tone_violation": self.detected_tone_violation,
            "facts_injected": self.facts_injected,
        }
