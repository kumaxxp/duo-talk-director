"""Signal dictionaries for state extraction

Contains keyword patterns for detecting emotions and relationship tones
from Thought text.
"""

from .models import EmotionType, RelationshipTone


# Emotion signal dictionaries
# Priority order: AFFECTION > JOY > WORRY > ANNOYANCE > NEUTRAL
EMOTION_SIGNALS: dict[EmotionType, list[str]] = {
    EmotionType.JOY: [
        "嬉しい",
        "楽しい",
        "ワクワク",
        "最高",
        "素敵",
        "よかった",
        "面白い",
        "幸せ",
        "いいな",
        "好き",
        "笑顔",
        "やった",  # Gap fix: common joy expression
    ],
    EmotionType.WORRY: [
        "心配",
        "不安",
        "大丈夫かな",
        "困る",
        "どうしよう",
        "気になる",
        "怖い",
        "不安定",
    ],
    EmotionType.ANNOYANCE: [
        "また始まった",
        "いつも",
        "面倒",
        "うんざり",
        "やれやれ",
        "はぁ",
        "ため息",
        "仕方ない",
        "困った",
        "無神経",
    ],
    EmotionType.AFFECTION: [
        "可愛い",
        "大切",
        "守りたい",
        "愛おしい",
        "妹思い",
        "姉思い",
        "仲良し",
    ],
}

# Relationship signal dictionaries
RELATIONSHIP_SIGNALS: dict[RelationshipTone, list[str]] = {
    RelationshipTone.WARM: [
        "嬉しそう",
        "笑顔",
        "一緒に",
        "仲良し",
        "楽しそう",
        "元気そう",
        "ありがとう",  # Gap fix: gratitude = warm
        "姉様",  # Gap fix: respectful address = warm
    ],
    RelationshipTone.TEASING: [
        "からかう",
        "いじわる",
        "ツンツン",
        "素直じゃない",
        "相変わらず",
        "照れ",
    ],
    RelationshipTone.CONCERNED: [
        "心配",
        "大丈夫",
        "無理しないで",
        "体調",
        "気をつけて",
    ],
    RelationshipTone.DISTANT: [
        "距離",
        "冷たい",
        "無視",
        "そっけない",
        "避ける",
    ],
}

# Character reference patterns
CHARACTER_REFERENCES: dict[str, list[str]] = {
    "あゆ": ["あゆ", "妹"],
    "姉様": ["姉様", "姉", "やな"],
}

# Intensity modifiers
INTENSITY_BOOSTERS: list[str] = [
    "！",
    "!",
    "すごく",
    "とても",
    "本当に",
    "めっちゃ",
    "超",
]

INTENSITY_REDUCERS: list[str] = [
    "ちょっと",
    "少し",
    "まあ",
    "一応",
]


# Negation tokens for negation guard
# Prefix tokens: appear BEFORE the keyword
# Note: 「全然」「まったく」are excluded because they can be used
# for emphasis in positive contexts (e.g., 「全然最高！」)
# These cases are covered by suffix tokens (e.g., 「くない」)
NEGATION_PREFIX_TOKENS: list[str] = [
    # Empty for now - suffix tokens handle most cases
    # Future: Add context-aware prefix detection if needed
]

# Suffix tokens: appear AFTER the keyword (e.g., 嬉しくない)
NEGATION_SUFFIX_TOKENS: list[str] = [
    "くない",
    "じゃない",
    "でもない",
    "ではない",
]

# Window size for negation check (characters)
NEGATION_WINDOW: int = 6


def count_signal_matches(text: str, signals: list[str]) -> int:
    """Count signal matches with negation guard

    Args:
        text: Text to search in
        signals: List of signal keywords to match

    Returns:
        Count of valid (non-negated) matches
    """
    count = 0
    for signal in signals:
        if signal in text:
            if not _is_negated(text, signal):
                count += 1
    return count


def _is_negated(text: str, signal: str) -> bool:
    """Check if a signal match is negated

    Checks for:
    - Prefix tokens in window before the signal (全然, まったく)
    - Suffix tokens in window after the signal (くない, じゃない)

    Args:
        text: Full text
        signal: Signal keyword that was matched

    Returns:
        True if the signal is negated
    """
    # Find the position of the signal
    pos = text.find(signal)
    if pos < 0:
        return False

    # Check prefix window (before the signal)
    prefix_start = max(0, pos - NEGATION_WINDOW)
    prefix_window = text[prefix_start:pos]

    for token in NEGATION_PREFIX_TOKENS:
        if token in prefix_window:
            return True

    # Check suffix window (after the signal)
    suffix_start = pos + len(signal)
    suffix_end = min(len(text), suffix_start + NEGATION_WINDOW)
    suffix_window = text[suffix_start:suffix_end]

    for token in NEGATION_SUFFIX_TOKENS:
        if token in suffix_window:
            return True

    return False
