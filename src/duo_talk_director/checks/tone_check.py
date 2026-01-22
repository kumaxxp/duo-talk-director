"""Tone marker check for character speech patterns

Validates that characters use appropriate speech patterns:
- やな (Yana): Casual, emotional markers
- あゆ (Ayu): Polite, logical markers
"""

import re
from dataclasses import dataclass
from typing import Optional

from ..interfaces import CheckResult, DirectorStatus


@dataclass
class ToneMarkers:
    """Tone markers for a character"""
    markers: list[str]  # Required markers
    vocab_markers: list[str]  # Vocabulary markers
    expected_desc: list[str]  # Description for suggestion
    forbidden_words: list[str]  # Words this character cannot use


# やな (Yana / Elder sister) - Casual, emotional
YANA_MARKERS = ToneMarkers(
    markers=["わ！", "へ？", "よね", "かな", "かも", "だね", "じゃん", "～"],
    vocab_markers=["やだ", "ほんと", "えー", "うーん", "すっごい", "そっか", "だね", "ね。", "もー"],
    expected_desc=["わ！", "へ？", "〜よね", "〜かな", "〜かも", "〜だね", "〜じゃん"],
    forbidden_words=["姉様"],  # That's how Ayu calls Yana
)

# あゆ (Ayu / Younger sister) - Polite, logical
AYU_MARKERS = ToneMarkers(
    markers=["でしょう", "ですね", "ました", "ません", "ですよ", "ですか"],
    vocab_markers=["つまり", "要するに", "一般的に", "目安", "推奨", "ですね", "です。"],
    expected_desc=["〜でしょう", "〜ですね", "〜ました", "〜ですよ"],
    forbidden_words=["姉上", "お姉ちゃん"],  # Wrong ways to call Yana
)


class ToneChecker:
    """Check tone markers for character consistency"""

    def __init__(self):
        self.markers = {
            "やな": YANA_MARKERS,
            "あゆ": AYU_MARKERS,
            "A": YANA_MARKERS,  # Legacy support
            "B": AYU_MARKERS,
        }

    def check(
        self,
        speaker: str,
        response: str,
    ) -> CheckResult:
        """Check tone markers in response

        Args:
            speaker: Character name ("やな", "あゆ", "A", or "B")
            response: Response text to check

        Returns:
            CheckResult with pass/fail status
        """
        tone_markers = self.markers.get(speaker)
        if tone_markers is None:
            return CheckResult(
                name="tone_check",
                passed=True,
                reason="Unknown speaker, skipping check",
            )

        normalized = self._normalize_for_checks(response)

        # Check forbidden words first
        for word in tone_markers.forbidden_words:
            if word in normalized:
                return CheckResult(
                    name="tone_check",
                    passed=False,
                    status=DirectorStatus.RETRY,
                    reason=f"禁止ワード「{word}」を使用",
                    details={"forbidden_word": word},
                )

        # Calculate tone score
        found_markers = [m for m in tone_markers.markers if m in normalized]
        marker_hit = len(found_markers) >= 1

        vocab_hit = any(word in normalized for word in tone_markers.vocab_markers)

        style_hit = self._check_style(speaker, normalized)

        tone_score = int(marker_hit) + int(vocab_hit) + int(style_hit)

        if tone_score >= 2:
            return CheckResult(
                name="tone_check",
                passed=True,
                status=DirectorStatus.PASS,
                reason="OK",
                details={"score": tone_score, "found_markers": found_markers},
            )
        elif tone_score == 1:
            return CheckResult(
                name="tone_check",
                passed=True,  # WARN is still passing
                status=DirectorStatus.WARN,
                reason=f"口調スコア不足 (score={tone_score})",
                details={
                    "score": tone_score,
                    "suggestion": f"口調マーカーを追加: {', '.join(tone_markers.expected_desc)}",
                },
            )
        else:
            return CheckResult(
                name="tone_check",
                passed=False,
                status=DirectorStatus.RETRY,
                reason=f"口調スコア不足 (score={tone_score})",
                details={
                    "score": tone_score,
                    "suggestion": f"口調マーカーを追加: {', '.join(tone_markers.expected_desc)}",
                },
            )

    def _check_style(self, speaker: str, normalized: str) -> bool:
        """Check style based on character type"""
        sentences = self._split_sentences(normalized)
        sentence_count = len(sentences)

        if speaker in ("A", "やな"):
            # Yana: Short, emotional sentences
            return sentence_count <= 3 and ("！" in normalized or "？" in normalized or "～" in normalized)
        else:
            # Ayu: Polite forms
            polite_matches = re.findall(r"(です|ます|でした|ました)", normalized)
            return len(polite_matches) >= 2

    @staticmethod
    def _normalize_for_checks(text: str) -> str:
        """Normalize text for checking

        Note: Quote brackets 「」『』 are removed but their content is kept,
        since dialogue content (where tone markers appear) is inside quotes.
        Parenthetical content （）is still removed as it's usually action descriptions.
        """
        normalized = text or ""
        # Keep quoted content but remove brackets (dialogue is inside quotes!)
        normalized = re.sub(r"[「『」』]", "", normalized)
        # Remove parenthetical action descriptions
        normalized = re.sub(r"（[^）]*）", "", normalized)
        # Normalize punctuation
        normalized = normalized.replace("｡", "。")
        normalized = re.sub(r"([！？!?.])\1+", r"\1", normalized)
        # Normalize whitespace
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized

    @staticmethod
    def _split_sentences(text: str) -> list[str]:
        """Split text into sentences"""
        if not text:
            return []
        parts = re.split(r"[。！？\n]+", text)
        return [p.strip() for p in parts if p.strip()]
