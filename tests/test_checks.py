"""Tests for individual check modules"""

import pytest

from duo_talk_director.checks import (
    ToneChecker,
    PraiseChecker,
    SettingChecker,
    FormatChecker,
)
from duo_talk_director.interfaces import DirectorStatus


class TestToneChecker:
    """Tests for ToneChecker"""

    @pytest.fixture
    def checker(self) -> ToneChecker:
        return ToneChecker()

    # === PASS cases ===

    def test_yana_good_response_passes(
        self, checker: ToneChecker, yana_speaker: str, yana_good_response: str
    ):
        """やな with proper tone markers should PASS"""
        result = checker.check(yana_speaker, yana_good_response)
        assert result.passed is True
        assert result.status == DirectorStatus.PASS

    def test_ayu_good_response_passes(
        self, checker: ToneChecker, ayu_speaker: str, ayu_good_response: str
    ):
        """あゆ with proper tone markers should PASS"""
        result = checker.check(ayu_speaker, ayu_good_response)
        assert result.passed is True
        assert result.status == DirectorStatus.PASS

    def test_yana_with_markers_passes(self, checker: ToneChecker, yana_speaker: str):
        """やな with markers like じゃん, ～ should pass"""
        response = "あ、それってほんとにすっごいじゃん！"
        result = checker.check(yana_speaker, response)
        assert result.passed is True

    def test_ayu_polite_form_passes(self, checker: ToneChecker, ayu_speaker: str):
        """あゆ with polite forms should pass"""
        response = "それは一般的にはそうですね。推奨されますよ。"
        result = checker.check(ayu_speaker, response)
        assert result.passed is True

    # === RETRY cases ===

    def test_yana_missing_markers_retries(
        self, checker: ToneChecker, yana_speaker: str, yana_bad_response: str
    ):
        """やな without tone markers should RETRY (score=0)"""
        result = checker.check(yana_speaker, yana_bad_response)
        # Score=0 results in RETRY
        assert result.passed is False
        assert result.status == DirectorStatus.RETRY
        assert result.details.get("score") == 0

    def test_ayu_missing_markers_retries(
        self, checker: ToneChecker, ayu_speaker: str, ayu_bad_response: str
    ):
        """あゆ without polite markers should RETRY"""
        result = checker.check(ayu_speaker, ayu_bad_response)
        assert result.passed is False
        assert result.status == DirectorStatus.RETRY

    def test_yana_using_forbidden_word_retries(
        self, checker: ToneChecker, yana_speaker: str
    ):
        """やな using 姉様 (forbidden) should RETRY"""
        response = "姉様、これはどうですか？"  # やな should not call herself 姉様
        result = checker.check(yana_speaker, response)
        assert result.passed is False
        assert result.status == DirectorStatus.RETRY
        assert "姉様" in result.reason

    def test_ayu_using_forbidden_word_retries(
        self, checker: ToneChecker, ayu_speaker: str
    ):
        """あゆ using お姉ちゃん (forbidden) should RETRY"""
        response = "お姉ちゃん、これはどうですか？"  # あゆ should use 姉様
        result = checker.check(ayu_speaker, response)
        assert result.passed is False
        assert result.status == DirectorStatus.RETRY

    # === WARN cases ===

    def test_yana_partial_markers_warns(self, checker: ToneChecker, yana_speaker: str):
        """やな with only one marker should WARN"""
        response = "うーん。"  # Only vocab marker, no style markers
        result = checker.check(yana_speaker, response)
        # Should be WARN (score=1) or RETRY (score=0) depending on style check
        assert result.status in [DirectorStatus.WARN, DirectorStatus.RETRY]

    # === Unknown speaker ===

    def test_unknown_speaker_passes(self, checker: ToneChecker):
        """Unknown speaker should pass (skip check)"""
        result = checker.check("unknown", "any response")
        assert result.passed is True
        assert "Unknown speaker" in result.reason

    # === Legacy support ===

    def test_legacy_speaker_a_supported(self, checker: ToneChecker):
        """Legacy speaker 'A' (Yana) should be supported"""
        response = "えー、すっごいじゃん！"
        result = checker.check("A", response)
        assert result.passed is True

    def test_legacy_speaker_b_supported(self, checker: ToneChecker):
        """Legacy speaker 'B' (Ayu) should be supported"""
        response = "一般的にはそうですね。推奨されますよ。"
        result = checker.check("B", response)
        assert result.passed is True


