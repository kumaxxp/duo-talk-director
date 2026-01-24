"""Data models for state extraction

Defines the minimal state representation extracted from Thought text.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class EmotionType(Enum):
    """Detected emotion types"""

    JOY = "joy"  # 喜び
    WORRY = "worry"  # 心配
    ANNOYANCE = "annoyance"  # 苛立ち
    AFFECTION = "affection"  # 愛情
    NEUTRAL = "neutral"  # 中立


class RelationshipTone(Enum):
    """Detected relationship tones"""

    WARM = "warm"  # 温かい
    TEASING = "teasing"  # からかい
    CONCERNED = "concerned"  # 心配
    DISTANT = "distant"  # 距離感
    NEUTRAL = "neutral"  # 中立


@dataclass
class ExtractedState:
    """State extracted from a single Thought (minimal version)

    Attributes:
        emotion: Primary emotion detected
        emotion_intensity: Emotion strength (0.0-1.0)
        emotion_target: Target of emotion ("あゆ", "姉様", etc.)
        relationship_tone: Detected relationship tone
        topic_keywords: Extracted topic keywords
        topic_interest: Interest level in current topic (0.0-1.0)
        confidence: Extraction confidence score (0.0-1.0)
        extraction_method: Method used ("signal" or "llm")
    """

    # Emotion state
    emotion: EmotionType = EmotionType.NEUTRAL
    emotion_intensity: float = 0.5
    emotion_target: Optional[str] = None

    # Relationship state
    relationship_tone: RelationshipTone = RelationshipTone.NEUTRAL

    # Topic state
    topic_keywords: list[str] = field(default_factory=list)
    topic_interest: float = 0.5

    # Metadata
    confidence: float = 0.0
    extraction_method: str = "signal"


@dataclass
class StateDiff:
    """State difference between turns

    Tracks changes in emotional and relational state across turns.

    Attributes:
        turn_number: Current turn number
        speaker: Speaker name
        emotion_changed: Whether emotion changed from previous turn
        emotion_from: Previous emotion (if changed)
        emotion_to: Current emotion (if changed)
        relationship_changed: Whether relationship tone changed
        relationship_from: Previous relationship tone (if changed)
        relationship_to: Current relationship tone (if changed)
        new_topics: New topics introduced in this turn
    """

    turn_number: int
    speaker: str

    # Emotion changes
    emotion_changed: bool = False
    emotion_from: Optional[EmotionType] = None
    emotion_to: Optional[EmotionType] = None

    # Relationship changes
    relationship_changed: bool = False
    relationship_from: Optional[RelationshipTone] = None
    relationship_to: Optional[RelationshipTone] = None

    # Topic changes
    new_topics: list[str] = field(default_factory=list)
