"""DirectorLLM: LLM-based Director implementation (Phase 2.2)

Uses LLM to evaluate dialogue quality on 5 axes and determine
PASS/WARN/RETRY status based on configurable thresholds.
"""

import re
from typing import Optional

from .interfaces import DirectorProtocol, DirectorEvaluation, DirectorStatus, LLMEvaluationScore
from .llm.evaluator import LLMEvaluator, EvaluatorLLMClient
from .config.thresholds import ThresholdConfig, determine_status, build_reason


def extract_output(response: str) -> str:
    """Extract Output section from Thought/Output format response.

    Args:
        response: Full response text (may include Thought section)

    Returns:
        Output section text, or full response if no marker found
    """
    # Case-insensitive search for Output: marker
    match = re.search(r"[Oo]utput:\s*(.*)$", response, re.DOTALL)
    if match:
        return match.group(1).strip()
    return response


class DirectorLLM(DirectorProtocol):
    """LLM-based Director using 5-axis evaluation scoring.

    Evaluates responses using LLM to score:
    - character_consistency
    - topic_novelty
    - relationship_quality
    - naturalness
    - concreteness

    Status is determined by configurable thresholds.
    """

    def __init__(
        self,
        llm_client: EvaluatorLLMClient,
        threshold_config: Optional[ThresholdConfig] = None,
    ):
        """Initialize DirectorLLM.

        Args:
            llm_client: LLM client for evaluation
            threshold_config: Optional custom threshold configuration
        """
        self.evaluator = LLMEvaluator(llm_client)
        self.config = threshold_config or ThresholdConfig()
        self._history: list[dict] = []

    def evaluate_response(
        self,
        speaker: str,
        response: str,
        topic: str,
        history: list[dict],
        turn_number: int,
    ) -> DirectorEvaluation:
        """Evaluate response using LLM scoring.

        Args:
            speaker: Character name ("やな" or "あゆ")
            response: Generated response (may include Thought/Output)
            topic: Conversation topic
            history: Previous turns as list of {speaker, content}
            turn_number: Current turn number (0-indexed)

        Returns:
            DirectorEvaluation with status and details
        """
        # Extract Output section for evaluation
        output_text = extract_output(response)

        try:
            score = self.evaluator.evaluate_single_turn(
                speaker=speaker,
                response=output_text,
                topic=topic,
                history=history,
            )

            status = determine_status(score, self.config)
            reason = build_reason(score, status)

            return DirectorEvaluation(
                status=status,
                reason=reason,
                suggestion=self._build_suggestion(score, status),
                checks_passed=["llm_evaluation"] if status != DirectorStatus.RETRY else [],
                checks_failed=["llm_evaluation"] if status == DirectorStatus.RETRY else [],
            )

        except Exception as e:
            # Fallback on LLM error - return WARN to not block dialogue
            return DirectorEvaluation(
                status=DirectorStatus.WARN,
                reason=f"[WARN] LLM evaluation error: {str(e)}",
                suggestion="LLM評価が失敗しました。手動確認を推奨します。",
                checks_passed=[],
                checks_failed=["llm_evaluation"],
            )

    def commit_evaluation(
        self,
        response: str,
        evaluation: DirectorEvaluation,
    ) -> None:
        """Store accepted response for novelty tracking.

        Called when evaluation.status is PASS or WARN.

        Args:
            response: Accepted response text
            evaluation: The evaluation result
        """
        self._history.append({
            "response": response,
            "evaluation": evaluation,
        })

    def reset_for_new_session(self) -> None:
        """Reset state for new dialogue session.

        Clears history for fresh novelty tracking.
        """
        self._history.clear()

    def _build_suggestion(
        self,
        score: LLMEvaluationScore,
        status: DirectorStatus,
    ) -> Optional[str]:
        """Build improvement suggestion based on score.

        Args:
            score: LLMEvaluationScore with metrics
            status: Determined status

        Returns:
            Suggestion string or None
        """
        if status == DirectorStatus.PASS:
            return None

        suggestions = []

        # Identify weak areas
        if score.character_consistency < 0.5:
            suggestions.append("キャラクターの一貫性を改善（口調、一人称）")
        if score.topic_novelty < 0.5:
            suggestions.append("話題の繰り返しを避ける")
        if score.relationship_quality < 0.5:
            suggestions.append("姉妹らしい掛け合いを追加")
        if score.naturalness < 0.5:
            suggestions.append("応答の自然さを改善")
        if score.concreteness < 0.5:
            suggestions.append("具体的な情報を追加")

        # Include LLM-generated issues
        if score.issues:
            suggestions.extend(score.issues[:2])

        if suggestions:
            return "; ".join(suggestions[:3])

        return None
