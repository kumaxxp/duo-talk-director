"""DirectorHybrid: Combined static + LLM Director (Phase 2.2 + 3.1)

Runs static checks first (DirectorMinimal) for fast rejection,
then LLM evaluation (DirectorLLM) for semantic quality scoring.

Phase 3.1: RAG integration for logging (observe only, no injection).
"""

from typing import Optional

from .interfaces import (
    DirectorProtocol,
    DirectorEvaluation,
    DirectorStatus,
    RAGLogEntry,
    RAGFactEntry,
    RAGSummary,
)
from .director_minimal import DirectorMinimal
from .director_llm import DirectorLLM
from .llm.evaluator import EvaluatorLLMClient
from .config.thresholds import ThresholdConfig
from .rag import RAGManager


class DirectorHybrid(DirectorProtocol):
    """Hybrid Director combining static checks and LLM evaluation.

    Strategy:
    1. Run DirectorMinimal (static checks) first
    2. If static RETRY and skip_llm_on_static_retry=True: return immediately
    3. Otherwise, run DirectorLLM (semantic evaluation)
    4. Merge results, taking the stricter status

    This optimizes performance by skipping expensive LLM calls
    for obvious static violations.

    Phase 3.1: RAG integration for logging (observe only, no injection).
    """

    def __init__(
        self,
        llm_client: EvaluatorLLMClient,
        threshold_config: Optional[ThresholdConfig] = None,
        skip_llm_on_static_retry: bool = True,
        rag_enabled: bool = False,
    ):
        """Initialize DirectorHybrid.

        Args:
            llm_client: LLM client for semantic evaluation
            threshold_config: Optional custom threshold configuration
            skip_llm_on_static_retry: Skip LLM when static check returns RETRY
            rag_enabled: Enable RAG logging (Phase 3.1, observe only)
        """
        self.minimal = DirectorMinimal()
        self.llm_director = DirectorLLM(llm_client, threshold_config)
        self.skip_llm_on_static_retry = skip_llm_on_static_retry
        self.rag_enabled = rag_enabled
        self.rag_manager: Optional[RAGManager] = RAGManager() if rag_enabled else None
        self._rag_attempts: list[RAGLogEntry] = []  # Track RAG for all attempts

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
        # Phase 3.1: RAG search (observe only, no injection)
        rag_log = self._search_rag(speaker, response)

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
            # Attach RAG summary even on RETRY
            return self._attach_rag_summary(static_result, rag_log)

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
            result = DirectorEvaluation(
                status=static_result.status,
                reason=f"{static_result.reason} [LLM unavailable: {str(e)}]",
                suggestion=static_result.suggestion,
                checks_passed=static_result.checks_passed,
                checks_failed=static_result.checks_failed + ["llm_evaluation"],
            )
            return self._attach_rag_summary(result, rag_log)

        # Step 4: Merge results
        merged = self._merge_results(static_result, llm_result)
        return self._attach_rag_summary(merged, rag_log)

    def _search_rag(
        self,
        speaker: str,
        response: str,
    ) -> Optional[RAGLogEntry]:
        """Search RAG and return log entry (Phase 3.1, observe only)

        Args:
            speaker: Character name
            response: Response text to check

        Returns:
            RAGLogEntry if RAG is enabled, None otherwise
        """
        if not self.rag_enabled or self.rag_manager is None:
            return None

        # Extract output text from response (may include Thought/Output format)
        output_text = response
        if "Output:" in response:
            output_text = response.split("Output:")[-1].strip()

        # Search RAG
        result = self.rag_manager.search(speaker, output_text)

        # Convert to log entry
        log_dict = self.rag_manager.to_log_entry(result)

        # Determine triggers
        triggered_by = []
        if log_dict["blocked_props"]:
            triggered_by.append("blocked_props")
        for fact in result.facts:
            if "使わない" in fact.content:
                triggered_by.append("prohibited_terms")
                break

        # Build RAGLogEntry
        facts = [
            RAGFactEntry(
                tag=f["tag"],
                text=f["text"],
                source=f["source"],
                fact_id=f["id"],
            )
            for f in log_dict["facts"]
        ]

        rag_log = RAGLogEntry(
            enabled=True,
            triggered_by=list(set(triggered_by)),
            blocked_props=log_dict["blocked_props"],
            facts=facts,
            latency_ms=log_dict["latency_ms"],
        )

        # Track for summary
        self._rag_attempts.append(rag_log)

        return rag_log

    def _attach_rag_summary(
        self,
        evaluation: DirectorEvaluation,
        rag_log: Optional[RAGLogEntry],
    ) -> DirectorEvaluation:
        """Attach RAG summary to evaluation result

        Args:
            evaluation: The evaluation result
            rag_log: RAG log entry (if available)

        Returns:
            DirectorEvaluation with rag_summary attached
        """
        if rag_log is None:
            return evaluation

        # Build summary from all attempts
        sources: dict[str, int] = {}
        tags: list[str] = []
        total_facts = 0

        for i, attempt in enumerate(self._rag_attempts, 1):
            for fact in attempt.facts:
                sources[fact.source] = sources.get(fact.source, 0) + 1
                if fact.tag not in tags:
                    tags.append(fact.tag)
                total_facts += 1

        evaluation.rag_summary = RAGSummary(
            facts_count=total_facts,
            sources=sources,
            top_tags=tags[:3],
            used_for_attempts=list(range(1, len(self._rag_attempts) + 1)),
        )

        return evaluation

    def get_last_rag_log(self) -> Optional[RAGLogEntry]:
        """Get the last RAG log entry (for external logging)

        Returns:
            The last RAGLogEntry or None if no RAG searches
        """
        if self._rag_attempts:
            return self._rag_attempts[-1]
        return None

    def clear_rag_attempts(self) -> None:
        """Clear RAG attempts tracking (call after turn completes)"""
        self._rag_attempts.clear()

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
        self._rag_attempts.clear()
        if self.rag_manager:
            self.rag_manager.reset_session()
