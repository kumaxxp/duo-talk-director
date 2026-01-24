"""Thought logging (Phase 2.3)

Logs thought generation events for analysis:
- Thought content and length
- Emotion and relationship tone (via StateExtractor)
- Missing/empty thoughts

Log schema per PHASE2_3_SPEC.md:
- timestamp: ISO format
- turn_number: Turn number
- speaker: Speaker name
- thought: Thought text
- emotion: Detected emotion
- emotion_intensity: Emotion intensity
- relationship_tone: Relationship tone
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .log_store import get_log_store


@dataclass
class ThoughtLogEntry:
    """Log entry for Thought generation events

    Attributes:
        timestamp: ISO format timestamp
        turn_number: Turn number
        speaker: Speaker name
        thought: Thought text
        thought_length: Length of thought text
        thought_missing: Whether thought was empty/default
        emotion: Detected emotion (from StateExtractor)
        emotion_intensity: Emotion intensity (0.0-1.0)
        relationship_tone: Relationship tone
        state_confidence: StateExtractor confidence
    """

    timestamp: str
    turn_number: int
    speaker: str
    thought: str
    thought_length: int = 0
    thought_missing: bool = False
    emotion: str = "NEUTRAL"
    emotion_intensity: float = 0.0
    relationship_tone: str = "NEUTRAL"
    state_confidence: float = 0.0

    def __post_init__(self):
        """Calculate derived fields"""
        if self.thought_length == 0:
            self.thought_length = len(self.thought)


class ThoughtLogger:
    """Logger for Thought generation events

    Usage:
        logger = ThoughtLogger()
        logger.log(
            turn_number=1,
            speaker="やな",
            thought="今日は楽しい一日になりそう！",
            state=extracted_state,  # Optional StateExtraction
        )
    """

    LOG_TYPE = "thought"
    DEFAULT_THOUGHTS = ["(特に懸念はない)", "(No specific thought)", ""]

    def __init__(self, log_store=None):
        """Initialize ThoughtLogger

        Args:
            log_store: LogStore instance (uses global if not provided)
        """
        self._log_store = log_store

    @property
    def log_store(self):
        """Get log store (lazy initialization)"""
        if self._log_store is None:
            self._log_store = get_log_store()
        return self._log_store

    def log(
        self,
        turn_number: int,
        speaker: str,
        thought: str,
        state: Optional["StateExtraction"] = None,
    ) -> ThoughtLogEntry:
        """Log a thought generation event

        Args:
            turn_number: Current turn number
            speaker: Speaker name
            thought: Generated thought text
            state: Optional StateExtraction from StateExtractor

        Returns:
            Created log entry
        """
        # Check if thought is missing/default
        thought_missing = self._is_thought_missing(thought)

        # Extract state information if available
        emotion = "NEUTRAL"
        emotion_intensity = 0.0
        relationship_tone = "NEUTRAL"
        state_confidence = 0.0

        if state is not None:
            emotion = state.emotion.value if hasattr(state.emotion, "value") else str(state.emotion)
            emotion_intensity = state.emotion_intensity
            relationship_tone = (
                state.relationship_tone.value
                if hasattr(state.relationship_tone, "value")
                else str(state.relationship_tone)
            )
            state_confidence = state.confidence

        entry = ThoughtLogEntry(
            timestamp=datetime.now().isoformat(),
            turn_number=turn_number,
            speaker=speaker,
            thought=thought,
            thought_length=len(thought),
            thought_missing=thought_missing,
            emotion=emotion,
            emotion_intensity=emotion_intensity,
            relationship_tone=relationship_tone,
            state_confidence=state_confidence,
        )

        self.log_store.write(self.LOG_TYPE, entry)
        return entry

    def _is_thought_missing(self, thought: str) -> bool:
        """Check if thought is missing or default

        Args:
            thought: Thought text

        Returns:
            True if thought is empty or default
        """
        if not thought or not thought.strip():
            return True

        # Check against known default thoughts
        cleaned = thought.strip()
        return cleaned in self.DEFAULT_THOUGHTS

    def get_missing_rate(self) -> float:
        """Get rate of missing thoughts

        Returns:
            Ratio of missing thoughts (0.0-1.0)
        """
        entries = self.log_store.read_all(self.LOG_TYPE)
        if not entries:
            return 0.0

        missing = sum(1 for e in entries if e.get("thought_missing", False))
        return missing / len(entries)

    def get_emotion_distribution(self) -> dict[str, int]:
        """Get distribution of detected emotions

        Returns:
            Dictionary of emotion -> count
        """
        entries = self.log_store.read_all(self.LOG_TYPE)
        distribution: dict[str, int] = {}

        for entry in entries:
            emotion = entry.get("emotion", "NEUTRAL")
            distribution[emotion] = distribution.get(emotion, 0) + 1

        return dict(sorted(distribution.items(), key=lambda x: -x[1]))

    def get_character_stats(self) -> dict[str, dict]:
        """Get thought stats by character

        Returns:
            Dictionary of character -> stats
        """
        entries = self.log_store.read_all(self.LOG_TYPE)
        stats: dict[str, dict] = {}

        for entry in entries:
            speaker = entry.get("speaker", "unknown")
            if speaker not in stats:
                stats[speaker] = {
                    "total": 0,
                    "missing": 0,
                    "total_length": 0,
                    "emotions": {},
                    "tones": {},
                }

            stats[speaker]["total"] += 1
            stats[speaker]["total_length"] += entry.get("thought_length", 0)

            if entry.get("thought_missing", False):
                stats[speaker]["missing"] += 1

            emotion = entry.get("emotion", "NEUTRAL")
            stats[speaker]["emotions"][emotion] = stats[speaker]["emotions"].get(emotion, 0) + 1

            tone = entry.get("relationship_tone", "NEUTRAL")
            stats[speaker]["tones"][tone] = stats[speaker]["tones"].get(tone, 0) + 1

        # Calculate averages
        for speaker in stats:
            total = stats[speaker]["total"]
            if total > 0:
                stats[speaker]["avg_length"] = stats[speaker]["total_length"] / total
                stats[speaker]["missing_rate"] = stats[speaker]["missing"] / total

        return stats

    def get_summary(self) -> dict:
        """Get summary statistics

        Returns:
            Summary dictionary with key metrics
        """
        entries = self.log_store.read_all(self.LOG_TYPE)

        total = len(entries)
        if total == 0:
            return {
                "total_thoughts": 0,
                "missing_count": 0,
                "missing_rate": 0.0,
                "avg_length": 0.0,
                "emotion_distribution": {},
            }

        missing = sum(1 for e in entries if e.get("thought_missing", False))
        total_length = sum(e.get("thought_length", 0) for e in entries)

        return {
            "total_thoughts": total,
            "missing_count": missing,
            "missing_rate": missing / total,
            "avg_length": total_length / total,
            "emotion_distribution": self.get_emotion_distribution(),
        }
