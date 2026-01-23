"""Tests for ToneChecker v2.1 - Negative Policing Approach

v2.1 Key Changes:
- Remove positive scoring (markers are NOT required)
- Focus on violation detection (forbidden patterns cause RETRY)
- Neutral responses without violations should PASS
"""

import pytest

from duo_talk_director.checks import ToneChecker
from duo_talk_director.interfaces import DirectorStatus


class TestToneCheckerV21NegativePolicing:
    """v2.1: Negative policing tests - check for violations, not required markers"""

    @pytest.fixture
    def checker(self) -> ToneChecker:
        return ToneChecker()

    # ===== やな (Yana) - Forbidden Formal Endings =====

    @pytest.mark.parametrize(
        "formal_ending",
        ["です", "ます", "ございます", "致します"],
    )
    def test_yana_formal_endings_retry(
        self, checker: ToneChecker, yana_speaker: str, formal_ending: str
    ):
        """やな using formal endings (です/ます) should RETRY"""
        response = f"そうかもしれない{formal_ending}。"
        result = checker.check(yana_speaker, response)
        assert result.passed is False, f"やな should not use '{formal_ending}'"
        assert result.status == DirectorStatus.RETRY
        assert "丁寧語" in result.reason or formal_ending in result.reason

    def test_yana_desu_at_sentence_end_retry(
        self, checker: ToneChecker, yana_speaker: str
    ):
        """やな with です at sentence end should RETRY"""
        response = "これは面白いです。"
        result = checker.check(yana_speaker, response)
        assert result.passed is False
        assert result.status == DirectorStatus.RETRY

    def test_yana_masu_at_sentence_end_retry(
        self, checker: ToneChecker, yana_speaker: str
    ):
        """やな with ます at sentence end should RETRY"""
        response = "わたしもそう思います。"
        result = checker.check(yana_speaker, response)
        assert result.passed is False
        assert result.status == DirectorStatus.RETRY

    # ===== やな (Yana) - No Markers, No Violations = PASS =====

    def test_yana_neutral_without_markers_passes(
        self, checker: ToneChecker, yana_speaker: str
    ):
        """やな without any markers but no violations should PASS (v2.1 key change)

        This is the "Forced Cheerfulness" fix - neutral responses should not be rejected.
        """
        # Examples from REPORT.md that were incorrectly rejected in v0.2
        neutral_responses = [
            "うん、わかった",
            "(心配そうに) 「え？どうしたの？」",
            "(伸びをして) 「おはよう、あゆ。まだ寝てるみたいね…」",
            "へえ、そうなんだ",
        ]
        for response in neutral_responses:
            result = checker.check(yana_speaker, response)
            assert result.passed is True, f"Neutral response should PASS: {response}"
            assert result.status in [DirectorStatus.PASS, DirectorStatus.WARN]

    def test_yana_quiet_affirmation_passes(
        self, checker: ToneChecker, yana_speaker: str
    ):
        """やな with quiet affirmation (no ！) should PASS"""
        response = "(頷いて) 「そうだね」"
        result = checker.check(yana_speaker, response)
        assert result.passed is True
        assert result.status in [DirectorStatus.PASS, DirectorStatus.WARN]

    # ===== やな (Yana) - Excessive Exclamation Marks =====

    def test_yana_excessive_exclamation_warns(
        self, checker: ToneChecker, yana_speaker: str
    ):
        """やな with too many ！ (>3) should WARN"""
        response = "すごい！やばい！最高！これは！ほんとに！"
        result = checker.check(yana_speaker, response)
        # Should warn but not fail
        assert result.status == DirectorStatus.WARN
        assert "感嘆符" in result.reason or "！" in result.reason

    def test_yana_moderate_exclamation_passes(
        self, checker: ToneChecker, yana_speaker: str
    ):
        """やな with moderate ！ usage (<=3) should PASS"""
        response = "すごいじゃん！やってみようよ！"
        result = checker.check(yana_speaker, response)
        assert result.passed is True
        assert result.status == DirectorStatus.PASS

    # ===== あゆ (Ayu) - Forbidden Casual Endings =====

    @pytest.mark.parametrize(
        "casual_ending",
        ["だね", "だよ", "じゃん", "でしょ"],
    )
    def test_ayu_casual_endings_retry(
        self, checker: ToneChecker, ayu_speaker: str, casual_ending: str
    ):
        """あゆ using casual endings should RETRY"""
        response = f"そう{casual_ending}。"
        result = checker.check(ayu_speaker, response)
        assert result.passed is False, f"あゆ should not use '{casual_ending}'"
        assert result.status == DirectorStatus.RETRY

    def test_ayu_dane_retry(self, checker: ToneChecker, ayu_speaker: str):
        """あゆ with だね should RETRY"""
        response = "そうだね、面白いと思う。"
        result = checker.check(ayu_speaker, response)
        assert result.passed is False
        assert result.status == DirectorStatus.RETRY

    def test_ayu_jan_retry(self, checker: ToneChecker, ayu_speaker: str):
        """あゆ with じゃん should RETRY"""
        response = "それいいじゃん。"
        result = checker.check(ayu_speaker, response)
        assert result.passed is False
        assert result.status == DirectorStatus.RETRY

    # ===== あゆ (Ayu) - Forbidden Slang =====

    @pytest.mark.parametrize(
        "slang",
        ["マジ", "ヤバい", "うける"],
    )
    def test_ayu_slang_retry(
        self, checker: ToneChecker, ayu_speaker: str, slang: str
    ):
        """あゆ using slang should RETRY"""
        response = f"{slang}ですね。"
        result = checker.check(ayu_speaker, response)
        assert result.passed is False, f"あゆ should not use slang '{slang}'"
        assert result.status == DirectorStatus.RETRY

    # ===== あゆ (Ayu) - No Markers, No Violations = PASS =====

    def test_ayu_neutral_without_markers_passes(
        self, checker: ToneChecker, ayu_speaker: str
    ):
        """あゆ without typical polite markers but no violations should PASS"""
        neutral_responses = [
            "そうかもしれない。",
            "なるほど、興味深い。",
            "姉様の言う通りかも。",
        ]
        for response in neutral_responses:
            result = checker.check(ayu_speaker, response)
            assert result.passed is True, f"Neutral response should PASS: {response}"

    # ===== あゆ (Ayu) - Forbidden Role Call =====

    def test_ayu_yanachan_retry(self, checker: ToneChecker, ayu_speaker: str):
        """あゆ calling やなちゃん (instead of 姉様) should RETRY"""
        response = "やなちゃん、これどう思う？"
        result = checker.check(ayu_speaker, response)
        assert result.passed is False
        assert result.status == DirectorStatus.RETRY

    # ===== Existing Forbidden Words (v0.2) Still Work =====

    def test_yana_anesama_still_forbidden(
        self, checker: ToneChecker, yana_speaker: str
    ):
        """やな calling herself 姉様 should still RETRY (v0.2 rule)"""
        response = "姉様として、私が決めるわ。"
        result = checker.check(yana_speaker, response)
        assert result.passed is False
        assert result.status == DirectorStatus.RETRY
        assert "姉様" in result.reason

    def test_ayu_oneechan_still_forbidden(
        self, checker: ToneChecker, ayu_speaker: str
    ):
        """あゆ calling お姉ちゃん (instead of 姉様) should still RETRY"""
        response = "お姉ちゃん、助けて。"
        result = checker.check(ayu_speaker, response)
        assert result.passed is False
        assert result.status == DirectorStatus.RETRY


