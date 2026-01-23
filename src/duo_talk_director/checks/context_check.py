"""Context check for dialogue consistency

Validates that character reactions match the actual context:
- やな should not react to "毒舌" if あゆ's previous message wasn't toxic
- Prevents hallucination-based context mismatches
"""

from ..interfaces import CheckResult, DirectorStatus


class ContextChecker:
    """Check context consistency for character reactions

    Specifically detects when やな reacts to non-existent "toxicity"
    from あゆ's previous message.
    """

    # Trigger words that indicate a "toxicity reaction"
    TOXICITY_REACTION_TRIGGERS = [
        "毒舌",
        "厳しい",
        "辛辣",
        "きつい",
        "手厳しい",
    ]

    # Words that indicate actual toxic/harsh content in あゆ's message
    TOXIC_KEYWORDS = [
        "無駄",
        "コスト",
        "ダメ",
        "無理",
        "非効率",
        "リスク",
        "問題",
        "危険",
        "失敗",
        "間違い",
        "正気",
        "呆れ",
        "ため息",
    ]

    def check(
        self,
        speaker: str,
        response: str,
        history: list[dict],
    ) -> CheckResult:
        """Check context consistency

        Args:
            speaker: Character name ("やな" or "あゆ")
            response: Generated response text
            history: Conversation history

        Returns:
            CheckResult with pass/fail status
        """
        # Only check やな's responses
        if speaker not in ("やな", "A"):
            return CheckResult(
                name="context_check",
                passed=True,
                status=DirectorStatus.PASS,
                reason="OK",
            )

        # Check if response contains toxicity reaction triggers
        has_toxicity_reaction = any(
            trigger in response for trigger in self.TOXICITY_REACTION_TRIGGERS
        )

        if not has_toxicity_reaction:
            # No toxicity reaction, no context check needed
            return CheckResult(
                name="context_check",
                passed=True,
                status=DirectorStatus.PASS,
                reason="OK",
            )

        # Get the last message from あゆ
        last_ayu_message = self._get_last_ayu_message(history)

        if last_ayu_message is None:
            # No あゆ message to check, pass
            return CheckResult(
                name="context_check",
                passed=True,
                status=DirectorStatus.PASS,
                reason="OK (no previous あゆ message)",
            )

        # Check if あゆ's message actually contains toxic content
        is_actually_toxic = any(
            keyword in last_ayu_message for keyword in self.TOXIC_KEYWORDS
        )

        if is_actually_toxic:
            # Toxicity reaction is justified
            return CheckResult(
                name="context_check",
                passed=True,
                status=DirectorStatus.PASS,
                reason="OK",
                details={"context_matched": True},
            )
        else:
            # Toxicity reaction without actual toxicity - hallucination!
            return CheckResult(
                name="context_check",
                passed=False,
                status=DirectorStatus.RETRY,
                reason="文脈エラー: 存在しない「毒舌」への反応を検出",
                details={
                    "suggestion": "直前のあゆの発言は毒舌ではありません。文脈に沿った反応をしてください。",
                    "last_ayu_message": last_ayu_message[:50] + "..." if len(last_ayu_message) > 50 else last_ayu_message,
                },
            )

    def _get_last_ayu_message(self, history: list[dict]) -> str | None:
        """Get あゆ's message only if it's the most recent one

        If やな is the last speaker, return None (no immediate context to check).
        This prevents false positives when やな reacts to something other than
        the immediate previous message.

        Args:
            history: Conversation history

        Returns:
            あゆ's last message content if she was the last speaker, else None
        """
        if not history:
            return None

        # Only check if the immediate previous message is from あゆ
        last_message = history[-1]
        if last_message.get("speaker") in ("あゆ", "B"):
            return last_message.get("content", "")

        # If the last speaker is not あゆ, return None
        # (やな is not directly reacting to あゆ's message)
        return None
