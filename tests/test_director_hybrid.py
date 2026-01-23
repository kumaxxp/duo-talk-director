"""Tests for DirectorHybrid (Phase 2.2)

TDD approach: Write tests first.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import json

from duo_talk_director.interfaces import (
    DirectorStatus,
    DirectorEvaluation,
    DirectorProtocol,
)


class TestDirectorHybridProtocol:
    """Tests for DirectorHybrid protocol compliance"""

    def test_implements_director_protocol(self):
        """DirectorHybrid implements DirectorProtocol"""
        from duo_talk_director.director_hybrid import DirectorHybrid

        mock_client = Mock()
        director = DirectorHybrid(mock_client)

        assert hasattr(director, "evaluate_response")
        assert hasattr(director, "commit_evaluation")
        assert hasattr(director, "reset_for_new_session")


class TestDirectorHybridStaticFirst:
    """Tests for static-first evaluation strategy"""

    def test_static_retry_skips_llm(self):
        """Static RETRY skips LLM evaluation (performance optimization)"""
        from duo_talk_director.director_hybrid import DirectorHybrid

        mock_client = Mock()
        # Should NOT be called because static check fails
        mock_client.generate = Mock(side_effect=Exception("Should not be called"))

        director = DirectorHybrid(mock_client)

        # Response that fails static check (too long - 10+ lines)
        bad_response = "Thought: (考え)\nOutput: 「セリフ」\n" + "\n".join(
            [f"追加行{i}" for i in range(10)]
        )

        result = director.evaluate_response(
            speaker="やな",
            response=bad_response,
            topic="テスト",
            history=[],
            turn_number=0,
        )

        # Static check should fail and return RETRY without calling LLM
        assert result.status == DirectorStatus.RETRY
        # LLM should NOT have been called
        mock_client.generate.assert_not_called()

    def test_static_pass_triggers_llm(self):
        """Static PASS triggers LLM evaluation"""
        from duo_talk_director.director_hybrid import DirectorHybrid

        mock_client = Mock()
        mock_client.generate.return_value = json.dumps({
            "character_consistency": 0.8,
            "topic_novelty": 0.7,
            "relationship_quality": 0.7,
            "naturalness": 0.8,
            "concreteness": 0.6,
            "overall_score": 0.72,
            "issues": [],
            "strengths": [],
        })

        director = DirectorHybrid(mock_client)

        # Good response that passes static checks
        good_response = "Thought: (楽しそう)\nOutput: えー、すっごいじゃん！"

        result = director.evaluate_response(
            speaker="やな",
            response=good_response,
            topic="テスト",
            history=[],
            turn_number=0,
        )

        # LLM should have been called
        mock_client.generate.assert_called_once()
        assert result.status == DirectorStatus.PASS


class TestDirectorHybridMerging:
    """Tests for result merging logic"""

    def test_llm_can_demote_pass_to_warn(self):
        """LLM evaluation can demote PASS to WARN"""
        from duo_talk_director.director_hybrid import DirectorHybrid

        mock_client = Mock()
        # Medium LLM score
        mock_client.generate.return_value = json.dumps({
            "character_consistency": 0.5,
            "topic_novelty": 0.5,
            "relationship_quality": 0.5,
            "naturalness": 0.5,
            "concreteness": 0.5,
            "overall_score": 0.5,  # Below warn threshold
            "issues": ["Character slightly off"],
            "strengths": [],
        })

        director = DirectorHybrid(mock_client)

        # Response that passes static but has medium LLM score
        response = "Thought: (普通)\nOutput: えー、まあまあかな～。"

        result = director.evaluate_response(
            speaker="やな",
            response=response,
            topic="テスト",
            history=[],
            turn_number=0,
        )

        assert result.status == DirectorStatus.WARN

    def test_llm_can_demote_pass_to_retry(self):
        """LLM evaluation can demote PASS to RETRY"""
        from duo_talk_director.director_hybrid import DirectorHybrid

        mock_client = Mock()
        # Very low LLM score
        mock_client.generate.return_value = json.dumps({
            "character_consistency": 0.2,
            "topic_novelty": 0.2,
            "relationship_quality": 0.2,
            "naturalness": 0.2,
            "concreteness": 0.2,
            "overall_score": 0.2,
            "issues": ["Completely wrong character"],
            "strengths": [],
        })

        director = DirectorHybrid(mock_client)

        # Response that passes static but fails LLM
        response = "Thought: (OK)\nOutput: テスト"

        result = director.evaluate_response(
            speaker="やな",
            response=response,
            topic="テスト",
            history=[],
            turn_number=0,
        )

        assert result.status == DirectorStatus.RETRY

    def test_combines_check_results(self):
        """Combined results include checks from both static and LLM"""
        from duo_talk_director.director_hybrid import DirectorHybrid

        mock_client = Mock()
        mock_client.generate.return_value = json.dumps({
            "character_consistency": 0.8,
            "topic_novelty": 0.8,
            "relationship_quality": 0.8,
            "naturalness": 0.8,
            "concreteness": 0.8,
            "overall_score": 0.8,
            "issues": [],
            "strengths": [],
        })

        director = DirectorHybrid(mock_client)
        response = "Thought: (考え)\nOutput: いいじゃん！"

        result = director.evaluate_response(
            speaker="やな",
            response=response,
            topic="テスト",
            history=[],
            turn_number=0,
        )

        # Should have both static and LLM checks in passed list
        assert "llm_evaluation" in result.checks_passed
        # Static checks should also be present
        assert len(result.checks_passed) > 1


class TestDirectorHybridStateManagement:
    """Tests for state management"""

    def test_reset_clears_both_directors(self):
        """reset_for_new_session clears state in both directors"""
        from duo_talk_director.director_hybrid import DirectorHybrid

        mock_client = Mock()
        mock_client.generate.return_value = json.dumps({
            "character_consistency": 0.8,
            "topic_novelty": 0.8,
            "relationship_quality": 0.8,
            "naturalness": 0.8,
            "concreteness": 0.8,
            "overall_score": 0.8,
            "issues": [],
            "strengths": [],
        })

        director = DirectorHybrid(mock_client)

        # Add some state
        evaluation = DirectorEvaluation(status=DirectorStatus.PASS, reason="Test")
        director.commit_evaluation("Test", evaluation)

        # Reset
        director.reset_for_new_session()

        # LLM director history should be cleared
        assert len(director.llm_director._history) == 0


class TestDirectorHybridFallback:
    """Tests for fallback behavior"""

    def test_llm_error_falls_back_to_static_result(self):
        """LLM error falls back to static check result"""
        from duo_talk_director.director_hybrid import DirectorHybrid

        mock_client = Mock()
        mock_client.generate.side_effect = Exception("LLM unavailable")

        director = DirectorHybrid(mock_client)
        response = "Thought: (考え)\nOutput: いいじゃん！"

        result = director.evaluate_response(
            speaker="やな",
            response=response,
            topic="テスト",
            history=[],
            turn_number=0,
        )

        # Should still return a result (fallback to WARN, not crash)
        assert result.status in [DirectorStatus.PASS, DirectorStatus.WARN]

    def test_skip_llm_on_static_retry_configurable(self):
        """skip_llm_on_static_retry can be disabled"""
        from duo_talk_director.director_hybrid import DirectorHybrid

        mock_client = Mock()
        mock_client.generate.return_value = json.dumps({
            "character_consistency": 0.9,
            "topic_novelty": 0.9,
            "relationship_quality": 0.9,
            "naturalness": 0.9,
            "concreteness": 0.9,
            "overall_score": 0.9,
            "issues": [],
            "strengths": [],
        })

        # Disable skip_llm_on_static_retry
        director = DirectorHybrid(mock_client, skip_llm_on_static_retry=False)

        # Response that fails static check (too long)
        bad_response = "Thought: (考え)\nOutput: 「セリフ」\n" + "\n".join(
            [f"追加行{i}" for i in range(10)]
        )

        result = director.evaluate_response(
            speaker="やな",
            response=bad_response,
            topic="テスト",
            history=[],
            turn_number=0,
        )

        # LLM should have been called (because skip is disabled)
        mock_client.generate.assert_called_once()
