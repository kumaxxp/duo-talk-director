"""Tests for ContextChecker

ContextChecker detects context mismatches, specifically:
- When やな reacts to "毒舌" that doesn't exist in あゆ's previous message
"""

import pytest

from duo_talk_director.checks import ContextChecker
from duo_talk_director.interfaces import DirectorStatus


class TestContextChecker:
    """Tests for ContextChecker"""

    @pytest.fixture
    def checker(self) -> ContextChecker:
        return ContextChecker()

    @pytest.fixture
    def yana_speaker(self) -> str:
        return "やな"

    @pytest.fixture
    def ayu_speaker(self) -> str:
        return "あゆ"

    # === PASS cases (correct context) ===

    def test_normal_response_passes(self, checker: ContextChecker, yana_speaker: str):
        """Normal response without toxicity reaction should PASS"""
        response = "「あゆ、今日も頑張ろうね～」"
        history = [{"speaker": "あゆ", "content": "姉様、おはようございます。"}]
        result = checker.check(yana_speaker, response, history)
        assert result.passed is True
        assert result.status == DirectorStatus.PASS

    def test_toxicity_reaction_with_actual_toxicity_passes(
        self, checker: ContextChecker, yana_speaker: str
    ):
        """Reacting to actual toxicity should PASS"""
        response = "「もー、あゆは毒舌だね～」"
        history = [{"speaker": "あゆ", "content": "姉様、それは無駄ですよ。コストの無駄遣いです。"}]
        result = checker.check(yana_speaker, response, history)
        assert result.passed is True
        assert result.status == DirectorStatus.PASS

    def test_toxicity_reaction_with_risk_mention_passes(
        self, checker: ContextChecker, yana_speaker: str
    ):
        """Reacting to risk-related comment should PASS"""
        response = "「厳しいこと言うね～」"
        history = [{"speaker": "あゆ", "content": "そのプランはリスクが高すぎます。"}]
        result = checker.check(yana_speaker, response, history)
        assert result.passed is True
        assert result.status == DirectorStatus.PASS

    def test_ayu_response_always_passes(
        self, checker: ContextChecker, ayu_speaker: str
    ):
        """あゆ's response should always pass context check (only checks やな)"""
        response = "姉様は毒舌ですね。"  # Even if あゆ says this, pass
        history = [{"speaker": "やな", "content": "今日もいい天気だね～"}]
        result = checker.check(ayu_speaker, response, history)
        assert result.passed is True

    def test_empty_history_passes(self, checker: ContextChecker, yana_speaker: str):
        """Empty history should pass (no context to mismatch)"""
        response = "「おはよう、あゆ！」"
        history = []
        result = checker.check(yana_speaker, response, history)
        assert result.passed is True

    # === RETRY cases (context mismatch) ===

    def test_toxicity_reaction_without_toxicity_retries(
        self, checker: ContextChecker, yana_speaker: str
    ):
        """Reacting to non-existent toxicity should RETRY"""
        response = "「毒舌だね～、あゆは」"
        history = [{"speaker": "あゆ", "content": "姉様、おはようございます。今日も良い天気ですね。"}]
        result = checker.check(yana_speaker, response, history)
        assert result.passed is False
        assert result.status == DirectorStatus.RETRY
        assert "文脈" in result.reason or "Context" in result.reason

    def test_harsh_reaction_without_harshness_retries(
        self, checker: ContextChecker, yana_speaker: str
    ):
        """Reacting to non-existent harshness should RETRY"""
        response = "「厳しいこと言うなぁ」"
        history = [{"speaker": "あゆ", "content": "姉様、準備できましたよ。"}]
        result = checker.check(yana_speaker, response, history)
        assert result.passed is False
        assert result.status == DirectorStatus.RETRY

    def test_cruel_reaction_without_cruelty_retries(
        self, checker: ContextChecker, yana_speaker: str
    ):
        """Reacting to non-existent cruelty should RETRY"""
        response = "「辛辣だね～」"
        history = [{"speaker": "あゆ", "content": "姉様、お茶を入れましょうか。"}]
        result = checker.check(yana_speaker, response, history)
        assert result.passed is False
        assert result.status == DirectorStatus.RETRY

    # === Edge cases ===

    def test_only_checks_last_ayu_message(
        self, checker: ContextChecker, yana_speaker: str
    ):
        """Should only check the most recent あゆ message"""
        response = "「毒舌だね～」"
        history = [
            {"speaker": "あゆ", "content": "無駄ですよ。"},  # Old toxic message
            {"speaker": "やな", "content": "そっか～"},
            {"speaker": "あゆ", "content": "姉様、お茶どうぞ。"},  # Recent non-toxic
        ]
        result = checker.check(yana_speaker, response, history)
        assert result.passed is False  # Should fail because recent message is not toxic
        assert result.status == DirectorStatus.RETRY

    def test_multiple_toxic_keywords_detected(
        self, checker: ContextChecker, yana_speaker: str
    ):
        """Multiple toxic keywords should all be detected"""
        response = "「あゆは厳しいね～」"
        history = [{"speaker": "あゆ", "content": "非効率で無理があります。ダメです。"}]
        result = checker.check(yana_speaker, response, history)
        assert result.passed is True  # Multiple toxic words present

    def test_last_speaker_not_ayu_passes(
        self, checker: ContextChecker, yana_speaker: str
    ):
        """If last speaker is not あゆ, context check should pass"""
        response = "「毒舌だね～」"
        history = [
            {"speaker": "あゆ", "content": "姉様、おはよう。"},
            {"speaker": "やな", "content": "おはよう！"},
        ]
        # Last message is from やな, not あゆ, so no context to check
        result = checker.check(yana_speaker, response, history)
        assert result.passed is True

    # === Suggestion in result ===

    def test_retry_includes_helpful_suggestion(
        self, checker: ContextChecker, yana_speaker: str
    ):
        """RETRY result should include helpful suggestion"""
        response = "「毒舌だね～」"
        history = [{"speaker": "あゆ", "content": "姉様、おはようございます。"}]
        result = checker.check(yana_speaker, response, history)
        assert result.details.get("suggestion") is not None
        assert "文脈" in result.details["suggestion"] or "context" in result.details["suggestion"].lower()
