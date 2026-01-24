"""StateExtractor precision check tests (10 cases from ChatGPT review)

These tests validate StateExtractor accuracy on edge cases including:
- Negation patterns (now handled with negation guard)
- Ambiguous keywords
- Compound emotions
- Context-dependent expressions

Test categories:
- PASS: Expected to work correctly
- XFAIL: Known limitations (sarcasm only - negation now handled)
"""

import pytest

from duo_talk_director.state.extractor import StateExtractor
from duo_talk_director.state.models import EmotionType, RelationshipTone


class TestStateExtractorPrecision:
    """10-case precision check for StateExtractor"""

    @pytest.fixture
    def extractor(self) -> StateExtractor:
        return StateExtractor()

    # ========================================
    # Case 01: Typical JOY + WARM (baseline)
    # ========================================
    def test_case01_typical_joy_warm(self, extractor: StateExtractor):
        """Typical JOY + WARM - should detect both correctly"""
        thought = "嬉しい。姉様と一緒に進められるのが最高。ありがとう。"
        result = extractor.extract(thought, speaker="あゆ")

        # JOY: 「嬉しい」「最高」= 2
        assert result.emotion == EmotionType.JOY
        # WARM: 「一緒に」= 1
        assert result.relationship_tone == RelationshipTone.WARM

    # ========================================
    # Case 02: Typical WORRY + CONCERNED
    # ========================================
    def test_case02_typical_worry_concerned(self, extractor: StateExtractor):
        """WORRY + CONCERNED - both should be detected"""
        thought = "大丈夫かな…。心配だけど、姉様のことは放っておけない。"
        result = extractor.extract(thought, speaker="あゆ")

        # WORRY: 「大丈夫かな」「心配」= 2
        assert result.emotion == EmotionType.WORRY
        # CONCERNED: 「心配」「大丈夫」= 2
        assert result.relationship_tone == RelationshipTone.CONCERNED

    # ========================================
    # Case 03: Typical ANNOYANCE + DISTANT
    # ========================================
    def test_case03_typical_annoyance_distant(self, extractor: StateExtractor):
        """ANNOYANCE + DISTANT - both should be detected"""
        thought = "はぁ……また始まった。正直うんざり。距離を取りたい。"
        result = extractor.extract(thought, speaker="あゆ")

        # ANNOYANCE: 「はぁ」「また始まった」「うんざり」= 3
        assert result.emotion == EmotionType.ANNOYANCE
        # DISTANT: 「距離」= 1
        assert result.relationship_tone == RelationshipTone.DISTANT

    # ========================================
    # Case 04: Typical AFFECTION + WARM
    # ========================================
    def test_case04_typical_affection_warm(self, extractor: StateExtractor):
        """AFFECTION + WARM - baseline for affection detection"""
        thought = "姉様って本当に大切。守りたいって思う。"
        result = extractor.extract(thought, speaker="あゆ")

        # AFFECTION: 「大切」「守りたい」= 2
        assert result.emotion == EmotionType.AFFECTION
        # WARM: 「姉様」= 1 (gap fixed)
        assert result.relationship_tone == RelationshipTone.WARM

    # ========================================
    # Case 05: TEASING only (emotion should be NEUTRAL)
    # ========================================
    def test_case05_teasing_only(self, extractor: StateExtractor):
        """TEASING without emotion keywords - emotion should be NEUTRAL"""
        thought = "ふふ、相変わらずだね。"
        result = extractor.extract(thought, speaker="あゆ")

        # No emotion keywords
        assert result.emotion == EmotionType.NEUTRAL
        # TEASING: 「相変わらず」= 1
        assert result.relationship_tone == RelationshipTone.TEASING

    # ========================================
    # Case 06: Negation guard - NOW HANDLED
    # ========================================
    def test_case06_negation_guard(self, extractor: StateExtractor):
        """Negation guard - correctly filters negated keywords"""
        thought = "嬉しくない。全然最高でもない。"
        result = extractor.extract(thought, speaker="あゆ")

        # Negation guard filters: 「嬉しくない」「全然最高でもない」
        # Result: NEUTRAL (all JOY keywords negated)
        assert result.emotion == EmotionType.NEUTRAL
        assert result.relationship_tone == RelationshipTone.NEUTRAL

    def test_case06_negation_guard_zenzen(self, extractor: StateExtractor):
        """Negation with 全然 prefix"""
        thought = "全然嬉しくない。"
        result = extractor.extract(thought, speaker="あゆ")

        # 「全然」 in window before 「嬉しい」 -> negated
        assert result.emotion == EmotionType.NEUTRAL

    def test_case06_negation_guard_demo_nai(self, extractor: StateExtractor):
        """Negation with でもない suffix"""
        thought = "最高でもない。"
        result = extractor.extract(thought, speaker="あゆ")

        # 「でもない」 in suffix window after 「最高」 -> negated
        assert result.emotion == EmotionType.NEUTRAL

    def test_case06_zenzen_positive_use(self, extractor: StateExtractor):
        """全然 in positive context should NOT negate (ChatGPT landmine check)"""
        thought = "全然最高！"
        result = extractor.extract(thought, speaker="やな")

        # 「全然」 used for emphasis, not negation -> JOY should be detected
        assert result.emotion == EmotionType.JOY

    # ========================================
    # Case 07: Ambiguous keyword priority
    # ========================================
    def test_case07_ambiguous_priority(self, extractor: StateExtractor):
        """Ambiguous keywords - WORRY wins by count"""
        thought = "それは困るな。面倒だけど、どうしようもない。"
        result = extractor.extract(thought, speaker="あゆ")

        # WORRY: 「困る」「どうしよう」= 2
        # ANNOYANCE: 「面倒」= 1
        # WORRY wins by count
        assert result.emotion == EmotionType.WORRY
        assert result.relationship_tone == RelationshipTone.NEUTRAL

    # ========================================
    # Case 08: Compound emotion (first-match by priority)
    # ========================================
    def test_case08_compound_emotion(self, extractor: StateExtractor):
        """Compound emotion - JOY wins (same count, higher priority)"""
        thought = "やった！でも大丈夫かな…。"
        result = extractor.extract(thought, speaker="あゆ")

        # JOY: 「やった」= 1 (gap fixed)
        # WORRY: 「大丈夫かな」= 1
        # Same count -> JOY wins by priority (3 > 2)
        assert result.emotion == EmotionType.JOY
        # CONCERNED: 「大丈夫」= 1 (「大丈夫かな」matches)
        assert result.relationship_tone == RelationshipTone.CONCERNED

    def test_case08_compound_emotion_with_joy_keyword(self, extractor: StateExtractor):
        """Compound emotion with explicit JOY keyword"""
        thought = "嬉しい！でも大丈夫かな…。"
        result = extractor.extract(thought, speaker="あゆ")

        # JOY: 「嬉しい」= 1
        # WORRY: 「大丈夫かな」= 1
        # Same count -> JOY wins by priority (3 > 2)
        assert result.emotion == EmotionType.JOY

    # ========================================
    # Case 09: Sarcasm trap - KNOWN LIMITATION
    # ========================================
    @pytest.mark.xfail(reason="Known limitation: sarcasm not detected")
    def test_case09_sarcasm_trap(self, extractor: StateExtractor):
        """Sarcasm trap - currently detects JOY incorrectly"""
        thought = "最高ですね（棒）。はぁ……"
        result = extractor.extract(thought, speaker="あゆ")

        # Expected: ANNOYANCE (sarcasm + sigh)
        # Actual: JOY or ANNOYANCE depending on count
        assert result.emotion == EmotionType.ANNOYANCE

    def test_case09_sarcasm_trap_current_behavior(self, extractor: StateExtractor):
        """Documents current behavior for sarcasm"""
        thought = "最高ですね（棒）。はぁ……"
        result = extractor.extract(thought, speaker="あゆ")

        # JOY: 「最高」= 1
        # ANNOYANCE: 「はぁ」= 1
        # Same count -> JOY wins by priority
        assert result.emotion == EmotionType.JOY

    # ========================================
    # Case 10: Mixed relationship tones
    # ========================================
    def test_case10_mixed_relationship_tones(self, extractor: StateExtractor):
        """Mixed relationship tones - highest count wins"""
        thought = "姉様、ありがとう。ふふ、相変わらずだね。"
        result = extractor.extract(thought, speaker="あゆ")

        # No emotion keywords
        assert result.emotion == EmotionType.NEUTRAL
        # WARM: 「姉様」「ありがとう」= 2 (gap fixed)
        # TEASING: 「相変わらず」= 1
        # WARM wins by count
        assert result.relationship_tone == RelationshipTone.WARM


