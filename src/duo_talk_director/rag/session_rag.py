"""SessionRAG - Scene and session memory retrieval

Retrieves facts about current scene state, available props,
and session context.
"""

from dataclasses import dataclass, field
from typing import Optional

from .fact_card import FactCard


@dataclass
class SceneContext:
    """Scene context for session RAG

    Attributes:
        location: Current location/setting
        time_of_day: Time of day (朝, 昼, 夕方, 夜)
        available_props: List of available props in scene
        mood: Current mood/atmosphere
        current_topic: Current conversation topic
    """

    location: str = ""
    time_of_day: str = ""
    available_props: list[str] = field(default_factory=list)
    mood: str = ""
    current_topic: str = ""


class SessionRAG:
    """RAG for session and scene context

    Generates FactCards about scene constraints, available props,
    and current conversation context.
    """

    def __init__(self):
        """Initialize SessionRAG"""
        self._scene_context: Optional[SceneContext] = None
        self._blocked_props: list[str] = []
        self._recent_topics: list[str] = []

    def set_scene_context(self, context: SceneContext) -> None:
        """Set current scene context"""
        self._scene_context = context

    def add_blocked_prop(self, prop: str) -> None:
        """Record a prop that was blocked by ActionSanitizer"""
        if prop not in self._blocked_props:
            self._blocked_props.append(prop)

    def add_topic(self, topic: str) -> None:
        """Add a topic to recent topics"""
        if topic and topic not in self._recent_topics:
            self._recent_topics.append(topic)
            # Keep only last 3 topics
            if len(self._recent_topics) > 3:
                self._recent_topics.pop(0)

    def search(
        self,
        speaker: str,
        response_text: str,
        max_facts: int = 3,
    ) -> list[FactCard]:
        """Search for relevant session facts

        Args:
            speaker: Current speaker
            response_text: Response text to check
            max_facts: Maximum number of facts to return

        Returns:
            List of FactCards (up to max_facts)
        """
        facts: list[FactCard] = []

        # Check for blocked props in response
        blocked_facts = self._check_blocked_props(response_text)
        facts.extend(blocked_facts)

        # Add scene props fact if available
        props_fact = self._get_scene_props_fact()
        if props_fact:
            facts.append(props_fact)

        # Add current topic fact
        topic_fact = self._get_current_topic_fact()
        if topic_fact:
            facts.append(topic_fact)

        # Sort by priority and limit
        facts.sort(key=lambda f: f.priority)
        return facts[:max_facts]

    def _check_blocked_props(self, response_text: str) -> list[FactCard]:
        """Check if response mentions previously blocked props"""
        facts = []

        for prop in self._blocked_props:
            if prop in response_text:
                fact_content = f"「{prop}」はSceneに存在しない。"
                if len(fact_content) <= 50:
                    facts.append(
                        FactCard(
                            content=fact_content,
                            source="session",
                            priority=1,  # High priority for violations
                            confidence=1.0,
                        )
                    )

        return facts

    def _get_scene_props_fact(self) -> Optional[FactCard]:
        """Get fact about available scene props"""
        if not self._scene_context:
            return None

        props = self._scene_context.available_props
        if not props:
            return None

        # Format props list
        if len(props) == 1:
            props_str = f"「{props[0]}」"
        elif len(props) <= 3:
            props_str = "、".join(f"「{p}」" for p in props)
        else:
            props_str = "、".join(f"「{p}」" for p in props[:3]) + "など"

        fact_content = f"Sceneにある物: {props_str}。"
        if len(fact_content) <= 50:
            return FactCard(
                content=fact_content,
                source="session",
                priority=2,
                confidence=1.0,
            )

        # If too long, simplify
        fact_content = f"Sceneには{len(props)}個の小物がある。"
        return FactCard(
            content=fact_content,
            source="session",
            priority=2,
            confidence=0.8,
        )

    def _get_current_topic_fact(self) -> Optional[FactCard]:
        """Get fact about current conversation topic"""
        if not self._recent_topics:
            return None

        current_topic = self._recent_topics[-1]
        fact_content = f"現在の話題: 「{current_topic}」。"

        if len(fact_content) <= 50:
            return FactCard(
                content=fact_content,
                source="session",
                priority=4,
                confidence=0.9,
            )

        return None

    def get_available_props(self) -> list[str]:
        """Get list of available props in current scene"""
        if self._scene_context:
            return self._scene_context.available_props.copy()
        return []

    def get_blocked_props(self) -> list[str]:
        """Get list of props that have been blocked"""
        return self._blocked_props.copy()

    def reset(self) -> None:
        """Reset session state for new session"""
        self._scene_context = None
        self._blocked_props.clear()
        self._recent_topics.clear()
