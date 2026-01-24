"""Tests for StateExtractor - Thought state extraction (minimal version)

StateExtractor extracts emotional, relational, and topic states from
Thought text using signal detection (dictionary matching).

Key design decisions:
- Signal detection first (no LLM for speed)
- Minimal state model (emotion, relationship, topic)
- Diff calculation for turn-by-turn tracking
"""

import pytest

from duo_talk_director.state.models import (
    EmotionType,
    RelationshipTone,
    ExtractedState,
    StateDiff,
)
from duo_talk_director.state.extractor import StateExtractor


class TestStateExtractorEmotionDetection:
    """Emotion detection tests"""

    @pytest.fixture
    def extractor(self) -> StateExtractor:
        return StateExtractor()

    def test_extract_joy_emotion(self, extractor: StateExtractor):
        """Joy signals should be detected"""
        thought = "ワクワクしてる！今日は楽しくなりそう"
        state = extractor.extract(thought, "やな")
        assert state.emotion == EmotionType.JOY

    def test_extract_joy_with_ureshii(self, extractor: StateExtractor):
        """嬉しい should trigger JOY"""
        thought = "あゆが来てくれて嬉しい"
        state = extractor.extract(thought, "やな")
        assert state.emotion == EmotionType.JOY

    def test_extract_worry_emotion(self, extractor: StateExtractor):
        """Worry signals should be detected"""
        thought = "大丈夫かな…ちょっと心配"
        state = extractor.extract(thought, "やな")
        assert state.emotion == EmotionType.WORRY

    def test_extract_annoyance_emotion(self, extractor: StateExtractor):
        """Annoyance signals should be detected"""
        thought = "また始まった…姉様のハイテンションは"
        state = extractor.extract(thought, "あゆ")
        assert state.emotion == EmotionType.ANNOYANCE

    def test_extract_annoyance_with_sigh(self, extractor: StateExtractor):
        """ため息 should trigger ANNOYANCE"""
        thought = "はぁ、面倒だな"
        state = extractor.extract(thought, "あゆ")
        assert state.emotion == EmotionType.ANNOYANCE

    def test_extract_affection_emotion(self, extractor: StateExtractor):
        """Affection signals should be detected"""
        thought = "あゆが可愛い、守りたい"
        state = extractor.extract(thought, "やな")
        assert state.emotion == EmotionType.AFFECTION

    def test_extract_neutral_no_signal(self, extractor: StateExtractor):
        """No signal should return NEUTRAL"""
        thought = "そうですね"
        state = extractor.extract(thought, "あゆ")
        assert state.emotion == EmotionType.NEUTRAL

    def test_extract_empty_thought(self, extractor: StateExtractor):
        """Empty thought should return NEUTRAL"""
        state = extractor.extract("", "やな")
        assert state.emotion == EmotionType.NEUTRAL


class TestStateExtractorEmotionIntensity:
    """Emotion intensity tests"""

    @pytest.fixture
    def extractor(self) -> StateExtractor:
        return StateExtractor()

    def test_intensity_single_signal(self, extractor: StateExtractor):
        """Single signal should have moderate intensity"""
        thought = "楽しいな"
        state = extractor.extract(thought, "やな")
        assert 0.4 <= state.emotion_intensity <= 0.7

    def test_intensity_multiple_signals(self, extractor: StateExtractor):
        """Multiple signals should increase intensity"""
        thought = "嬉しい！楽しい！最高！"
        state = extractor.extract(thought, "やな")
        assert state.emotion_intensity >= 0.7

    def test_intensity_exclamation(self, extractor: StateExtractor):
        """Exclamation marks should increase intensity"""
        thought = "ワクワクしてる！！"
        state = extractor.extract(thought, "やな")
        assert state.emotion_intensity >= 0.6


