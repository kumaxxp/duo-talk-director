"""StateExtractor - Extract state from Thought text

Uses signal detection (dictionary matching) to extract emotional,
relational, and topic states from Thought text.

Key design decisions:
- No LLM for speed (signal detection only)
- Priority-based emotion selection when multiple detected
- Confidence based on signal count and intensity
"""

from typing import Optional

from .models import EmotionType, RelationshipTone, ExtractedState, StateDiff
from .signals import (
    EMOTION_SIGNALS,
    RELATIONSHIP_SIGNALS,
    CHARACTER_REFERENCES,
    INTENSITY_BOOSTERS,
    INTENSITY_REDUCERS,
)


class StateExtractor:
    """Extract state from Thought text using signal detection

    Detects emotions, relationship tones, and topics from Thought text
    by matching against predefined signal dictionaries.
    """

    # Emotion priority order (higher = stronger)
    EMOTION_PRIORITY = {
        EmotionType.AFFECTION: 4,
        EmotionType.JOY: 3,
        EmotionType.WORRY: 2,
        EmotionType.ANNOYANCE: 1,
        EmotionType.NEUTRAL: 0,
    }

    def extract(self, thought: str, speaker: str) -> ExtractedState:
        """Extract state from a single Thought

        Args:
            thought: Thought text to analyze
            speaker: Speaker name ("やな" or "あゆ")

        Returns:
            ExtractedState with detected emotion, relationship, and topics
        """
        if not thought or not thought.strip():
            return ExtractedState()

        # Detect emotion
        emotion, emotion_count = self._detect_emotion(thought)

        # Calculate intensity
        intensity = self._calculate_intensity(thought, emotion_count)

        # Detect emotion target
        target = self._detect_target(thought, speaker)

        # Detect relationship tone
        relationship = self._detect_relationship(thought)

        # Extract topic keywords (simplified)
        keywords = self._extract_keywords(thought)

        # Calculate topic interest based on emotion intensity
        topic_interest = self._calculate_topic_interest(intensity, emotion)

        # Calculate confidence
        confidence = self._calculate_confidence(emotion_count, emotion)

        return ExtractedState(
            emotion=emotion,
            emotion_intensity=intensity,
            emotion_target=target,
            relationship_tone=relationship,
            topic_keywords=keywords,
            topic_interest=topic_interest,
            confidence=confidence,
            extraction_method="signal",
        )

    def extract_diff(
        self,
        current: ExtractedState,
        previous: Optional[ExtractedState],
        turn_number: int,
        speaker: str,
    ) -> StateDiff:
        """Calculate state difference between turns

        Args:
            current: Current turn's extracted state
            previous: Previous turn's extracted state (or None for first turn)
            turn_number: Current turn number
            speaker: Current speaker name

        Returns:
            StateDiff describing changes from previous turn
        """
        diff = StateDiff(turn_number=turn_number, speaker=speaker)

        if previous is None:
            # First turn - no changes to report
            return diff

        # Check emotion change
        if current.emotion != previous.emotion:
            diff.emotion_changed = True
            diff.emotion_from = previous.emotion
            diff.emotion_to = current.emotion

        # Check relationship change
        if current.relationship_tone != previous.relationship_tone:
            diff.relationship_changed = True
            diff.relationship_from = previous.relationship_tone
            diff.relationship_to = current.relationship_tone

        # Detect new topics
        prev_keywords = set(previous.topic_keywords)
        curr_keywords = set(current.topic_keywords)
        diff.new_topics = list(curr_keywords - prev_keywords)

        return diff

    def _detect_emotion(self, thought: str) -> tuple[EmotionType, int]:
        """Detect primary emotion and signal count

        Returns:
            Tuple of (detected emotion, signal count)
        """
        emotion_scores: dict[EmotionType, int] = {}

        for emotion, signals in EMOTION_SIGNALS.items():
            count = sum(1 for signal in signals if signal in thought)
            if count > 0:
                emotion_scores[emotion] = count

        if not emotion_scores:
            return EmotionType.NEUTRAL, 0

        # If multiple emotions detected, use priority
        max_count = max(emotion_scores.values())
        candidates = [e for e, c in emotion_scores.items() if c == max_count]

        if len(candidates) == 1:
            return candidates[0], max_count

        # Multiple candidates with same count - use priority
        best = max(candidates, key=lambda e: self.EMOTION_PRIORITY[e])
        return best, max_count

    def _calculate_intensity(self, thought: str, signal_count: int) -> float:
        """Calculate emotion intensity based on signals and modifiers

        Returns:
            Intensity value between 0.0 and 1.0
        """
        # Base intensity from signal count
        base = min(0.5 + (signal_count * 0.1), 0.8)

        # Boost from intensity modifiers
        boost_count = sum(1 for b in INTENSITY_BOOSTERS if b in thought)
        reduce_count = sum(1 for r in INTENSITY_REDUCERS if r in thought)

        modifier = (boost_count * 0.1) - (reduce_count * 0.1)
        intensity = base + modifier

        # Clamp to valid range
        return max(0.0, min(1.0, intensity))

    def _detect_target(self, thought: str, speaker: str) -> Optional[str]:
        """Detect emotion target (character reference)

        Args:
            thought: Thought text
            speaker: Current speaker

        Returns:
            Target character name or None
        """
        # Check for other character references
        for target, patterns in CHARACTER_REFERENCES.items():
            for pattern in patterns:
                if pattern in thought:
                    # Don't return self-reference as target
                    if target == "姉様" and speaker == "あゆ":
                        return "姉様"
                    elif target == "あゆ" and speaker == "やな":
                        return "あゆ"
                    elif target != speaker:
                        return target

        return None

    def _detect_relationship(self, thought: str) -> RelationshipTone:
        """Detect relationship tone from thought

        Returns:
            Detected RelationshipTone
        """
        tone_scores: dict[RelationshipTone, int] = {}

        for tone, signals in RELATIONSHIP_SIGNALS.items():
            count = sum(1 for signal in signals if signal in thought)
            if count > 0:
                tone_scores[tone] = count

        if not tone_scores:
            return RelationshipTone.NEUTRAL

        # Return highest scoring tone
        return max(tone_scores, key=lambda t: tone_scores[t])

    def _extract_keywords(self, thought: str) -> list[str]:
        """Extract topic keywords from thought (simplified)

        For now, returns empty list. Full implementation would use
        morphological analysis or NLP.

        Returns:
            List of topic keywords
        """
        # Simplified: just return empty for now
        # Full implementation would extract nouns/topics
        return []

    def _calculate_topic_interest(
        self, intensity: float, emotion: EmotionType
    ) -> float:
        """Calculate topic interest based on emotion

        Returns:
            Topic interest value between 0.0 and 1.0
        """
        # High intensity positive emotions = high interest
        if emotion in [EmotionType.JOY, EmotionType.AFFECTION]:
            return min(0.5 + intensity * 0.5, 1.0)
        elif emotion == EmotionType.WORRY:
            return 0.5  # Neutral interest
        elif emotion == EmotionType.ANNOYANCE:
            return max(0.5 - intensity * 0.3, 0.2)  # Lower interest
        else:
            return 0.5  # Neutral

    def _calculate_confidence(
        self, signal_count: int, emotion: EmotionType
    ) -> float:
        """Calculate extraction confidence

        Returns:
            Confidence value between 0.0 and 1.0
        """
        if emotion == EmotionType.NEUTRAL and signal_count == 0:
            return 0.2  # Low confidence for neutral

        # More signals = higher confidence
        return min(0.3 + (signal_count * 0.2), 1.0)
