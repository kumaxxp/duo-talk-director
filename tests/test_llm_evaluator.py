"""Tests for LLM Evaluator (Phase 2.2)

TDD approach: Write tests first, then implement.
"""

import pytest
from unittest.mock import Mock, patch
import json

from duo_talk_director.interfaces import LLMEvaluationScore


class TestLLMEvaluationScore:
    """Tests for LLMEvaluationScore dataclass"""

    def test_auto_calculates_overall_score(self):
        """overall_score is auto-calculated from weighted average"""
        score = LLMEvaluationScore(
            character_consistency=0.8,
            topic_novelty=0.7,
            relationship_quality=0.6,
            naturalness=0.9,
            concreteness=0.5,
        )
        # 0.8*0.25 + 0.7*0.20 + 0.6*0.25 + 0.9*0.15 + 0.5*0.15 = 0.7
        assert abs(score.overall_score - 0.7) < 0.001

    def test_explicit_overall_score_not_overwritten(self):
        """Explicit overall_score is not overwritten"""
        score = LLMEvaluationScore(
            character_consistency=0.8,
            topic_novelty=0.7,
            relationship_quality=0.6,
            naturalness=0.9,
            concreteness=0.5,
            overall_score=0.85,  # Explicit value
        )
        assert score.overall_score == 0.85

    def test_default_lists_are_empty(self):
        """issues and strengths default to empty lists"""
        score = LLMEvaluationScore(
            character_consistency=0.8,
            topic_novelty=0.7,
            relationship_quality=0.6,
            naturalness=0.9,
            concreteness=0.5,
        )
        assert score.issues == []
        assert score.strengths == []


class TestLLMEvaluator:
    """Tests for LLMEvaluator class"""

    def test_evaluate_single_turn_returns_score(self):
        """evaluate_single_turn returns LLMEvaluationScore"""
        from duo_talk_director.llm.evaluator import LLMEvaluator

        # Mock LLM client
        mock_client = Mock()
        mock_client.generate.return_value = json.dumps({
            "character_consistency": 0.8,
            "topic_novelty": 0.7,
            "relationship_quality": 0.6,
            "naturalness": 0.9,
            "concreteness": 0.5,
            "overall_score": 0.7,
            "issues": [],
            "strengths": ["Good character voice"],
        })

        evaluator = LLMEvaluator(mock_client)
        score = evaluator.evaluate_single_turn(
            speaker="やな",
            response="えー、すっごいじゃん！",
            topic="テスト",
            history=[],
        )

        assert isinstance(score, LLMEvaluationScore)
        assert score.character_consistency == 0.8

    def test_parse_valid_json_response(self):
        """_parse_response correctly parses valid JSON"""
        from duo_talk_director.llm.evaluator import LLMEvaluator

        mock_client = Mock()
        evaluator = LLMEvaluator(mock_client)

        json_text = json.dumps({
            "character_consistency": 0.8,
            "topic_novelty": 0.7,
            "relationship_quality": 0.6,
            "naturalness": 0.9,
            "concreteness": 0.5,
            "overall_score": 0.7,
            "issues": ["Too short"],
            "strengths": ["Good tone"],
        })

        score = evaluator._parse_response(json_text)
        assert score.character_consistency == 0.8
        assert "Too short" in score.issues

    def test_parse_json_with_surrounding_text(self):
        """_parse_response extracts JSON from surrounding text"""
        from duo_talk_director.llm.evaluator import LLMEvaluator

        mock_client = Mock()
        evaluator = LLMEvaluator(mock_client)

        response_text = """以下が評価結果です：

{
  "character_consistency": 0.8,
  "topic_novelty": 0.7,
  "relationship_quality": 0.6,
  "naturalness": 0.9,
  "concreteness": 0.5,
  "overall_score": 0.7,
  "issues": [],
  "strengths": []
}

以上です。"""

        score = evaluator._parse_response(response_text)
        assert score.character_consistency == 0.8

    def test_parse_malformed_json_returns_default(self):
        """_parse_response returns default score for malformed JSON"""
        from duo_talk_director.llm.evaluator import LLMEvaluator

        mock_client = Mock()
        evaluator = LLMEvaluator(mock_client)

        malformed = "This is not JSON at all"
        score = evaluator._parse_response(malformed)

        # Default values
        assert score.character_consistency == 0.5
        assert score.topic_novelty == 0.5
        assert "JSON parse error" in score.issues[0]

    def test_clamps_scores_to_valid_range(self):
        """Scores are clamped to 0.0-1.0 range"""
        from duo_talk_director.llm.evaluator import LLMEvaluator

        mock_client = Mock()
        evaluator = LLMEvaluator(mock_client)

        json_text = json.dumps({
            "character_consistency": 1.5,  # Over 1.0
            "topic_novelty": -0.2,  # Below 0.0
            "relationship_quality": 0.6,
            "naturalness": 0.9,
            "concreteness": 0.5,
            "overall_score": 0.7,
            "issues": [],
            "strengths": [],
        })

        score = evaluator._parse_response(json_text)
        assert score.character_consistency == 1.0  # Clamped
        assert score.topic_novelty == 0.0  # Clamped


class TestPrompts:
    """Tests for evaluation prompts"""

    def test_single_turn_prompt_has_speaker_placeholder(self):
        """SINGLE_TURN_PROMPT has {speaker} placeholder"""
        from duo_talk_director.llm.prompts import SINGLE_TURN_PROMPT

        assert "{speaker}" in SINGLE_TURN_PROMPT

    def test_single_turn_prompt_has_response_placeholder(self):
        """SINGLE_TURN_PROMPT has {response} placeholder"""
        from duo_talk_director.llm.prompts import SINGLE_TURN_PROMPT

        assert "{response}" in SINGLE_TURN_PROMPT

    def test_format_history_empty(self):
        """format_history returns placeholder for empty history"""
        from duo_talk_director.llm.prompts import format_history

        result = format_history([])
        assert "会話開始" in result or "なし" in result.lower()

    def test_format_history_with_messages(self):
        """format_history formats messages correctly"""
        from duo_talk_director.llm.prompts import format_history

        history = [
            {"speaker": "やな", "content": "おはよう！"},
            {"speaker": "あゆ", "content": "おはようございます、姉様。"},
        ]
        result = format_history(history)
        assert "やな" in result
        assert "おはよう！" in result
        assert "あゆ" in result
