"""DirectorHybrid: Combined static + LLM Director (Phase 2.2)

Runs static checks first (DirectorMinimal) for fast rejection,
then LLM evaluation (DirectorLLM) for semantic quality scoring.
"""

from typing import Optional

from .interfaces import DirectorProtocol, DirectorEvaluation, DirectorStatus
from .director_minimal import DirectorMinimal
from .director_llm import DirectorLLM
from .llm.evaluator import EvaluatorLLMClient
from .config.thresholds import ThresholdConfig


class DirectorHybrid(DirectorProtocol):
    """Hybrid Director combining static checks and LLM evaluation.

    Strategy:
    1. Run DirectorMinimal (static checks) first
    2. If static RETRY and skip_llm_on_static_retry=True: return immediately
    3. Otherwise, run DirectorLLM (semantic evaluation)
    4. Merge results, taking the stricter status

    This optimizes performance by skipping expensive LLM calls
    for obvious static violations.
    """

    def __init__(
        self,
        llm_client: EvaluatorLLMClient,
        threshold_config: Optional[ThresholdConfig] = None,
        skip_llm_on_static_retry: bool = True,
    ):
        """Initialize DirectorHybrid.

        Args:
            llm_client: LLM client for semantic evaluation
            threshold_config: Optional custom threshold configuration
            skip_llm_on_static_retry: Skip LLM when static check returns RETRY
        """
        self.minimal = DirectorMinimal()
        self.llm_director = DirectorLLM(llm_client, threshold_config)
        self.skip_llm_on_static_retry = skip_llm_on_static_retry

    def evaluate_response(
        self,
        speaker: str,
        response: str,
        topic: str,
        history: list[dict],
        turn_number: int,
    ) -> DirectorEvaluation:
        """Evaluate response using hybrid static + LLM approach.

        Args:
            speaker: Character name ("やな" or "あゆ")
            response: Generated response (may include Thought/Output)
            topic: Conversation topic
            history: Previous turns as list of {speaker, content}
            turn_number: Current turn number (0-indexed)

        Returns:
            DirectorEvaluation with merged status and details
        """
        # Step 1: Static checks (fast)
        static_result = self.minimal.evaluate_response(
            speaker=speaker,
            response=response,
            topic=topic,
            history=history,
            turn_number=turn_number,
        )

        # Step 2: Short-circuit on static RETRY (if enabled)
        if static_result.status == DirectorStatus.RETRY and self.skip_llm_on_static_retry:
            return static_result

        # Step 3: LLM evaluation (semantic)
        try:
            llm_result = self.llm_director.evaluate_response(
                speaker=speaker,
                response=response,
                topic=topic,
                history=history,
                turn_number=turn_number,
            )
        except Exception as e:
            # LLM failed, fall back to static result
            return DirectorEvaluation(
                status=static_result.status,
                reason=f"{static_result.reason} [LLM unavailable: {str(e)}]",
                suggestion=static_result.suggestion,
                checks_passed=static_result.checks_passed,
                checks_failed=static_result.checks_failed + ["llm_evaluation"],
            )

        # Step 4: Merge results
        return self._merge_results(static_result, llm_result)

    def _merge_results(
        self,
        static: DirectorEvaluation,
        llm: DirectorEvaluation,
    ) -> DirectorEvaluation:
        """Merge static and LLM evaluation results.

        Takes the stricter (worse) status between the two.

        Args:
            static: DirectorEvaluation from static checks
            llm: DirectorEvaluation from LLM evaluation

        Returns:
            Merged DirectorEvaluation
        """
        # Status priority: MODIFY > RETRY > WARN > PASS
        status_priority = {
            DirectorStatus.PASS: 0,
            DirectorStatus.WARN: 1,
            DirectorStatus.RETRY: 2,
            DirectorStatus.MODIFY: 3,
        }

        # Take stricter status
        if status_priority[llm.status] > status_priority[static.status]:
            final_status = llm.status
        else:
            final_status = static.status

        # Combine check lists
        checks_passed = static.checks_passed + llm.checks_passed
        checks_failed = static.checks_failed + llm.checks_failed

        # Build combined reason
        reason_parts = []
        if static.reason:
            reason_parts.append(f"[Static] {static.reason}")
        if llm.reason:
            reason_parts.append(f"[LLM] {llm.reason}")

        return DirectorEvaluation(
            status=final_status,
            reason=" ".join(reason_parts),
            suggestion=llm.suggestion or static.suggestion,
            checks_passed=checks_passed,
            checks_failed=checks_failed,
            llm_score=llm.llm_score,
        )

    def commit_evaluation(
        self,
        response: str,
        evaluation: DirectorEvaluation,
    ) -> None:
        """Commit evaluation to both directors.

        Args:
            response: Accepted response text
            evaluation: The evaluation result
        """
        self.minimal.commit_evaluation(response, evaluation)
        self.llm_director.commit_evaluation(response, evaluation)

    def reset_for_new_session(self) -> None:
        """Reset both directors for new session."""
        self.minimal.reset_for_new_session()
        self.llm_director.reset_for_new_session()
