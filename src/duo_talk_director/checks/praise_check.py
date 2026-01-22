"""Praise word check for character consistency

Validates that Ayu (あゆ) doesn't use excessive praise words,
which would break her character as the analytical, critical sister.
"""

import re
from dataclasses import dataclass

from ..interfaces import CheckResult, DirectorStatus


# Praise words that Ayu should avoid
PRAISE_WORDS_FOR_AYU = [
    "いい観点", "いい質問", "さすが", "鋭い",
    "おっしゃる通り", "その通り", "素晴らしい", "お見事",
    "よく気づ", "正解です", "大正解", "正解", "すごい", "完璧", "天才",
]

# Tokens indicating the praise is directed at someone
RECIPIENT_TOKENS = [
    "あなた", "きみ", "ユーザー",
    "その答え", "その考え", "その意見", "発言", "回答",
]


class PraiseChecker:
    """Check for inappropriate praise words (Ayu only)"""

    def __init__(
        self,
        praise_words: list[str] | None = None,
        recipient_tokens: list[str] | None = None,
    ):
        self.praise_words = praise_words or PRAISE_WORDS_FOR_AYU
        self.recipient_tokens = recipient_tokens or RECIPIENT_TOKENS

    def check(
        self,
        speaker: str,
        response: str,
    ) -> CheckResult:
        """Check for praise words in response

        Only applies to Ayu (あゆ / B). Yana can praise freely.

        Args:
            speaker: Character name ("やな", "あゆ", "A", or "B")
            response: Response text to check

        Returns:
            CheckResult with pass/fail status
        """
        # Only check Ayu's responses
        if speaker in ("A", "やな"):
            return CheckResult(
                name="praise_check",
                passed=True,
                reason="Praise check only applies to Ayu",
            )

        normalized = self._normalize_for_checks(response)
        sentences = self._split_sentences(normalized)

        for sentence in sentences:
            for word in self.praise_words:
                if word in sentence:
                    # Check if praise is directed at someone
                    if any(token in sentence for token in self.recipient_tokens):
                        return CheckResult(
                            name="praise_check",
                            passed=False,
                            status=DirectorStatus.RETRY,
                            reason=f"あゆの褒め言葉使用: 「{word}」",
                            details={
                                "praise_word": word,
                                "sentence": sentence,
                                "suggestion": "評価・判定型の表現を避け、情報提供に徹してください",
                            },
                        )

                    # Praise word without recipient - just a warning
                    return CheckResult(
                        name="praise_check",
                        passed=True,  # WARN is still passing
                        status=DirectorStatus.WARN,
                        reason=f"評価語の使用: 「{word}」",
                        details={
                            "praise_word": word,
                            "suggestion": "評価語は避け、説明に置き換えてください",
                        },
                    )

        return CheckResult(
            name="praise_check",
            passed=True,
            status=DirectorStatus.PASS,
            reason="OK",
        )

    @staticmethod
    def _normalize_for_checks(text: str) -> str:
        """Normalize text for checking"""
        normalized = text or ""
        normalized = re.sub(r"[「『][^」』]*[」』]", "", normalized)
        normalized = re.sub(r"（[^）]*）", "", normalized)
        normalized = normalized.replace("｡", "。")
        normalized = re.sub(r"([！？!?.])\1+", r"\1", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized

    @staticmethod
    def _split_sentences(text: str) -> list[str]:
        """Split text into sentences"""
        if not text:
            return []
        parts = re.split(r"[。！？\n]+", text)
        return [p.strip() for p in parts if p.strip()]
