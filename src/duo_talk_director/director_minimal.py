"""Minimal Director: Static checks only

A lightweight Director implementation that uses only static pattern matching.
No LLM calls, zero latency impact.

Checks performed:
1. Thought structure (presence, content, completeness)
2. Tone markers (character speech patterns)
3. Praise words (Ayu only)
4. Context consistency (hallucination detection)
5. Setting consistency (sisters live together)
6. Format (response length)
"""

from .interfaces import (
    DirectorProtocol,
    DirectorStatus,
    DirectorEvaluation,
)
from .checks import (
    ToneChecker,
    PraiseChecker,
    SettingChecker,
    FormatChecker,
    ContextChecker,
    ThoughtChecker,
)


class DirectorMinimal(DirectorProtocol):
    """Minimal Director with static checks only

    Uses pattern matching to validate:
    - Character tone consistency
    - Appropriate language use
    - World setting consistency
    - Response format

    No LLM calls, designed for low-latency quality control.
    """

    def __init__(self):
        self.thought_checker = ThoughtChecker()
        self.tone_checker = ToneChecker()
        self.praise_checker = PraiseChecker()
        self.context_checker = ContextChecker()
        self.setting_checker = SettingChecker()
        self.format_checker = FormatChecker()

    def evaluate_response(
        self,
        speaker: str,
        response: str,
        topic: str,
        history: list[dict],
        turn_number: int,
    ) -> DirectorEvaluation:
        """Evaluate response with static checks

        Args:
            speaker: Character name ("やな" or "あゆ")
            response: Generated response text
            topic: Conversation topic (unused in minimal)
            history: Conversation history (used for context check)
            turn_number: Turn number (unused in minimal)

        Returns:
            DirectorEvaluation with status and details
        """
        checks_passed = []
        checks_failed = []
        warnings = []

        # 1. Thought structure check
        thought_result = self.thought_checker.check(response)
        if thought_result.status == DirectorStatus.RETRY:
            checks_failed.append(thought_result.name)
            return DirectorEvaluation(
                status=DirectorStatus.RETRY,
                reason=thought_result.reason,
                suggestion=thought_result.details.get("suggestion"),
                checks_passed=checks_passed,
                checks_failed=checks_failed,
            )
        elif thought_result.status == DirectorStatus.WARN:
            warnings.append(thought_result.reason)
        checks_passed.append(thought_result.name)

        # 2. Tone markers check
        tone_result = self.tone_checker.check(speaker, response)
        if tone_result.status == DirectorStatus.RETRY:
            checks_failed.append(tone_result.name)
            return DirectorEvaluation(
                status=DirectorStatus.RETRY,
                reason=tone_result.reason,
                suggestion=tone_result.details.get("suggestion"),
                checks_passed=checks_passed,
                checks_failed=checks_failed,
            )
        elif tone_result.status == DirectorStatus.WARN:
            warnings.append(tone_result.reason)
        checks_passed.append(tone_result.name)

        # 3. Praise words check (Ayu only)
        praise_result = self.praise_checker.check(speaker, response)
        if praise_result.status == DirectorStatus.RETRY:
            checks_failed.append(praise_result.name)
            return DirectorEvaluation(
                status=DirectorStatus.RETRY,
                reason=praise_result.reason,
                suggestion=praise_result.details.get("suggestion"),
                checks_passed=checks_passed,
                checks_failed=checks_failed,
            )
        elif praise_result.status == DirectorStatus.WARN:
            warnings.append(praise_result.reason)
        checks_passed.append(praise_result.name)

        # 4. Context consistency check (hallucination detection)
        context_result = self.context_checker.check(speaker, response, history)
        if context_result.status == DirectorStatus.RETRY:
            checks_failed.append(context_result.name)
            return DirectorEvaluation(
                status=DirectorStatus.RETRY,
                reason=context_result.reason,
                suggestion=context_result.details.get("suggestion"),
                checks_passed=checks_passed,
                checks_failed=checks_failed,
            )
        checks_passed.append(context_result.name)

        # 5. Setting consistency check
        setting_result = self.setting_checker.check(response)
        if setting_result.status == DirectorStatus.RETRY:
            checks_failed.append(setting_result.name)
            return DirectorEvaluation(
                status=DirectorStatus.RETRY,
                reason=setting_result.reason,
                suggestion=setting_result.details.get("suggestion"),
                checks_passed=checks_passed,
                checks_failed=checks_failed,
            )
        checks_passed.append(setting_result.name)

        # 6. Format check
        format_result = self.format_checker.check(response)
        if format_result.status == DirectorStatus.RETRY:
            checks_failed.append(format_result.name)
            return DirectorEvaluation(
                status=DirectorStatus.RETRY,
                reason=format_result.reason,
                suggestion=format_result.details.get("suggestion"),
                checks_passed=checks_passed,
                checks_failed=checks_failed,
            )
        elif format_result.status == DirectorStatus.WARN:
            warnings.append(format_result.reason)
        checks_passed.append(format_result.name)

        # Final result
        if warnings:
            return DirectorEvaluation(
                status=DirectorStatus.WARN,
                reason=f"警告: {', '.join(warnings)}",
                suggestion="次のターンで改善してください",
                action="NOOP",
                checks_passed=checks_passed,
                checks_failed=checks_failed,
            )

        return DirectorEvaluation(
            status=DirectorStatus.PASS,
            reason="OK",
            action="NOOP",
            checks_passed=checks_passed,
            checks_failed=checks_failed,
        )

    def commit_evaluation(
        self,
        response: str,
        evaluation: DirectorEvaluation,
    ) -> None:
        """Commit accepted response (no-op for minimal)

        Minimal Director is stateless, so this does nothing.
        Maintained for interface compatibility.
        """
        pass

    def reset_for_new_session(self) -> None:
        """Reset for new session (no-op for minimal)

        Minimal Director is stateless, so this does nothing.
        Maintained for interface compatibility.
        """
        pass
