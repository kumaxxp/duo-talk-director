"""Tone marker check for character speech patterns (v2.1 - Negative Policing)

v2.1 Changes:
- Removed "positive scoring" (requiring markers)
- Focus on "negative policing" (detecting violations)
- Neutral responses without violations now PASS

Violations detected:
- やな (Yana): Formal endings (です/ます), 姉様 self-reference, excessive ！
- あゆ (Ayu): Casual endings (だね/じゃん), slang, wrong role calls
"""

import re
from dataclasses import dataclass, field
from typing import Optional

from ..interfaces import CheckResult, DirectorStatus


@dataclass
class ToneViolations:
    """Violation rules for a character (v2.1 Negative Policing)"""

    # Forbidden word endings (sentence-final patterns)
    forbidden_endings: list[str] = field(default_factory=list)

    # Forbidden words anywhere in text
    forbidden_words: list[str] = field(default_factory=list)

    # Forbidden slang/expressions
    forbidden_slang: list[str] = field(default_factory=list)

    # Description for each forbidden pattern (for error messages)
    forbidden_guidance: dict[str, str] = field(default_factory=dict)


# やな (Yana / Elder sister) - Casual, emotional
# VIOLATION: Using formal language (です/ます) is forbidden
# Note: Longer patterns first to avoid substring matching (e.g., "ございます" before "ます")
YANA_VIOLATIONS = ToneViolations(
    forbidden_endings=["ございます", "致します", "です", "ます"],
    forbidden_words=["姉様"],  # That's how Ayu calls Yana
    forbidden_slang=[],  # Yana can use casual slang
    forbidden_guidance={
        "です": "丁寧語（です）は禁止です。砕けた口調で話してください。",
        "ます": "丁寧語（ます）は禁止です。砕けた口調で話してください。",
        "ございます": "丁寧語（ございます）は禁止です。砕けた口調で話してください。",
        "致します": "丁寧語（致します）は禁止です。砕けた口調で話してください。",
        "姉様": "「姉様」はあゆが姉のやなを呼ぶ言葉です。やなは妹を「あゆ」と呼んでください。",
    },
)

# あゆ (Ayu / Younger sister) - Polite, logical
# VIOLATION: Using casual language (だね/じゃん) or slang is forbidden
AYU_VIOLATIONS = ToneViolations(
    forbidden_endings=["だね", "だよ", "じゃん", "でしょ"],
    forbidden_words=["姉上", "お姉ちゃん", "やなちゃん"],  # Wrong ways to call Yana
    forbidden_slang=["マジ", "ヤバい", "うける"],
    forbidden_guidance={
        "だね": "カジュアルな語尾（だね）は禁止です。丁寧語で話してください。",
        "だよ": "カジュアルな語尾（だよ）は禁止です。丁寧語で話してください。",
        "じゃん": "カジュアルな語尾（じゃん）は禁止です。丁寧語で話してください。",
        "でしょ": "カジュアルな語尾（でしょ）は禁止です。「でしょう」を使ってください。",
        "姉上": "「姉上」ではなく「姉様」を使ってください。",
        "お姉ちゃん": "「お姉ちゃん」ではなく「姉様」を使ってください。",
        "やなちゃん": "「やなちゃん」ではなく「姉様」を使ってください。",
        "マジ": "スラング「マジ」は禁止です。「本当に」を使ってください。",
        "ヤバい": "スラング「ヤバい」は禁止です。丁寧な表現を使ってください。",
        "うける": "スラング「うける」は禁止です。丁寧な表現を使ってください。",
    },
)

# Role information for error messages
ROLE_INFO = {
    "やな": {
        "role": "姉 (Elder Sister)",
        "calls_partner": "あゆ",
        "partner_calls_me": "姉様",
    },
    "あゆ": {
        "role": "妹 (Younger Sister)",
        "calls_partner": "姉様",
        "partner_calls_me": "あゆ",
    },
    "A": {
        "role": "姉 (Elder Sister)",
        "calls_partner": "あゆ",
        "partner_calls_me": "姉様",
    },
    "B": {
        "role": "妹 (Younger Sister)",
        "calls_partner": "姉様",
        "partner_calls_me": "あゆ",
    },
}

# Exclamation mark threshold for warning
EXCLAMATION_WARN_THRESHOLD = 3


