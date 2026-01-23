"""Tests for threshold configuration (Phase 2.2)

TDD approach: Write tests first.
"""

import pytest

from duo_talk_director.interfaces import DirectorStatus, LLMEvaluationScore


class TestThresholdConfig:
    """Tests for ThresholdConfig dataclass"""

    def test_default_values(self):
        """Default values are set correctly"""
        from duo_talk_director.config.thresholds import ThresholdConfig

        config = ThresholdConfig()
        assert config.retry_overall == 0.4
        assert config.retry_character == 0.3
        assert config.retry_relationship == 0.3
        assert config.warn_overall == 0.6

    def test_custom_values(self):
        """Custom values can be set"""
        from duo_talk_director.config.thresholds import ThresholdConfig

        config = ThresholdConfig(
            retry_overall=0.5,
            warn_overall=0.7,
        )
        assert config.retry_overall == 0.5
        assert config.warn_overall == 0.7


class TestDetermineStatus:
    """Tests for determine_status function"""

    def test_high_overall_returns_pass(self):
        """High overall score returns PASS"""
        from duo_talk_director.config.thresholds import ThresholdConfig, determine_status

        score = LLMEvaluationScore(
            character_consistency=0.8,
            topic_novelty=0.7,
            relationship_quality=0.7,
            naturalness=0.8,
            concreteness=0.6,
            overall_score=0.72,  # > 0.6
        )
        config = ThresholdConfig()
        status = determine_status(score, config)
        assert status == DirectorStatus.PASS

    def test_medium_overall_returns_warn(self):
        """Medium overall score returns WARN"""
        from duo_talk_director.config.thresholds import ThresholdConfig, determine_status

        score = LLMEvaluationScore(
            character_consistency=0.6,
            topic_novelty=0.5,
            relationship_quality=0.5,
            naturalness=0.6,
            concreteness=0.5,
            overall_score=0.55,  # 0.4 <= x < 0.6
        )
        config = ThresholdConfig()
        status = determine_status(score, config)
        assert status == DirectorStatus.WARN

    def test_low_overall_returns_retry(self):
        """Low overall score returns RETRY"""
        from duo_talk_director.config.thresholds import ThresholdConfig, determine_status

        score = LLMEvaluationScore(
            character_consistency=0.4,
            topic_novelty=0.3,
            relationship_quality=0.4,
            naturalness=0.4,
            concreteness=0.3,
            overall_score=0.35,  # < 0.4
        )
        config = ThresholdConfig()
        status = determine_status(score, config)
        assert status == DirectorStatus.RETRY

    def test_low_character_returns_retry_even_if_overall_ok(self):
        """Low character_consistency triggers RETRY even if overall is OK"""
        from duo_talk_director.config.thresholds import ThresholdConfig, determine_status

        score = LLMEvaluationScore(
            character_consistency=0.2,  # Below retry_character (0.3)
            topic_novelty=0.9,
            relationship_quality=0.9,
            naturalness=0.9,
            concreteness=0.9,
            overall_score=0.76,  # Overall is high
        )
        config = ThresholdConfig()
        status = determine_status(score, config)
        assert status == DirectorStatus.RETRY

    def test_low_relationship_returns_retry_even_if_overall_ok(self):
        """Low relationship_quality triggers RETRY even if overall is OK"""
        from duo_talk_director.config.thresholds import ThresholdConfig, determine_status

        score = LLMEvaluationScore(
            character_consistency=0.9,
            topic_novelty=0.9,
            relationship_quality=0.2,  # Below retry_relationship (0.3)
            naturalness=0.9,
            concreteness=0.9,
            overall_score=0.76,  # Overall is high
        )
        config = ThresholdConfig()
        status = determine_status(score, config)
        assert status == DirectorStatus.RETRY

    def test_boundary_exactly_at_warn_threshold(self):
        """Score exactly at warn threshold returns PASS"""
        from duo_talk_director.config.thresholds import ThresholdConfig, determine_status

        score = LLMEvaluationScore(
            character_consistency=0.6,
            topic_novelty=0.6,
            relationship_quality=0.6,
            naturalness=0.6,
            concreteness=0.6,
            overall_score=0.6,  # == warn_overall
        )
        config = ThresholdConfig()
        status = determine_status(score, config)
        assert status == DirectorStatus.PASS

    def test_boundary_exactly_at_retry_threshold(self):
        """Score exactly at retry threshold returns WARN"""
        from duo_talk_director.config.thresholds import ThresholdConfig, determine_status

        score = LLMEvaluationScore(
            character_consistency=0.4,
            topic_novelty=0.4,
            relationship_quality=0.4,
            naturalness=0.4,
            concreteness=0.4,
            overall_score=0.4,  # == retry_overall
        )
        config = ThresholdConfig()
        status = determine_status(score, config)
        assert status == DirectorStatus.WARN


class TestBuildReason:
    """Tests for build_reason function"""

    def test_build_reason_for_pass(self):
        """build_reason returns appropriate message for PASS"""
        from duo_talk_director.config.thresholds import build_reason

        score = LLMEvaluationScore(
            character_consistency=0.8,
            topic_novelty=0.7,
            relationship_quality=0.7,
            naturalness=0.8,
            concreteness=0.6,
            overall_score=0.72,
        )
        reason = build_reason(score, DirectorStatus.PASS)
        assert "0.72" in reason or "72" in reason

    def test_build_reason_includes_issues(self):
        """build_reason includes issues list"""
        from duo_talk_director.config.thresholds import build_reason

        score = LLMEvaluationScore(
            character_consistency=0.3,
            topic_novelty=0.3,
            relationship_quality=0.3,
            naturalness=0.3,
            concreteness=0.3,
            issues=["Character voice inconsistent", "Too repetitive"],
        )
        reason = build_reason(score, DirectorStatus.RETRY)
        assert "Character voice" in reason or "issues" in reason.lower()