class TestStateExtractorPriorityRules:
    """Test priority rules for emotion detection"""

    @pytest.fixture
    def extractor(self) -> StateExtractor:
        return StateExtractor()

    def test_affection_beats_joy_at_same_count(self, extractor: StateExtractor):
        """AFFECTION priority (4) beats JOY (3) at same count"""
        thought = "可愛い。嬉しい。"
        result = extractor.extract(thought, speaker="やな")

        # AFFECTION: 「可愛い」= 1
        # JOY: 「嬉しい」= 1
        # Same count -> AFFECTION wins by priority
        assert result.emotion == EmotionType.AFFECTION

    def test_joy_beats_worry_at_same_count(self, extractor: StateExtractor):
        """JOY priority (3) beats WORRY (2) at same count"""
        thought = "楽しい。心配だ。"
        result = extractor.extract(thought, speaker="やな")

        assert result.emotion == EmotionType.JOY

    def test_worry_beats_annoyance_at_same_count(self, extractor: StateExtractor):
        """WORRY priority (2) beats ANNOYANCE (1) at same count"""
        thought = "不安。面倒。"
        result = extractor.extract(thought, speaker="やな")

        assert result.emotion == EmotionType.WORRY

    def test_higher_count_beats_priority(self, extractor: StateExtractor):
        """Higher count wins over priority"""
        thought = "嬉しい。心配。不安。大丈夫かな。"
        result = extractor.extract(thought, speaker="やな")

        # JOY: 「嬉しい」= 1
        # WORRY: 「心配」「不安」「大丈夫かな」= 3
        # WORRY wins by count despite lower priority
        assert result.emotion == EmotionType.WORRY