class TestToneCheckerV21EdgeCases:
    """v2.1 Edge cases"""

    @pytest.fixture
    def checker(self) -> ToneChecker:
        return ToneChecker()

    def test_yana_desu_in_quoted_speech_retry(
        self, checker: ToneChecker, yana_speaker: str
    ):
        """やな with です inside quotes should still RETRY"""
        response = '「これは本当です」'
        result = checker.check(yana_speaker, response)
        assert result.passed is False
        assert result.status == DirectorStatus.RETRY

    def test_yana_masu_in_compound_word_passes(
        self, checker: ToneChecker, yana_speaker: str
    ):
        """やな with ます as part of compound word should PASS"""
        # e.g., "ますます" (increasingly) is not a polite ending
        response = "ますます面白くなってきた！"
        result = checker.check(yana_speaker, response)
        assert result.passed is True

    def test_ayu_jane_not_jan_passes(
        self, checker: ToneChecker, ayu_speaker: str
    ):
        """あゆ with ジェーン (name) should PASS - not confused with じゃん"""
        response = "ジェーンさんという方がいらっしゃいます。"
        result = checker.check(ayu_speaker, response)
        assert result.passed is True

    def test_empty_response_passes(self, checker: ToneChecker, yana_speaker: str):
        """Empty response should PASS (no violations)"""
        result = checker.check(yana_speaker, "")
        assert result.passed is True
