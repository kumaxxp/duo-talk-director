"""RAGManager - Unified RAG interface

Combines PersonaRAG and SessionRAG to provide a single interface
for fact retrieval. Handles priority-based fact selection and
ensures maximum fact count is respected.
"""

import time
from pathlib import Path
from typing import Optional

from .fact_card import FactCard, RAGResult, MAX_FACT_COUNT
from .persona_rag import PersonaRAG
from .session_rag import SessionRAG, SceneContext


class RAGManager:
    """Unified RAG manager combining Persona and Session RAG

    Provides a single interface for retrieving facts from both
    character rules and session context.
    """

    def __init__(self, persona_config_path: Optional[Path] = None):
        """Initialize RAGManager

        Args:
            persona_config_path: Optional path to persona_rules.yaml
        """
        self.persona_rag = PersonaRAG(config_path=persona_config_path)
        self.session_rag = SessionRAG()
        self._enabled = True

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable RAG"""
        self._enabled = enabled

    def set_scene_context(self, context: SceneContext) -> None:
        """Set scene context for session RAG"""
        self.session_rag.set_scene_context(context)

    def add_blocked_prop(self, prop: str) -> None:
        """Record a blocked prop for session RAG"""
        self.session_rag.add_blocked_prop(prop)

    def add_topic(self, topic: str) -> None:
        """Add current topic for session RAG"""
        self.session_rag.add_topic(topic)

    def search(
        self,
        speaker: str,
        response_text: str,
        max_facts: int = MAX_FACT_COUNT,
    ) -> RAGResult:
        """Search for relevant facts from both RAG sources

        Args:
            speaker: Current speaker ("やな" or "あゆ")
            response_text: Response text to check for violations
            max_facts: Maximum number of facts to return (default 3)

        Returns:
            RAGResult with combined and prioritized facts
        """
        start_time = time.time()

        result = RAGResult(
            sources_searched=["persona", "session"],
        )

        if not self._enabled:
            result.query_time_ms = (time.time() - start_time) * 1000
            return result

        # Get facts from both sources
        persona_facts = self.persona_rag.search(
            speaker=speaker,
            response_text=response_text,
            max_facts=max_facts,
        )

        session_facts = self.session_rag.search(
            speaker=speaker,
            response_text=response_text,
            max_facts=max_facts,
        )

        # Combine and prioritize
        all_facts = persona_facts + session_facts
        all_facts.sort(key=lambda f: (f.priority, -f.confidence))

        # Select top facts up to limit
        selected_facts = self._deduplicate_and_select(all_facts, max_facts)

        for fact in selected_facts:
            result.add_fact(fact)

        result.query_time_ms = (time.time() - start_time) * 1000
        return result

    def _deduplicate_and_select(
        self,
        facts: list[FactCard],
        max_count: int,
    ) -> list[FactCard]:
        """Remove duplicate facts and select top N

        Deduplication is based on content similarity.
        """
        seen_contents: set[str] = set()
        selected: list[FactCard] = []

        for fact in facts:
            # Simple deduplication based on exact content
            if fact.content in seen_contents:
                continue

            # Check for similar content (same topic)
            is_duplicate = False
            for seen in seen_contents:
                if self._is_similar(fact.content, seen):
                    is_duplicate = True
                    break

            if not is_duplicate:
                seen_contents.add(fact.content)
                selected.append(fact)

                if len(selected) >= max_count:
                    break

        return selected

    def _is_similar(self, content1: str, content2: str) -> bool:
        """Check if two fact contents are similar

        Simple implementation - checks for shared key terms.
        """
        # Extract key terms (simplified)
        terms1 = set(content1.replace("。", "").replace("「", "").replace("」", "").split())
        terms2 = set(content2.replace("。", "").replace("「", "").replace("」", "").split())

        # If more than half of shorter set is in common, consider similar
        if not terms1 or not terms2:
            return False

        common = terms1 & terms2
        shorter_len = min(len(terms1), len(terms2))

        return len(common) > shorter_len / 2

    def get_fact_string(
        self,
        speaker: str,
        response_text: str,
    ) -> str:
        """Get facts as formatted string for logging

        Convenience method that returns facts in FACT: format.
        """
        result = self.search(speaker, response_text)
        return result.to_fact_string()

    def reset_session(self) -> None:
        """Reset session state (call when starting new conversation)"""
        self.session_rag.reset()