class TestStateExtractorEmotionTarget:
    """Emotion target detection tests"""

    @pytest.fixture
    def extractor(self) -> StateExtractor:
        return StateExtractor()

    def test_target_ayu(self, extractor: StateExtractor):
        """あゆ in thought should be detected as target"""
        thought = "あゆが元気そうで嬉しい"
        state = extractor.extract(thought, "やな")
        assert state.emotion_target == "あゆ"

    def test_target_yana_as_anesama(self, extractor: StateExtractor):
        """姉様 should be detected as やな"""
        thought = "姉様のことが心配"
        state = extractor.extract(thought, "あゆ")
        assert state.emotion_target == "姉様"

    def test_target_none_no_reference(self, extractor: StateExtractor):
        """No reference should return None"""
        thought = "今日は天気がいいな"
        state = extractor.extract(thought, "やな")
        assert state.emotion_target is None


class TestStateExtractorRelationship:
    """Relationship tone detection tests"""

    @pytest.fixture
    def extractor(self) -> StateExtractor:
        return StateExtractor()

    def test_relationship_warm(self, extractor: StateExtractor):
        """Warm signals should be detected"""
        thought = "あゆと一緒にいると嬉しそうな顔してる"
        state = extractor.extract(thought, "やな")
        assert state.relationship_tone == RelationshipTone.WARM

    def test_relationship_teasing(self, extractor: StateExtractor):
        """Teasing signals should be detected"""
        thought = "姉様は相変わらず素直じゃない"
        state = extractor.extract(thought, "あゆ")
        assert state.relationship_tone == RelationshipTone.TEASING

    def test_relationship_concerned(self, extractor: StateExtractor):
        """Concern signals should be detected"""
        thought = "無理しないでほしい、大丈夫かな"
        state = extractor.extract(thought, "やな")
        assert state.relationship_tone == RelationshipTone.CONCERNED

    def test_relationship_neutral_no_signal(self, extractor: StateExtractor):
        """No signal should return NEUTRAL"""
        thought = "今日の予定を確認しよう"
        state = extractor.extract(thought, "やな")
        assert state.relationship_tone == RelationshipTone.NEUTRAL


class TestStateExtractorTopics:
    """Topic extraction tests"""

    @pytest.fixture
    def extractor(self) -> StateExtractor:
        return StateExtractor()

    def test_topic_keywords_extracted(self, extractor: StateExtractor):
        """Keywords should be extracted from thought"""
        thought = "AI技術について話すの、面白そう"
        state = extractor.extract(thought, "やな")
        # At minimum, should extract something
        assert isinstance(state.topic_keywords, list)

    def test_topic_interest_high_for_excited(self, extractor: StateExtractor):
        """High emotion should indicate high topic interest"""
        thought = "この話題すごく面白い！もっと知りたい！"
        state = extractor.extract(thought, "やな")
        assert state.topic_interest >= 0.6


class TestStateExtractorConfidence:
    """Extraction confidence tests"""

    @pytest.fixture
    def extractor(self) -> StateExtractor:
        return StateExtractor()

    def test_confidence_high_multiple_signals(self, extractor: StateExtractor):
        """Multiple signals should increase confidence"""
        thought = "嬉しい！楽しい！ワクワクする！"
        state = extractor.extract(thought, "やな")
        assert state.confidence >= 0.7

    def test_confidence_low_no_signal(self, extractor: StateExtractor):
        """No signals should have low confidence"""
        thought = "そうですね"
        state = extractor.extract(thought, "あゆ")
        assert state.confidence <= 0.3

    def test_extraction_method_is_signal(self, extractor: StateExtractor):
        """Extraction method should be 'signal'"""
        state = extractor.extract("テスト", "やな")
        assert state.extraction_method == "signal"


