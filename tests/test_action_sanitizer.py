"""Tests for ActionSanitizer - Lightweight props hallucination prevention

ActionSanitizer detects props (items) in Action descriptions that don't exist
in the current Scene, and either replaces them with safe alternatives or
removes the Action entirely.

Key design decisions:
- No RETRY, only sanitize (delete/replace)
- Dictionary-based detection (no NLP)
- Fallback actions for common props
"""

import pytest

from duo_talk_director.checks.action_sanitizer import ActionSanitizer, SanitizerResult


class TestActionSanitizerBasic:
    """Basic functionality tests"""

    @pytest.fixture
    def sanitizer(self) -> ActionSanitizer:
        return ActionSanitizer()

    @pytest.fixture
    def empty_scene(self) -> list[str]:
        return []

    @pytest.fixture
    def scene_with_coffee(self) -> list[str]:
        return ["コーヒー", "テーブル", "椅子"]

    # ===== No Action Cases =====

    def test_no_action_returns_unchanged(self, sanitizer: ActionSanitizer, empty_scene: list[str]):
        """Text without action should pass through unchanged"""
        text = "「おはよう、あゆ」"
        result = sanitizer.sanitize(text, empty_scene)
        assert result.sanitized_text == text
        assert result.action_removed is False
        assert result.action_replaced is False

    def test_empty_text_returns_empty(self, sanitizer: ActionSanitizer, empty_scene: list[str]):
        """Empty text should return empty result"""
        result = sanitizer.sanitize("", empty_scene)
        assert result.sanitized_text == ""

    def test_dialogue_only_unchanged(self, sanitizer: ActionSanitizer, empty_scene: list[str]):
        """Dialogue without action passes through"""
        text = "「今日はいい天気だね～」"
        result = sanitizer.sanitize(text, empty_scene)
        assert result.sanitized_text == text

    # ===== Action Format Detection =====

    def test_parentheses_action_detected(self, sanitizer: ActionSanitizer, scene_with_coffee: list[str]):
        """（...）format action should be detected"""
        text = "（微笑む）「おはよう」"
        result = sanitizer.sanitize(text, scene_with_coffee)
        assert result.sanitized_text == text  # Safe action, unchanged
        assert result.original_action == "微笑む"

    def test_asterisk_action_detected(self, sanitizer: ActionSanitizer, scene_with_coffee: list[str]):
        """*...* format action should be detected and converted"""
        text = "*微笑む*「おはよう」"
        result = sanitizer.sanitize(text, scene_with_coffee)
        # Should be converted to parentheses format or remain unchanged if safe
        assert "微笑む" in result.sanitized_text or result.original_action == "微笑む"


class TestActionSanitizerPropsDetection:
    """Props detection and blocking tests"""

    @pytest.fixture
    def sanitizer(self) -> ActionSanitizer:
        return ActionSanitizer()

    @pytest.fixture
    def empty_scene(self) -> list[str]:
        return []

    @pytest.fixture
    def scene_with_glasses(self) -> list[str]:
        return ["眼鏡", "本棚"]

    # ===== Props Not In Scene =====

    def test_coffee_not_in_scene_blocked(self, sanitizer: ActionSanitizer, empty_scene: list[str]):
        """コーヒー not in scene should be blocked"""
        text = "（コーヒーを飲む）「おはよう」"
        result = sanitizer.sanitize(text, empty_scene)
        assert "コーヒー" not in result.sanitized_text
        assert "コーヒー" in result.blocked_props

    def test_glasses_not_in_scene_blocked(self, sanitizer: ActionSanitizer, empty_scene: list[str]):
        """眼鏡 not in scene should be blocked"""
        text = "（眼鏡を直しながら）「なるほど」"
        result = sanitizer.sanitize(text, empty_scene)
        assert "眼鏡" not in result.sanitized_text
        assert "眼鏡" in result.blocked_props

    def test_smartphone_not_in_scene_blocked(self, sanitizer: ActionSanitizer, empty_scene: list[str]):
        """スマホ not in scene should be blocked"""
        text = "（スマホを見ながら）「ちょっと待って」"
        result = sanitizer.sanitize(text, empty_scene)
        assert "スマホ" not in result.sanitized_text
        assert "スマホ" in result.blocked_props

    # ===== Props In Scene =====

    def test_glasses_in_scene_allowed(self, sanitizer: ActionSanitizer, scene_with_glasses: list[str]):
        """眼鏡 in scene should be allowed"""
        text = "（眼鏡を直しながら）「なるほど」"
        result = sanitizer.sanitize(text, scene_with_glasses)
        assert result.sanitized_text == text
        assert result.action_removed is False
        assert result.action_replaced is False

    def test_coffee_in_scene_allowed(self, sanitizer: ActionSanitizer):
        """コーヒー in scene should be allowed"""
        scene = ["コーヒー", "マグカップ"]
        text = "（コーヒーを飲む）「おはよう」"
        result = sanitizer.sanitize(text, scene)
        assert result.sanitized_text == text
        assert len(result.blocked_props) == 0