class TestPraiseChecker:
    """Tests for PraiseChecker"""

    @pytest.fixture
    def checker(self) -> PraiseChecker:
        return PraiseChecker()

    # === PASS cases (Yana can praise freely) ===

    def test_yana_praise_passes(
        self, checker: PraiseChecker, yana_speaker: str
    ):
        """やな can use praise words freely"""
        response = "さすがだね！あなたすごい！"
        result = checker.check(yana_speaker, response)
        assert result.passed is True
        assert result.status == DirectorStatus.PASS

    def test_ayu_no_praise_passes(
        self, checker: PraiseChecker, ayu_speaker: str, ayu_good_response: str
    ):
        """あゆ without praise words should PASS"""
        result = checker.check(ayu_speaker, ayu_good_response)
        assert result.passed is True
        assert result.status == DirectorStatus.PASS

    # === RETRY cases ===

    def test_ayu_praise_with_recipient_retries(
        self, checker: PraiseChecker, ayu_speaker: str, ayu_praise_response: str
    ):
        """あゆ with praise directed at someone should RETRY"""
        result = checker.check(ayu_speaker, ayu_praise_response)
        assert result.passed is False
        assert result.status == DirectorStatus.RETRY
        assert "さすが" in result.reason or "褒め" in result.reason

    def test_ayu_praise_with_answer_reference_retries(
        self, checker: PraiseChecker, ayu_speaker: str
    ):
        """あゆ praising an answer should RETRY"""
        response = "その答えは正解ですね。"
        result = checker.check(ayu_speaker, response)
        assert result.passed is False
        assert result.status == DirectorStatus.RETRY

    # === WARN cases ===

    def test_ayu_praise_without_recipient_warns(
        self, checker: PraiseChecker, ayu_speaker: str
    ):
        """あゆ with praise word but no recipient should WARN"""
        response = "すごいですね。"  # No recipient token
        result = checker.check(ayu_speaker, response)
        assert result.passed is True
        assert result.status == DirectorStatus.WARN

    # === Various praise words ===

    @pytest.mark.parametrize("praise_word", [
        "さすが", "素晴らしい", "正解", "天才", "完璧",
    ])
    def test_ayu_various_praise_words(
        self, checker: PraiseChecker, ayu_speaker: str, praise_word: str
    ):
        """あゆ should flag various praise words"""
        response = f"{praise_word}です、あなたの考えは。"
        result = checker.check(ayu_speaker, response)
        # Should be RETRY (with recipient) or WARN (without)
        assert result.status in [DirectorStatus.RETRY, DirectorStatus.WARN]


class TestSettingChecker:
    """Tests for SettingChecker"""

    @pytest.fixture
    def checker(self) -> SettingChecker:
        return SettingChecker()

    # === PASS cases ===

    def test_normal_response_passes(
        self, checker: SettingChecker, yana_good_response: str
    ):
        """Normal response without setting-breaking words should PASS"""
        result = checker.check(yana_good_response)
        assert result.passed is True
        assert result.status == DirectorStatus.PASS

    def test_home_reference_passes(self, checker: SettingChecker):
        """Proper home reference should pass"""
        response = "うちでゆっくりしようよ～"
        result = checker.check(response)
        assert result.passed is True
        assert result.status == DirectorStatus.PASS

    # === RETRY cases ===

    def test_setting_breaking_response_retries(
        self, checker: SettingChecker, setting_breaking_response: str
    ):
        """Response with setting-breaking words should RETRY"""
        result = checker.check(setting_breaking_response)
        assert result.passed is False
        assert result.status == DirectorStatus.RETRY

    @pytest.mark.parametrize("breaking_phrase", [
        "姉様のお家", "妹の家", "また遊びに来て", "お邪魔しました", "実家では",
    ])
    def test_various_breaking_phrases(
        self, checker: SettingChecker, breaking_phrase: str
    ):
        """Various setting-breaking phrases should RETRY"""
        response = f"今度は{breaking_phrase}どうですか。"
        result = checker.check(response)
        assert result.passed is False
        assert result.status == DirectorStatus.RETRY
        assert breaking_phrase in result.details.get("matched_word", "")