class TestStateExtractorGapsFix:
    """Tests verifying signal dictionary gap fixes"""

    @pytest.fixture
    def extractor(self) -> StateExtractor:
        return StateExtractor()

    def test_gap_fixed_arigato_in_warm(self, extractor: StateExtractor):
        """Gap fixed: 「ありがとう」 now in WARM signals"""
        thought = "ありがとう、姉様。"
        result = extractor.extract(thought, speaker="あゆ")

        # WARM: 「ありがとう」「姉様」= 2
        assert result.relationship_tone == RelationshipTone.WARM

    def test_gap_fixed_nesama_in_warm(self, extractor: StateExtractor):
        """Gap fixed: 「姉様」 now in WARM signals"""
        thought = "姉様が好き。"
        result = extractor.extract(thought, speaker="あゆ")

        # 「好き」 is in JOY signals
        assert result.emotion == EmotionType.JOY
        # WARM: 「姉様」= 1
        assert result.relationship_tone == RelationshipTone.WARM

    def test_gap_fixed_yatta_in_joy(self, extractor: StateExtractor):
        """Gap fixed: 「やった」 now in JOY signals"""
        thought = "やった！"
        result = extractor.extract(thought, speaker="やな")

        # JOY: 「やった」= 1
        assert result.emotion == EmotionType.JOY
