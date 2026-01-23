"""Integration tests for duo-talk-director with duo-talk-core

Tests the Director integration with DialogueManager from duo-talk-core.
"""

import pytest
from unittest.mock import MagicMock, patch

from duo_talk_director import DirectorMinimal
from duo_talk_director.interfaces import DirectorStatus, DirectorEvaluation


class TestDirectorIntegrationWithCore:
    """Tests for Director integration with duo-talk-core"""

    @pytest.fixture
    def director(self) -> DirectorMinimal:
        return DirectorMinimal()

    @pytest.fixture
    def mock_llm_client(self):
        """Create a mock LLM client"""
        client = MagicMock()
        client.is_available.return_value = True
        return client

    def test_director_protocol_compatible_with_core(self, director: DirectorMinimal):
        """Director should be compatible with duo-talk-core protocol"""
        # Check method signatures match what duo-talk-core expects
        assert hasattr(director, "evaluate_response")
        assert hasattr(director, "commit_evaluation")
        assert hasattr(director, "reset_for_new_session")

        # Test evaluate_response signature
        result = director.evaluate_response(
            speaker="やな",
            response="えー、すっごいじゃん！",
            topic="テスト",
            history=[],
            turn_number=0,
        )
        assert isinstance(result, DirectorEvaluation)
        assert hasattr(result, "status")
        assert hasattr(result, "reason")

    def test_director_status_values_match(self, director: DirectorMinimal):
        """Director status values should work with string comparison"""
        # duo-talk-core checks status as string
        result = director.evaluate_response(
            speaker="やな",
            response="えー、すっごいじゃん！",
            topic="テスト",
            history=[],
            turn_number=0,
        )
        assert result.status in ("PASS", "WARN", "RETRY", "MODIFY")
        assert result.status == DirectorStatus.PASS

    def test_director_retry_scenario(self, director: DirectorMinimal):
        """Test scenario where Director requests RETRY"""
        # Response with bad tone should trigger RETRY
        result = director.evaluate_response(
            speaker="やな",
            response="わかりました。了解です。",
            topic="テスト",
            history=[],
            turn_number=0,
        )
        assert result.status == DirectorStatus.RETRY
        assert result.status == "RETRY"

    def test_director_warn_scenario(self, director: DirectorMinimal):
        """Test scenario where Director returns WARN (v2.1: excessive exclamation)"""
        # Response with excessive exclamation marks (>3) causes WARN
        result = director.evaluate_response(
            speaker="やな",
            response="すごい！やばい！最高！これは！ほんとに！",
            topic="テスト",
            history=[],
            turn_number=0,
        )
        # v2.1: Excessive ！ causes WARN
        assert result.status == DirectorStatus.WARN

    @pytest.mark.skipif(
        True,  # Skip by default - requires duo-talk-core import
        reason="Requires duo-talk-core to be installed",
    )
    def test_full_integration_with_dialogue_manager(
        self, director: DirectorMinimal, mock_llm_client
    ):
        """Full integration test with DialogueManager"""
        try:
            from duo_talk_core import DialogueManager
        except ImportError:
            pytest.skip("duo-talk-core not installed")

        # This would be a full integration test
        # Skipped by default as it requires duo-talk-core


class TestDirectorWithMockedDialogueManager:
    """Tests simulating DialogueManager behavior with Director"""

    @pytest.fixture
    def director(self) -> DirectorMinimal:
        return DirectorMinimal()

    def test_retry_loop_simulation(self, director: DirectorMinimal):
        """Simulate DialogueManager retry loop with Director (v2.1 violation-based)"""
        max_retries = 3
        responses = [
            "わかりました。了解です。",  # RETRY (v2.1: forbidden ending ます/です)
            "そうですね。理解しています。",  # RETRY (v2.1: forbidden ending です/ます)
            "えー、すっごいじゃん！",  # PASS (no violations)
        ]

        accepted_response = None
        retry_count = 0
        for attempt, response in enumerate(responses[:max_retries]):
            evaluation = director.evaluate_response(
                speaker="やな",
                response=response,
                topic="テスト",
                history=[],
                turn_number=0,
            )

            if evaluation.status in ("PASS", "WARN"):
                director.commit_evaluation(response, evaluation)
                accepted_response = response
                break
            retry_count += 1

        # Should have retried twice and accepted the third response
        assert retry_count == 2
        assert accepted_response == "えー、すっごいじゃん！"

    def test_session_reset(self, director: DirectorMinimal):
        """Test that reset_for_new_session works"""
        # Run some evaluations
        director.evaluate_response(
            speaker="やな",
            response="えー、すっごいじゃん！",
            topic="テスト",
            history=[],
            turn_number=0,
        )

        # Reset should not raise
        director.reset_for_new_session()

    def test_multiple_turns_evaluation(self, director: DirectorMinimal):
        """Test evaluating multiple turns in a session"""
        history: list[dict] = []

        # Turn 0: やな
        response0 = "えー、AIの話？すっごい面白そうじゃん！"
        result0 = director.evaluate_response(
            speaker="やな",
            response=response0,
            topic="AIの話",
            history=history,
            turn_number=0,
        )
        assert result0.status in ("PASS", "WARN")
        director.commit_evaluation(response0, result0)
        history.append({"speaker": "やな", "content": response0})

        # Turn 1: あゆ
        response1 = "姉様、一般的に言えば、AIは様々な分野で推奨されていますね。"
        result1 = director.evaluate_response(
            speaker="あゆ",
            response=response1,
            topic="AIの話",
            history=history,
            turn_number=1,
        )
        assert result1.status in ("PASS", "WARN")
        director.commit_evaluation(response1, result1)

    def test_ayu_praise_rejection(self, director: DirectorMinimal):
        """Test that Ayu's inappropriate praise is rejected"""
        result = director.evaluate_response(
            speaker="あゆ",
            response="さすがですね、あなたの考えは素晴らしいです。",
            topic="テスト",
            history=[],
            turn_number=0,
        )
        assert result.status == DirectorStatus.RETRY
        assert "praise" in result.checks_failed or "praise_check" in result.checks_failed

    def test_setting_violation_rejection(self, director: DirectorMinimal):
        """Test that setting violations are rejected"""
        result = director.evaluate_response(
            speaker="やな",
            response="えー、実家ではよく～だったよね！すっごいじゃん！",
            topic="テスト",
            history=[],
            turn_number=0,
        )
        assert result.status == DirectorStatus.RETRY
        assert "setting_check" in result.checks_failed