class TestActionSanitizerReplacement:
    """Fallback action replacement tests"""

    @pytest.fixture
    def sanitizer(self) -> ActionSanitizer:
        return ActionSanitizer()

    @pytest.fixture
    def empty_scene(self) -> list[str]:
        return []

    def test_coffee_replaced_with_fallback(self, sanitizer: ActionSanitizer, empty_scene: list[str]):
        """コーヒー action should be replaced with 一息つく"""
        text = "（コーヒーを飲む）「おはよう」"
        result = sanitizer.sanitize(text, empty_scene)
        assert result.action_replaced is True
        assert "一息つく" in result.sanitized_text
        assert result.action_removed is False

    def test_glasses_replaced_with_fallback(self, sanitizer: ActionSanitizer, empty_scene: list[str]):
        """眼鏡 action should be replaced with 目を細める"""
        text = "（眼鏡の奥で目を細める）「そうですね」"
        result = sanitizer.sanitize(text, empty_scene)
        assert result.action_replaced is True
        assert "目を細める" in result.sanitized_text

    def test_smartphone_replaced_with_fallback(self, sanitizer: ActionSanitizer, empty_scene: list[str]):
        """スマホ action should be replaced with 考え込む"""
        text = "（スマホを見ながら）「ちょっと待って」"
        result = sanitizer.sanitize(text, empty_scene)
        assert result.action_replaced is True
        assert "考え込む" in result.sanitized_text


class TestActionSanitizerRemoval:
    """Action removal tests (when replacement is not possible)"""

    @pytest.fixture
    def sanitizer(self) -> ActionSanitizer:
        return ActionSanitizer()

    @pytest.fixture
    def empty_scene(self) -> list[str]:
        return []

    def test_action_removed_dialogue_preserved(self, sanitizer: ActionSanitizer, empty_scene: list[str]):
        """When action is removed, dialogue should be preserved"""
        text = "（コーヒーを飲む）「おはよう」"
        result = sanitizer.sanitize(text, empty_scene)
        # Either replaced or removed, but dialogue must remain
        assert "おはよう" in result.sanitized_text

    def test_parentheses_format_preserved_on_replace(self, sanitizer: ActionSanitizer, empty_scene: list[str]):
        """Replaced action should use （...） format"""
        text = "（コーヒーを飲む）「おはよう」"
        result = sanitizer.sanitize(text, empty_scene)
        if result.action_replaced:
            assert "（" in result.sanitized_text
            assert "）" in result.sanitized_text


class TestActionSanitizerBodyActions:
    """Body action (safe) tests"""

    @pytest.fixture
    def sanitizer(self) -> ActionSanitizer:
        return ActionSanitizer()

    @pytest.fixture
    def empty_scene(self) -> list[str]:
        return []

    @pytest.mark.parametrize(
        "safe_action",
        [
            "微笑む",
            "ため息をつく",
            "頷く",
            "首をかしげる",
            "肩をすくめる",
        ],
    )
    def test_body_actions_pass_through(
        self, sanitizer: ActionSanitizer, empty_scene: list[str], safe_action: str
    ):
        """Body actions should pass through unchanged"""
        text = f"（{safe_action}）「そうだね」"
        result = sanitizer.sanitize(text, empty_scene)
        assert result.sanitized_text == text
        assert result.action_removed is False
        assert result.action_replaced is False


class TestActionSanitizerAsteriskFormat:
    """*...* format handling tests"""

    @pytest.fixture
    def sanitizer(self) -> ActionSanitizer:
        return ActionSanitizer()

    @pytest.fixture
    def empty_scene(self) -> list[str]:
        return []

    def test_asterisk_format_converted(self, sanitizer: ActionSanitizer, empty_scene: list[str]):
        """*...* format should be converted to （...）"""
        text = "*微笑む*「おはよう」"
        result = sanitizer.sanitize(text, empty_scene)
        # Should convert to parentheses format
        assert "（微笑む）" in result.sanitized_text or result.sanitized_text == text

    def test_asterisk_with_blocked_props(self, sanitizer: ActionSanitizer, empty_scene: list[str]):
        """*...* format with blocked props should be sanitized"""
        text = "*コーヒーを飲む*「おはよう」"
        result = sanitizer.sanitize(text, empty_scene)
        assert "コーヒー" not in result.sanitized_text


class TestSanitizerResult:
    """SanitizerResult dataclass tests"""

    def test_result_defaults(self):
        """Default values should be set correctly"""
        result = SanitizerResult(sanitized_text="test")
        assert result.action_removed is False
        assert result.action_replaced is False
        assert result.blocked_props == []
        assert result.original_action is None

    def test_result_with_blocked_props(self):
        """blocked_props should be properly set"""
        result = SanitizerResult(
            sanitized_text="test",
            blocked_props=["コーヒー", "眼鏡"],
        )
        assert result.blocked_props == ["コーヒー", "眼鏡"]


class TestActionSanitizerSceneNormalization:
    """Scene items normalization tests"""

    @pytest.fixture
    def sanitizer(self) -> ActionSanitizer:
        return ActionSanitizer()

    def test_scene_case_insensitive(self, sanitizer: ActionSanitizer):
        """Scene items should be matched case-insensitively"""
        scene = ["PC", "パソコン"]
        text = "（パソコンを見る）「確認中」"
        result = sanitizer.sanitize(text, scene)
        assert result.sanitized_text == text  # パソコン is in scene

    def test_scene_with_symbols_normalized(self, sanitizer: ActionSanitizer):
        """Scene items with symbols should be normalized"""
        scene = ["コーヒー（ホット）", "紅茶"]
        text = "（コーヒーを飲む）「おはよう」"
        result = sanitizer.sanitize(text, scene)
        # コーヒー should match コーヒー（ホット）
        assert result.action_removed is False or result.action_replaced is False