class ToneChecker:
    """Check tone violations for character consistency (v2.1 Negative Policing)

    v2.1 Key Changes:
    - No longer requires positive markers
    - Only checks for violations (forbidden patterns)
    - Neutral responses without violations → PASS
    """

    def __init__(self):
        self.violations = {
            "やな": YANA_VIOLATIONS,
            "あゆ": AYU_VIOLATIONS,
            "A": YANA_VIOLATIONS,  # Legacy support
            "B": AYU_VIOLATIONS,
        }

    def check(
        self,
        speaker: str,
        response: str,
    ) -> CheckResult:
        """Check for tone violations in response (v2.1 Negative Policing)

        Args:
            speaker: Character name ("やな", "あゆ", "A", or "B")
            response: Response text to check

        Returns:
            CheckResult with pass/fail status
        """
        violations = self.violations.get(speaker)
        if violations is None:
            return CheckResult(
                name="tone_check",
                passed=True,
                reason="Unknown speaker, skipping check",
            )

        normalized = self._normalize_for_checks(response)

        # Empty response is OK (no violations possible)
        if not normalized.strip():
            return CheckResult(
                name="tone_check",
                passed=True,
                status=DirectorStatus.PASS,
                reason="OK (empty response)",
            )

        role_info = ROLE_INFO.get(speaker, {})
        role = role_info.get("role", speaker)

        # 1. Check forbidden endings (sentence-final patterns)
        ending_violation = self._check_forbidden_endings(
            normalized, violations, speaker, role
        )
        if ending_violation:
            return ending_violation

        # 2. Check forbidden words
        word_violation = self._check_forbidden_words(
            normalized, violations, speaker, role
        )
        if word_violation:
            return word_violation

        # 3. Check forbidden slang
        slang_violation = self._check_forbidden_slang(
            normalized, violations, speaker, role
        )
        if slang_violation:
            return slang_violation

        # 4. Check excessive exclamation marks (warning only for やな)
        if speaker in ("A", "やな"):
            exclamation_warning = self._check_excessive_exclamation(normalized)
            if exclamation_warning:
                return exclamation_warning

        # No violations found → PASS
        return CheckResult(
            name="tone_check",
            passed=True,
            status=DirectorStatus.PASS,
            reason="OK",
            details={"violations_checked": True},
        )

    def _check_forbidden_endings(
        self,
        normalized: str,
        violations: ToneViolations,
        speaker: str,
        role: str,
    ) -> Optional[CheckResult]:
        """Check for forbidden sentence endings"""
        for ending in violations.forbidden_endings:
            # Check if ending appears at sentence boundary
            # Pattern: ending + (。、？！ or end of string)
            pattern = rf"{re.escape(ending)}(?=[。、？！\s]|$)"
            if re.search(pattern, normalized):
                guidance = violations.forbidden_guidance.get(
                    ending, f"「{ending}」は使用禁止です。"
                )
                return CheckResult(
                    name="tone_check",
                    passed=False,
                    status=DirectorStatus.RETRY,
                    reason=f"役割違反: あなたは「{speaker}」（{role}）です。禁止された語尾「{ending}」を使用しました。",
                    details={
                        "violation_type": "forbidden_ending",
                        "forbidden_ending": ending,
                        "suggestion": guidance,
                    },
                )
        return None

    def _check_forbidden_words(
        self,
        normalized: str,
        violations: ToneViolations,
        speaker: str,
        role: str,
    ) -> Optional[CheckResult]:
        """Check for forbidden words anywhere in text"""
        for word in violations.forbidden_words:
            if word in normalized:
                guidance = violations.forbidden_guidance.get(
                    word, f"「{word}」は使用禁止です。"
                )
                return CheckResult(
                    name="tone_check",
                    passed=False,
                    status=DirectorStatus.RETRY,
                    reason=f"役割違反: あなたは「{speaker}」（{role}）です。禁止ワード「{word}」を使用しました。",
                    details={
                        "violation_type": "forbidden_word",
                        "forbidden_word": word,
                        "suggestion": guidance,
                    },
                )
        return None

    def _check_forbidden_slang(
        self,
        normalized: str,
        violations: ToneViolations,
        speaker: str,
        role: str,
    ) -> Optional[CheckResult]:
        """Check for forbidden slang expressions"""
        for slang in violations.forbidden_slang:
            if slang in normalized:
                guidance = violations.forbidden_guidance.get(
                    slang, f"スラング「{slang}」は禁止です。"
                )
                return CheckResult(
                    name="tone_check",
                    passed=False,
                    status=DirectorStatus.RETRY,
                    reason=f"役割違反: あなたは「{speaker}」（{role}）です。禁止スラング「{slang}」を使用しました。",
                    details={
                        "violation_type": "forbidden_slang",
                        "forbidden_slang": slang,
                        "suggestion": guidance,
                    },
                )
        return None

    def _check_excessive_exclamation(
        self, normalized: str
    ) -> Optional[CheckResult]:
        """Check for excessive exclamation mark usage (warning only)"""
        count = normalized.count("！")
        if count > EXCLAMATION_WARN_THRESHOLD:
            return CheckResult(
                name="tone_check",
                passed=True,  # WARN is still passing
                status=DirectorStatus.WARN,
                reason=f"感嘆符が多すぎます (count={count})",
                details={
                    "violation_type": "excessive_exclamation",
                    "exclamation_count": count,
                    "suggestion": "もう少し落ち着いた表現を使ってください。",
                },
            )
        return None

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
