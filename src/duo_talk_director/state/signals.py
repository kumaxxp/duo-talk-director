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