class TestFormatChecker:
    """Tests for FormatChecker"""

    @pytest.fixture
    def checker(self) -> FormatChecker:
        return FormatChecker()

    # === PASS cases ===

    def test_short_response_passes(
        self, checker: FormatChecker, yana_good_response: str
    ):
        """Short response (< 6 lines) should PASS"""
        result = checker.check(yana_good_response)
        assert result.passed is True
        assert result.status == DirectorStatus.PASS

    def test_single_line_passes(self, checker: FormatChecker):
        """Single line response should pass"""
        result = checker.check("これは一行の応答です。")
        assert result.passed is True
        assert result.status == DirectorStatus.PASS

    def test_five_lines_passes(self, checker: FormatChecker):
        """5 lines should pass"""
        lines = [f"これは{i}行目です。" for i in range(1, 6)]
        response = "\n".join(lines)
        result = checker.check(response)
        assert result.passed is True
        assert result.status == DirectorStatus.PASS

    # === WARN cases ===

    def test_medium_response_warns(
        self, checker: FormatChecker, medium_response: str
    ):
        """Medium response (6-7 lines) should WARN"""
        result = checker.check(medium_response)
        assert result.passed is True  # WARN is still passing
        assert result.status == DirectorStatus.WARN

    def test_seven_lines_warns(self, checker: FormatChecker):
        """7 lines should warn"""
        lines = [f"これは{i}行目です。" for i in range(1, 8)]
        response = "\n".join(lines)
        result = checker.check(response)
        assert result.passed is True
        assert result.status == DirectorStatus.WARN

    # === RETRY cases ===

    def test_long_response_retries(
        self, checker: FormatChecker, long_response: str
    ):
        """Long response (8+ lines) should RETRY"""
        result = checker.check(long_response)
        assert result.passed is False
        assert result.status == DirectorStatus.RETRY

    def test_ten_lines_retries(self, checker: FormatChecker):
        """10 lines should retry"""
        lines = [f"これは{i}行目です。" for i in range(1, 11)]
        response = "\n".join(lines)
        result = checker.check(response)
        assert result.passed is False
        assert result.status == DirectorStatus.RETRY

    # === Custom thresholds ===

    def test_custom_thresholds(self):
        """Custom thresholds should work"""
        checker = FormatChecker(retry_line_threshold=4, warn_line_threshold=3)

        # 2 lines - PASS
        result = checker.check("Line 1\nLine 2")
        assert result.status == DirectorStatus.PASS

        # 3 lines - WARN
        result = checker.check("Line 1\nLine 2\nLine 3")
        assert result.status == DirectorStatus.WARN

        # 4 lines - RETRY
        result = checker.check("Line 1\nLine 2\nLine 3\nLine 4")
        assert result.status == DirectorStatus.RETRY

    # === Empty lines handling ===

    def test_empty_lines_ignored(self, checker: FormatChecker):
        """Empty lines should be ignored in count"""
        response = "Line 1\n\nLine 2\n\n\nLine 3"  # 3 actual lines
        result = checker.check(response)
        assert result.passed is True
        assert result.status == DirectorStatus.PASS
        assert result.details["line_count"] == 3