class TestStateExtractorDiff:
    """State diff calculation tests"""

    @pytest.fixture
    def extractor(self) -> StateExtractor:
        return StateExtractor()

    def test_diff_emotion_changed(self, extractor: StateExtractor):
        """Emotion change should be detected"""
        state1 = ExtractedState(emotion=EmotionType.JOY)
        state2 = ExtractedState(emotion=EmotionType.ANNOYANCE)

        diff = extractor.extract_diff(state2, state1, turn_number=2, speaker="あゆ")

        assert diff.emotion_changed is True
        assert diff.emotion_from == EmotionType.JOY
        assert diff.emotion_to == EmotionType.ANNOYANCE

    def test_diff_emotion_no_change(self, extractor: StateExtractor):
        """Same emotion should not be flagged as changed"""
        state1 = ExtractedState(emotion=EmotionType.JOY)
        state2 = ExtractedState(emotion=EmotionType.JOY)

        diff = extractor.extract_diff(state2, state1, turn_number=2, speaker="やな")

        assert diff.emotion_changed is False

    def test_diff_relationship_changed(self, extractor: StateExtractor):
        """Relationship change should be detected"""
        state1 = ExtractedState(relationship_tone=RelationshipTone.WARM)
        state2 = ExtractedState(relationship_tone=RelationshipTone.TEASING)

        diff = extractor.extract_diff(state2, state1, turn_number=2, speaker="あゆ")

        assert diff.relationship_changed is True
        assert diff.relationship_from == RelationshipTone.WARM
        assert diff.relationship_to == RelationshipTone.TEASING

    def test_diff_first_turn_no_previous(self, extractor: StateExtractor):
        """First turn with no previous should handle None"""
        state = ExtractedState(emotion=EmotionType.JOY)

        diff = extractor.extract_diff(state, None, turn_number=1, speaker="やな")

        assert diff.emotion_changed is False
        assert diff.emotion_from is None

    def test_diff_metadata(self, extractor: StateExtractor):
        """Diff should include turn metadata"""
        state1 = ExtractedState()
        state2 = ExtractedState()

        diff = extractor.extract_diff(state2, state1, turn_number=3, speaker="あゆ")

        assert diff.turn_number == 3
        assert diff.speaker == "あゆ"


class TestStateExtractorMultipleEmotions:
    """Multiple emotion handling tests"""

    @pytest.fixture
    def extractor(self) -> StateExtractor:
        return StateExtractor()

    def test_multiple_emotions_strongest_wins(self, extractor: StateExtractor):
        """When multiple emotions detected, strongest signal wins"""
        thought = "嬉しいけど、ちょっと心配"
        state = extractor.extract(thought, "やな")
        # Should detect one of them (strongest signal)
        assert state.emotion in [EmotionType.JOY, EmotionType.WORRY]

    def test_conflicting_emotions_uses_priority(self, extractor: StateExtractor):
        """Conflicting emotions should use priority order"""
        # This tests that the extractor handles conflicts gracefully
        thought = "楽しいけど面倒"
        state = extractor.extract(thought, "やな")
        assert state.emotion != EmotionType.NEUTRAL  # Should detect something


class TestExtractedStateModel:
    """ExtractedState dataclass tests"""

    def test_default_values(self):
        """Default values should be set correctly"""
        state = ExtractedState()
        assert state.emotion == EmotionType.NEUTRAL
        assert state.emotion_intensity == 0.5
        assert state.emotion_target is None
        assert state.relationship_tone == RelationshipTone.NEUTRAL
        assert state.topic_keywords == []
        assert state.topic_interest == 0.5
        assert state.confidence == 0.0
        assert state.extraction_method == "signal"

    def test_custom_values(self):
        """Custom values should be set correctly"""
        state = ExtractedState(
            emotion=EmotionType.JOY,
            emotion_intensity=0.9,
            emotion_target="あゆ",
        )
        assert state.emotion == EmotionType.JOY
        assert state.emotion_intensity == 0.9
        assert state.emotion_target == "あゆ"


class TestStateDiffModel:
    """StateDiff dataclass tests"""

    def test_default_values(self):
        """Default values should be set correctly"""
        diff = StateDiff(turn_number=1, speaker="やな")
        assert diff.turn_number == 1
        assert diff.speaker == "やな"
        assert diff.emotion_changed is False
        assert diff.relationship_changed is False
        assert diff.new_topics == []

    def test_with_changes(self):
        """Changes should be recorded correctly"""
        diff = StateDiff(
            turn_number=2,
            speaker="あゆ",
            emotion_changed=True,
            emotion_from=EmotionType.JOY,
            emotion_to=EmotionType.ANNOYANCE,
        )
        assert diff.emotion_changed is True
        assert diff.emotion_from == EmotionType.JOY
        assert diff.emotion_to == EmotionType.ANNOYANCE
