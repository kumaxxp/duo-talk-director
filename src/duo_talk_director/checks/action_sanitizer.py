"""ActionSanitizer - Lightweight props hallucination prevention (v1.0)

Detects props (items) in Action descriptions that don't exist in the current
Scene, and either replaces them with safe alternatives or removes the Action.

Key design decisions:
- No RETRY, only sanitize (delete/replace) to minimize generation flow impact
- Dictionary-based detection (no NLP/morphological analysis for speed)
- Fallback actions for common props to preserve narrative flow
- Logs blocked props for frequency analysis

Usage:
    sanitizer = ActionSanitizer()
    result = sanitizer.sanitize(output_text, scene_items)
    if result.action_replaced or result.action_removed:
        log_sanitization(result)
"""

import re
from dataclasses import dataclass, field


@dataclass
class SanitizerResult:
    """Result of action sanitization"""

    sanitized_text: str
    action_removed: bool = False
    action_replaced: bool = False
    blocked_props: list[str] = field(default_factory=list)
    original_action: str | None = None


class ActionSanitizer:
    """Action sanitizer for props hallucination prevention (lightweight version)

    Detects props in Action that don't exist in Scene and sanitizes them.
    Uses dictionary matching instead of NLP for speed.
    """

    # Action extraction patterns
    ACTION_PATTERN = re.compile(r"^（([^）]+)）")
    ACTION_ASTERISK_PATTERN = re.compile(r"^\*([^*]+)\*")

    # NG props dictionary (items that require Scene presence)
    PROPS_NG_DICT: set[str] = {
        # Drinks
        "コーヒー",
        "珈琲",
        "カップ",
        "グラス",
        "ワイン",
        "ビール",
        "お茶",
        "紅茶",
        "ジュース",
        "水",
        # Accessories
        "眼鏡",
        "メガネ",
        "めがね",
        "サングラス",
        "指輪",
        "ネックレス",
        "イヤリング",
        "ピアス",
        "腕時計",
        "時計",
        # Electronics
        "スマホ",
        "携帯",
        "パソコン",
        "PC",
        "タブレット",
        "リモコン",
        # Smoking
        "タバコ",
        "煙草",
        "たばこ",
        "ライター",
        # Other items
        "本",
        "雑誌",
        "新聞",
        "ペン",
        "ノート",
        "バッグ",
        "傘",
        "ハンカチ",
        "ティッシュ",
    }

    # Fallback actions for blocked props
    FALLBACK_ACTIONS: dict[str, str] = {
        # Drinks -> 一息つく
        "コーヒー": "一息つく",
        "珈琲": "一息つく",
        "お茶": "一息つく",
        "紅茶": "一息つく",
        "飲む": "一息つく",
        # Glasses -> 目を細める
        "眼鏡": "目を細める",
        "メガネ": "目を細める",
        "めがね": "目を細める",
        "サングラス": "目を細める",
        # Electronics -> 考え込む
        "スマホ": "考え込む",
        "携帯": "考え込む",
        "パソコン": "考え込む",
        "PC": "考え込む",
        "タブレット": "考え込む",
        # Reading -> 考え込む
        "本": "考え込む",
        "雑誌": "考え込む",
        "新聞": "考え込む",
        # Smoking -> 一息つく
        "タバコ": "一息つく",
        "煙草": "一息つく",
        "たばこ": "一息つく",
    }

    # Default fallback when no specific mapping exists
    DEFAULT_FALLBACK = "小さく頷く"

    def sanitize(
        self,
        output_text: str,
        scene_items: list[str],
    ) -> SanitizerResult:
        """Sanitize Action in output text

        Args:
            output_text: Phase2 output text (expected: （action）「dialogue」)
            scene_items: Items present in current Scene (inventory + nearby + temporary)

        Returns:
            SanitizerResult with sanitized text and metadata
        """
        if not output_text:
            return SanitizerResult(sanitized_text="")

        # Normalize scene items for matching
        normalized_scene = self._normalize_scene_items(scene_items)

        # Extract action from text
        action, action_type = self._extract_action(output_text)
        if not action:
            return SanitizerResult(sanitized_text=output_text)

        # Detect blocked props in action
        blocked = self._detect_blocked_props(action, normalized_scene)
        if not blocked:
            # No blocked props, return unchanged (but record original action)
            return SanitizerResult(
                sanitized_text=output_text,
                original_action=action,
            )

        # Blocked props detected -> replace or remove
        return self._handle_blocked_action(
            output_text=output_text,
            action=action,
            action_type=action_type,
            blocked_props=blocked,
        )

    def _extract_action(self, text: str) -> tuple[str | None, str | None]:
        """Extract Action from text

        Supports:
        - （...）format (standard)
        - *...* format (legacy, to be converted)

        Returns:
            Tuple of (action_content, action_type) or (None, None)
        """
        # Check （...）format first
        match = self.ACTION_PATTERN.match(text)
        if match:
            return match.group(1), "parentheses"

        # Check *...* format (legacy/forbidden)
        match = self.ACTION_ASTERISK_PATTERN.match(text)
        if match:
            return match.group(1), "asterisk"

        return None, None

    def _normalize_scene_items(self, items: list[str]) -> set[str]:
        """Normalize scene items for flexible matching

        - Adds both original and lowercase versions
        - Removes symbols for fuzzy matching
        """
        normalized = set()
        for item in items:
            # Add original
            normalized.add(item)
            # Add lowercase
            normalized.add(item.lower())
            # Add version without symbols
            clean = re.sub(r"[^\w\s]", "", item)
            normalized.add(clean)
            normalized.add(clean.lower())
        return normalized

    def _detect_blocked_props(
        self,
        action: str,
        normalized_scene: set[str],
    ) -> list[str]:
        """Detect props in action that are not in scene

        Returns:
            List of blocked prop names
        """
        blocked = []
        for prop in self.PROPS_NG_DICT:
            if prop in action:
                # Check if prop exists in scene
                if not self._prop_in_scene(prop, normalized_scene):
                    blocked.append(prop)
        return blocked

    def _prop_in_scene(self, prop: str, normalized_scene: set[str]) -> bool:
        """Check if a prop exists in scene (flexible matching)"""
        # Direct match
        if prop in normalized_scene:
            return True
        # Lowercase match
        if prop.lower() in normalized_scene:
            return True
        # Check if prop is substring of any scene item
        for scene_item in normalized_scene:
            if prop in scene_item or prop.lower() in scene_item.lower():
                return True
        return False

    def _handle_blocked_action(
        self,
        output_text: str,
        action: str,
        action_type: str,
        blocked_props: list[str],
    ) -> SanitizerResult:
        """Handle action with blocked props

        Strategy:
        1. Try to replace with fallback action
        2. If no fallback, remove action entirely
        """
        # Try to get fallback action
        fallback = self._get_fallback_action(blocked_props)

        if fallback:
            # Replace action with fallback
            sanitized = self._replace_action(output_text, action_type, fallback)
            return SanitizerResult(
                sanitized_text=sanitized,
                action_replaced=True,
                blocked_props=blocked_props,
                original_action=action,
            )
        else:
            # Remove action entirely
            sanitized = self._remove_action(output_text, action_type)
            return SanitizerResult(
                sanitized_text=sanitized,
                action_removed=True,
                blocked_props=blocked_props,
                original_action=action,
            )

    def _get_fallback_action(self, blocked_props: list[str]) -> str:
        """Get fallback action for blocked props

        Returns first matching fallback, or default if none found.
        """
        for prop in blocked_props:
            if prop in self.FALLBACK_ACTIONS:
                return self.FALLBACK_ACTIONS[prop]
        # Return default fallback
        return self.DEFAULT_FALLBACK

    def _replace_action(
        self,
        text: str,
        action_type: str,
        fallback: str,
    ) -> str:
        """Replace action with fallback action"""
        if action_type == "parentheses":
            return re.sub(
                r"^（[^）]+）",
                f"（{fallback}）",
                text,
            )
        else:  # asterisk -> convert to parentheses
            return re.sub(
                r"^\*[^*]+\*",
                f"（{fallback}）",
                text,
            )

    def _remove_action(self, text: str, action_type: str) -> str:
        """Remove action from text, preserving dialogue"""
        if action_type == "parentheses":
            return re.sub(r"^（[^）]+）\s*", "", text)
        else:  # asterisk
            return re.sub(r"^\*[^*]+\*\s*", "", text)
