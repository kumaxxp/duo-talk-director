"""Tests for DirectorLLM (Phase 2.2)

TDD approach: Write tests first.
"""

import pytest
from unittest.mock import Mock, MagicMock
import json

from duo_talk_director.interfaces import (
    DirectorStatus,
    DirectorEvaluation,
    DirectorProtocol,
    LLMEvaluationScore,
)


class TestDirectorLLMProtocol:
    """Tests for DirectorLLM protocol compliance"""

    def test_implements_director_protocol(self):
        """DirectorLLM implements DirectorProtocol"""
        from duo_talk_director.director_llm import DirectorLLM

        mock_client = Mock()
        director = DirectorLLM(mock_client)

        # Check method signatures exist
        assert hasattr(director, "evaluate_response")
        assert hasattr(director, "commit_evaluation")
        assert hasattr(director, "reset_for_new_session")


class TestDirectorLLMEvaluateResponse:
    """Tests for evaluate_response method"""

    def test_evaluate_response_returns_evaluation(self):
        """evaluate_response returns DirectorEvaluation"""
        from duo_talk_director.director_llm import DirectorLLM

        mock_client = Mock()
        mock_client.generate.return_value = json.dumps({
            "character_consistency": 0.8,
            "topic_novelty": 0.7,
            "relationship_quality": 0.7,
            "naturalness": 0.8,
            "concreteness": 0.6,
            "overall_score": 0.72,
            "issues": [],
            "strengths": ["Good tone"],
        })

        director = DirectorLLM(mock_client)
        result = director.evaluate_response(
            speaker="やな",
            response="Thought: (楽しそう)\nOutput: えー、すっごいじゃん！",
            topic="テスト",
            history=[],
            turn_number=0,
        )

        assert isinstance(result, DirectorEvaluation)
        assert result.status == DirectorStatus.PASS

    def test_high_score_returns_pass(self):
        """High evaluation score returns PASS status"""
        from duo_talk_director.director_llm import DirectorLLM

        mock_client = Mock()
        mock_client.generate.return_value = json.dumps({
            "character_consistency": 0.9,
            "topic_novelty": 0.8,
            "relationship_quality": 0.8,
            "naturalness": 0.9,
            "concreteness": 0.7,
            "overall_score": 0.84,
            "issues": [],
            "strengths": [],
        })

        director = DirectorLLM(mock_client)
        result = director.evaluate_response(
            speaker="やな",
            response="Output: テスト",
            topic="テスト",
            history=[],
            turn_number=0,
        )

        assert result.status == DirectorStatus.PASS

    def test_low_score_returns_retry(self):
        """Low evaluation score returns RETRY status"""
        from duo_talk_director.director_llm import DirectorLLM

        mock_client = Mock()
        mock_client.generate.return_value = json.dumps({
            "character_consistency": 0.2,
            "topic_novelty": 0.3,
            "relationship_quality": 0.3,
            "naturalness": 0.3,
            "concreteness": 0.2,
            "overall_score": 0.26,
            "issues": ["Character inconsistent"],
            "strengths": [],
        })

        director = DirectorLLM(mock_client)
        result = director.evaluate_response(
            speaker="やな",
            response="Output: テスト",
            topic="テスト",
            history=[],
            turn_number=0,
        )

        assert result.status == DirectorStatus.RETRY

    def test_medium_score_returns_warn(self):
        """Medium evaluation score returns WARN status"""
        from duo_talk_director.director_llm import DirectorLLM

        mock_client = Mock()
        mock_client.generate.return_value = json.dumps({
            "character_consistency": 0.5,
            "topic_novelty": 0.5,
            "relationship_quality": 0.5,
            "naturalness": 0.5,
            "concreteness": 0.5,
            "overall_score": 0.5,
            "issues": ["Some minor issues"],
            "strengths": [],
        })

        director = DirectorLLM(mock_client)
        result = director.evaluate_response(
            speaker="やな",
            response="Output: テスト",
            topic="テスト",
            history=[],
            turn_number=0,
        )

        assert result.status == DirectorStatus.WARN

    def test_extracts_output_from_thought_output_format(self):
        """Evaluator extracts Output section for evaluation"""
        from duo_talk_director.director_llm import DirectorLLM, extract_output

        # Test extract_output helper
        response = "Thought: (考え中)\nOutput: これがセリフです。"
        output = extract_output(response)
        assert output == "これがセリフです。"

    def test_extracts_output_handles_no_marker(self):
        """Evaluator handles response without Output marker"""
        from duo_talk_director.director_llm import extract_output

        response = "これはマーカーなしのレスポンス"
        output = extract_output(response)
        assert output == response  # Returns full response


class TestDirectorLLMStateManagement:
    """Tests for state management methods"""

    def test_commit_evaluation_stores_history(self):
        """commit_evaluation stores evaluation in history"""
        from duo_talk_director.director_llm import DirectorLLM

        mock_client = Mock()
        director = DirectorLLM(mock_client)

        evaluation = DirectorEvaluation(
            status=DirectorStatus.PASS,
            reason="Test",
        )

        director.commit_evaluation("Test response", evaluation)

        assert len(director._history) == 1
        assert director._history[0]["response"] == "Test response"

    def test_reset_for_new_session_clears_history(self):
        """reset_for_new_session clears history"""
        from duo_talk_director.director_llm import DirectorLLM

        mock_client = Mock()
        director = DirectorLLM(mock_client)

        # Add some history
        evaluation = DirectorEvaluation(status=DirectorStatus.PASS, reason="Test")
        director.commit_evaluation("Response 1", evaluation)
        director.commit_evaluation("Response 2", evaluation)

        assert len(director._history) == 2

        # Reset
        director.reset_for_new_session()

        assert len(director._history) == 0


class TestDirectorLLMErrorHandling:
    """Tests for error handling"""

    def test_llm_error_returns_warn_with_fallback(self):
        """LLM error returns WARN status with error message"""
        from duo_talk_director.director_llm import DirectorLLM

        mock_client = Mock()
        mock_client.generate.side_effect = Exception("LLM connection failed")

        director = DirectorLLM(mock_client)
        result = director.evaluate_response(
            speaker="やな",
            response="Output: テスト",
            topic="テスト",
            history=[],
            turn_number=0,
        )

        # Should not crash, returns fallback
        assert result.status == DirectorStatus.WARN
        assert "error" in result.reason.lower() or "LLM" in result.reason


class TestExtractOutput:
    """Tests for extract_output helper function"""

    def test_extracts_from_standard_format(self):
        """Extracts Output from Thought/Output format"""
        from duo_talk_director.director_llm import extract_output

        response = "Thought: (内心の考え)\nOutput: (笑顔で) 「こんにちは！」"
        assert extract_output(response) == "(笑顔で) 「こんにちは！」"

    def test_handles_multiline_output(self):
        """Handles multiline Output section"""
        from duo_talk_director.director_llm import extract_output

        response = "Thought: (考え)\nOutput: (動作)\n「セリフ1」\n「セリフ2」"
        output = extract_output(response)
        assert "(動作)" in output
        assert "「セリフ1」" in output

    def test_returns_full_if_no_marker(self):
        """Returns full response if no Output marker"""
        from duo_talk_director.director_llm import extract_output

        response = "これはマーカーなし"
        assert extract_output(response) == response

    def test_handles_lowercase_output(self):
        """Handles lowercase 'output:' marker"""
        from duo_talk_director.director_llm import extract_output

        response = "Thought: (考え)\noutput: テスト"
        output = extract_output(response)
        assert "テスト" in output
