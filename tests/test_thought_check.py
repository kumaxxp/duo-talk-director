"""Tests for ThoughtChecker - Thought truncation detection

TDD: RED phase - These tests should FAIL initially.

ThoughtChecker detects:
1. Empty Thoughts: "Thought: (\n" or "Thought: \n"
2. Truncated Thoughts: "Thought: (やな:" without closing
3. Missing Thoughts: Response starts with Output without Thought
"""

import pytest
from duo_talk_director.checks.thought_check import ThoughtChecker
from duo_talk_director.interfaces import DirectorStatus


class TestThoughtCheckerEmpty:
    """Test empty Thought detection"""

    @pytest.fixture
    def checker(self):
        return ThoughtChecker()

    def test_empty_thought_with_parenthesis_retries(self, checker):
        """Empty Thought with just open parenthesis triggers RETRY"""
        response = "Thought: (\nOutput: (笑顔で) 「おはよう！」"
        result = checker.check(response)
        assert result.passed is False
        assert result.status == DirectorStatus.RETRY
        assert "Thought" in result.reason

    def test_empty_thought_whitespace_only_retries(self, checker):
        """Thought with only whitespace triggers RETRY"""
        response = "Thought:    \nOutput: (笑顔で) 「おはよう！」"
        result = checker.check(response)
        assert result.passed is False
        assert result.status == DirectorStatus.RETRY

    def test_empty_thought_newline_only_retries(self, checker):
        """Thought with immediate newline triggers RETRY"""
        response = "Thought:\nOutput: 「おはよう」"
        result = checker.check(response)
        assert result.passed is False
        assert result.status == DirectorStatus.RETRY

    def test_empty_thought_partial_name_retries(self, checker):
        """Thought with only speaker name but no content"""
        response = "Thought: (Yana:\nOutput: 「おはよう」"
        result = checker.check(response)
        assert result.passed is False
        assert result.status == DirectorStatus.RETRY

    def test_empty_thought_unclosed_parenthesis_retries(self, checker):
        """Thought with unclosed parenthesis and no content"""
        response = "Thought: (やな:\nOutput: 「おはよう」"
        result = checker.check(response)
        assert result.passed is False
        assert result.status == DirectorStatus.RETRY


class TestThoughtCheckerValid:
    """Test valid Thought detection"""

    @pytest.fixture
    def checker(self):
        return ThoughtChecker()

    def test_valid_thought_passes(self, checker):
        """Valid Thought with content passes"""
        response = "Thought: (Yana: あゆも起きてるかな？)\nOutput: 「おはよう！」"
        result = checker.check(response)
        assert result.passed is True
        assert result.status == DirectorStatus.PASS

    def test_valid_thought_japanese_passes(self, checker):
        """Valid Thought with Japanese speaker name passes"""
        response = "Thought: (やな: 朝から張り切ってるな)\nOutput: 「おはよう！」"
        result = checker.check(response)
        assert result.passed is True
        assert result.status == DirectorStatus.PASS

    def test_valid_thought_multiline_passes(self, checker):
        """Valid multiline Thought passes"""
        response = "Thought: (姉様の無邪気さに呆れる。でも嬉しい。)\nOutput: 「おはようございます」"
        result = checker.check(response)
        assert result.passed is True
        assert result.status == DirectorStatus.PASS

    def test_valid_thought_without_parenthesis_passes(self, checker):
        """Valid Thought without parenthesis passes"""
        response = "Thought: あゆも起きてるかな\nOutput: 「おはよう」"
        result = checker.check(response)
        assert result.passed is True
        assert result.status == DirectorStatus.PASS


class TestThoughtCheckerMissing:
    """Test missing Thought detection"""

    @pytest.fixture
    def checker(self):
        return ThoughtChecker()

    def test_missing_thought_retries(self, checker):
        """Response without Thought triggers RETRY"""
        response = "Output: 「おはよう！」"
        result = checker.check(response)
        assert result.passed is False
        assert result.status == DirectorStatus.RETRY
        assert "Thought" in result.reason

    def test_output_only_retries(self, checker):
        """Output-only response triggers RETRY"""
        response = "(笑顔で) 「おはよう！」"
        result = checker.check(response)
        assert result.passed is False
        assert result.status == DirectorStatus.RETRY

    def test_dialogue_only_retries(self, checker):
        """Dialogue-only response without Thought/Output markers"""
        response = "「おはよう！」"
        result = checker.check(response)
        assert result.passed is False
        assert result.status == DirectorStatus.RETRY


