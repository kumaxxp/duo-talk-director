"""Tests for DirectorMinimal"""

import pytest

from duo_talk_director import DirectorMinimal
from duo_talk_director.interfaces import DirectorStatus, DirectorEvaluation


class TestDirectorMinimal:
    """Tests for DirectorMinimal class"""

    @pytest.fixture
    def director(self) -> DirectorMinimal:
        return DirectorMinimal()

    # === evaluate_response tests ===

    def test_good_yana_response_passes(
        self,
        director: DirectorMinimal,
        yana_speaker: str,
        yana_good_response: str,
        sample_history: list[dict],
    ):
        """Good やな response should PASS"""
        result = director.evaluate_response(
            speaker=yana_speaker,
            response=yana_good_response,
            topic="テスト",
            history=sample_history,
            turn_number=2,
        )
        assert result.status == DirectorStatus.PASS
        assert "tone_check" in result.checks_passed

    def test_good_ayu_response_passes(
        self,
        director: DirectorMinimal,
        ayu_speaker: str,
        ayu_good_response: str,
        sample_history: list[dict],
    ):
        """Good あゆ response should PASS"""
        result = director.evaluate_response(
            speaker=ayu_speaker,
            response=ayu_good_response,
            topic="テスト",
            history=sample_history,
            turn_number=3,
        )
        assert result.status == DirectorStatus.PASS

    def test_bad_tone_triggers_retry(
        self,
        director: DirectorMinimal,
        yana_speaker: str,
        yana_bad_response: str,
        sample_history: list[dict],
    ):
        """Response with bad tone should RETRY"""
        result = director.evaluate_response(
            speaker=yana_speaker,
            response=yana_bad_response,
            topic="テスト",
            history=sample_history,
            turn_number=2,
        )
        assert result.status == DirectorStatus.RETRY
        assert "tone_check" in result.checks_failed

    def test_praise_triggers_retry(
        self,
        director: DirectorMinimal,
        ayu_speaker: str,
        ayu_praise_response: str,
        sample_history: list[dict],
    ):
        """あゆ with inappropriate praise should RETRY"""
        result = director.evaluate_response(
            speaker=ayu_speaker,
            response=ayu_praise_response,
            topic="テスト",
            history=sample_history,
            turn_number=3,
        )
        assert result.status == DirectorStatus.RETRY
        assert "praise_check" in result.checks_failed

    def test_setting_breaking_triggers_retry(
        self,
        director: DirectorMinimal,
        yana_speaker: str,
        setting_breaking_response: str,
        sample_history: list[dict],
    ):
        """Setting-breaking response should RETRY"""
        # Use yana_good_response style but with setting-breaking content
        # Must pass tone_check first to reach setting_check
        response = "えー、実家ではよくお茶を飲んでたよね～"
        result = director.evaluate_response(
            speaker=yana_speaker,
            response=response,
            topic="テスト",
            history=sample_history,
            turn_number=2,
        )
        assert result.status == DirectorStatus.RETRY
        assert "setting_check" in result.checks_failed

    def test_long_response_triggers_retry(
        self,
        director: DirectorMinimal,
        yana_speaker: str,
        long_response: str,
        sample_history: list[dict],
    ):
        """Long response should RETRY after passing other checks"""
        result = director.evaluate_response(
            speaker=yana_speaker,
            response=long_response,
            topic="テスト",
            history=sample_history,
            turn_number=2,
        )
        assert result.status == DirectorStatus.RETRY
        assert "format_check" in result.checks_failed
        # Should have passed tone_check, praise_check, setting_check
        assert "tone_check" in result.checks_passed

    def test_warns_collected_not_blocking(
        self,
        director: DirectorMinimal,
        ayu_speaker: str,
        medium_response: str,
        sample_history: list[dict],
    ):
        """Warnings should be collected but not block PASS/WARN"""
        # Create a response that's medium length but otherwise okay for Ayu
        lines = [
            "一般的に言えば、",
            "これはつまり、",
            "推奨される方法ですね。",
            "そうですよ。",
            "はい、そうです。",
            "確かにそうですね。",
        ]
        response = "\n".join(lines)

        result = director.evaluate_response(
            speaker=ayu_speaker,
            response=response,
            topic="テスト",
            history=sample_history,
            turn_number=3,
        )
        # Should be WARN (not RETRY) because format is 6 lines
        assert result.status == DirectorStatus.WARN
        assert "format_check" in result.checks_passed

    def test_first_retry_stops_evaluation(
        self,
        director: DirectorMinimal,
        yana_speaker: str,
        sample_history: list[dict],
    ):
        """First RETRY should stop further checks"""
        # Response that passes tone/praise but fails setting_check
        # Also has a long format (8+ lines), but should stop at setting_check
        response = "えー、また遊びに来てね～！すっごいじゃん！"

        result = director.evaluate_response(
            speaker=yana_speaker,
            response=response,
            topic="テスト",
            history=sample_history,
            turn_number=2,
        )

        assert result.status == DirectorStatus.RETRY
        # Should pass tone_check, praise_check, then fail setting_check
        assert "setting_check" in result.checks_failed
        # format_check should not be checked since we stopped at setting_check
        assert "format_check" not in result.checks_passed
        assert "format_check" not in result.checks_failed

    def test_evaluation_contains_suggestion(
        self,
        director: DirectorMinimal,
        yana_speaker: str,
        yana_bad_response: str,
        sample_history: list[dict],
    ):
        """RETRY evaluation should contain suggestion"""
        result = director.evaluate_response(
            speaker=yana_speaker,
            response=yana_bad_response,
            topic="テスト",
            history=sample_history,
            turn_number=2,
        )
        assert result.suggestion is not None

    # === commit_evaluation tests ===

    def test_commit_evaluation_noop(
        self,
        director: DirectorMinimal,
        yana_good_response: str,
    ):
        """commit_evaluation should be a no-op for minimal director"""
        evaluation = DirectorEvaluation(
            status=DirectorStatus.PASS,
            reason="OK",
        )
        # Should not raise
        director.commit_evaluation(yana_good_response, evaluation)

    # === reset_for_new_session tests ===

    def test_reset_for_new_session_noop(self, director: DirectorMinimal):
        """reset_for_new_session should be a no-op for minimal director"""
        # Should not raise
        director.reset_for_new_session()

    # === Integration scenarios ===

    def test_full_dialogue_scenario(
        self,
        director: DirectorMinimal,
    ):
        """Test a full dialogue scenario with PASS or WARN results"""
        history: list[dict] = []
        topic = "AIの話"

        # Turn 1: やな starts
        response1 = "えー、AIの話？すっごい面白そうじゃん！"
        result1 = director.evaluate_response(
            speaker="やな",
            response=response1,
            topic=topic,
            history=history,
            turn_number=0,
        )
        assert result1.status == DirectorStatus.PASS
        history.append({"speaker": "やな", "content": response1})

        # Turn 2: あゆ responds (with more polite markers)
        response2 = "姉様、一般的に言えば、AIは様々な分野で使われていますね。推奨されるのはですね、機械学習ですよ。"
        result2 = director.evaluate_response(
            speaker="あゆ",
            response=response2,
            topic=topic,
            history=history,
            turn_number=1,
        )
        # PASS or WARN is acceptable (not RETRY)
        assert result2.status in [DirectorStatus.PASS, DirectorStatus.WARN]
        history.append({"speaker": "あゆ", "content": response2})

        # Turn 3: やな continues (with more markers for score >= 2)
        response3 = "そっか～、あゆはほんと詳しいね！すっごいじゃん！"
        result3 = director.evaluate_response(
            speaker="やな",
            response=response3,
            topic=topic,
            history=history,
            turn_number=2,
        )
        assert result3.status in [DirectorStatus.PASS, DirectorStatus.WARN]

    def test_retry_reason_is_informative(
        self,
        director: DirectorMinimal,
        sample_history: list[dict],
    ):
        """RETRY reason should explain what went wrong (v2.1 violation-based)"""
        # Bad tone for やな (uses forbidden endings です/ます)
        result = director.evaluate_response(
            speaker="やな",
            response="わかりました。了解です。",
            topic="テスト",
            history=sample_history,
            turn_number=2,
        )
        assert result.status == DirectorStatus.RETRY
        # v2.1: Reason includes role violation info instead of score
        assert "役割違反" in result.reason or "禁止" in result.reason


class TestDirectorProtocolCompliance:
    """Tests that DirectorMinimal complies with DirectorProtocol"""

    def test_has_evaluate_response_method(self):
        """Should have evaluate_response method"""
        director = DirectorMinimal()
        assert hasattr(director, "evaluate_response")
        assert callable(director.evaluate_response)

    def test_has_commit_evaluation_method(self):
        """Should have commit_evaluation method"""
        director = DirectorMinimal()
        assert hasattr(director, "commit_evaluation")
        assert callable(director.commit_evaluation)

    def test_has_reset_for_new_session_method(self):
        """Should have reset_for_new_session method"""
        director = DirectorMinimal()
        assert hasattr(director, "reset_for_new_session")
        assert callable(director.reset_for_new_session)

    def test_evaluate_response_returns_evaluation(self):
        """evaluate_response should return DirectorEvaluation"""
        director = DirectorMinimal()
        result = director.evaluate_response(
            speaker="やな",
            response="えー、すっごいじゃん！",
            topic="test",
            history=[],
            turn_number=0,
        )
        assert isinstance(result, DirectorEvaluation)
        assert isinstance(result.status, DirectorStatus)