class TestThoughtCheckerTruncated:
    """Test truncated Thought detection"""

    @pytest.fixture
    def checker(self):
        return ThoughtChecker()

    def test_truncated_thought_no_closing_retries(self, checker):
        """Thought that cuts off mid-sentence triggers RETRY"""
        response = "Thought: (やな: あゆも起きて"
        result = checker.check(response)
        assert result.passed is False
        assert result.status == DirectorStatus.RETRY
        assert "truncated" in result.reason.lower() or "incomplete" in result.reason.lower()

    def test_thought_without_output_retries(self, checker):
        """Thought without following Output triggers RETRY"""
        response = "Thought: (やな: あゆも起きてるかな？)"
        result = checker.check(response)
        assert result.passed is False
        assert result.status == DirectorStatus.RETRY


class TestThoughtCheckerMinLength:
    """Test minimum Thought content length"""

    @pytest.fixture
    def checker(self):
        return ThoughtChecker(min_thought_length=5)

    def test_short_thought_warns(self, checker):
        """Very short Thought triggers WARN"""
        # "…" alone is too short (1 char), use slightly longer content
        response = "Thought: (ふむ)\nOutput: 「おはよう」"
        result = checker.check(response)
        # Short but valid (3 chars < min_length=5) should WARN, not RETRY
        assert result.status == DirectorStatus.WARN

    def test_ellipsis_only_thought_retries(self, checker):
        """Thought with only ellipsis is considered empty"""
        response = "Thought: (…)\nOutput: 「おはよう」"
        result = checker.check(response)
        # "…" alone is too short (1 char), treated as empty
        assert result.status == DirectorStatus.RETRY

    def test_adequate_thought_passes(self, checker):
        """Adequate length Thought passes"""
        response = "Thought: (姉様の笑顔を見て安心する)\nOutput: 「おはよう」"
        result = checker.check(response)
        assert result.passed is True


class TestThoughtCheckerRealExamples:
    """Test with real examples from experiment data"""

    @pytest.fixture
    def checker(self):
        return ThoughtChecker()

    def test_real_empty_thought_1(self, checker):
        """Real example: Thought: (\nOutput:"""
        response = 'Thought: (\nOutput: (目をキラキラさせて) 「プロジェクトね！　進捗確認…つまんないなぁ～(笑)　あゆ、何かサプライズでも考えてる？」'
        result = checker.check(response)
        assert result.passed is False
        assert result.status == DirectorStatus.RETRY

    def test_real_empty_thought_2(self, checker):
        """Real example: Thought: (\nOutput:"""
        response = 'Thought: (\nOutput: (少しだけからかうように) 「ふーん、そう。ちゃんと朝ごはん食べた？　あゆ、また忘れそうだよ～」'
        result = checker.check(response)
        assert result.passed is False
        assert result.status == DirectorStatus.RETRY

    def test_real_valid_thought(self, checker):
        """Real example: Valid Thought"""
        response = 'Thought: (Yana: あゆもちゃんと起きてるかな？朝から張り切ってるかも。)\nOutput: (にこやかに) 「おはよう！あゆ、ちゃんと朝ごはん食べた？」'
        result = checker.check(response)
        assert result.passed is True
        assert result.status == DirectorStatus.PASS

    def test_real_valid_thought_ayu(self, checker):
        """Real example: Valid Thought from Ayu"""
        response = 'Thought: (姉様の明るさが眩しい…でも、朝ごはんの確認はありがたい。)\nOutput: (少し照れながら) 「おはようございます、姉様。朝ごはん、ちゃんと食べましたよ。」'
        result = checker.check(response)
        assert result.passed is True
        assert result.status == DirectorStatus.PASS
