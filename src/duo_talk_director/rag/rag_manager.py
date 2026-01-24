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

# Tag mapping from fact content patterns
TAG_MAPPING = {
    "使わない": "STYLE",  # Prohibited terms
    "呼ぶ": "REL",  # Addressing rules
    "話し方": "STYLE",  # Speech style
    "Scene": "SCENE",  # Scene props
    "存在しない": "SCENE",  # Blocked props
    "話題": "SCENE",  # Current topic
}


class RAGManager:
    """Unified RAG manager combining Persona and Session RAG

    Provides a single interface for retrieving facts from both
    character rules and session context.

    Phase 3.1 features:
    - Fact deduplication across session (avoid repeating same facts)
    - Tag-based limits (max 1 per tag by default)
    - Trigger-based priority (SCENE first when blocked_props detected)
    """

    # Tag-based limits (max facts per tag per search)
    DEFAULT_MAX_PER_TAG = {"SCENE": 1, "REL": 1, "STYLE": 1}

    def __init__(
        self,
        persona_config_path: Optional[Path] = None,
        dedupe_enabled: bool = True,
    ):
        """Initialize RAGManager

        Args:
            persona_config_path: Optional path to persona_rules.yaml
            dedupe_enabled: Enable session-wide fact deduplication
        """
        self.persona_rag = PersonaRAG(config_path=persona_config_path)
        self.session_rag = SessionRAG()
        self._enabled = True
        self._dedupe_enabled = dedupe_enabled
        # Fact cache: speaker -> set of fact content hashes
        self._seen_facts: dict[str, set[str]] = {}
        # Track triggers for current search
        self._current_triggers: list[str] = []

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
        force_all: bool = False,
    ) -> RAGResult:
        """Search for relevant facts from both RAG sources

        Args:
            speaker: Current speaker ("やな" or "あゆ")
            response_text: Response text to check for violations
            max_facts: Maximum number of facts to return (default 3)
            force_all: Bypass deduplication (for debugging)

        Returns:
            RAGResult with combined and prioritized facts
        """
        start_time = time.time()
        self._current_triggers = []

        result = RAGResult(
            sources_searched=["persona", "session"],
        )

        if not self._enabled:
            result.query_time_ms = (time.time() - start_time) * 1000
            return result

        # Initialize speaker's seen set if needed
        if speaker not in self._seen_facts:
            self._seen_facts[speaker] = set()

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

        # Detect triggers
        blocked_props = self.session_rag.get_blocked_props()
        has_blocked_prop_violation = any(
            prop in response_text for prop in blocked_props
        )
        if has_blocked_prop_violation:
            self._current_triggers.append("blocked_props")

        has_prohibited_term = any(
            "使わない" in f.content for f in persona_facts
        )
        if has_prohibited_term:
            self._current_triggers.append("prohibited_terms")

        # Combine and prioritize
        all_facts = persona_facts + session_facts
        all_facts.sort(key=lambda f: (f.priority, -f.confidence))

        # Select facts with deduplication and tag limits
        selected_facts = self._select_with_limits(
            facts=all_facts,
            speaker=speaker,
            max_count=max_facts,
            force_all=force_all,
        )

        for fact in selected_facts:
            result.add_fact(fact)

        result.query_time_ms = (time.time() - start_time) * 1000
        return result

    def _get_fact_tag(self, fact: FactCard) -> str:
        """Determine tag for a fact based on content"""
        for pattern, tag in TAG_MAPPING.items():
            if pattern in fact.content:
                return tag
        return "STYLE"  # default

    def _get_fact_id(self, fact: FactCard) -> str:
        """Generate a unique ID for a fact (for deduplication)"""
        # Use content hash for deduplication
        return f"{fact.source}:{hash(fact.content)}"

    def _select_with_limits(
        self,
        facts: list[FactCard],
        speaker: str,
        max_count: int,
        force_all: bool = False,
    ) -> list[FactCard]:
        """Select facts with tag limits and session deduplication

        Phase 3.1 logic:
        - Apply tag-based limits (max 1 per tag)
        - Skip facts already seen in this session (unless triggered)
        - Prioritize SCENE when blocked_props detected
        """
        selected: list[FactCard] = []
        tag_counts: dict[str, int] = {}
        seen_contents: set[str] = set()

        # Determine if we should force certain tags
        force_scene = "blocked_props" in self._current_triggers
        force_style = "prohibited_terms" in self._current_triggers

        for fact in facts:
            if len(selected) >= max_count:
                break

            tag = self._get_fact_tag(fact)
            fact_id = self._get_fact_id(fact)

            # Check tag limit
            tag_limit = self.DEFAULT_MAX_PER_TAG.get(tag, 1)
            if tag_counts.get(tag, 0) >= tag_limit:
                continue

            # Check content deduplication (within this search)
            if fact.content in seen_contents:
                continue

            # Check session deduplication (skip if seen before)
            if self._dedupe_enabled and not force_all:
                already_seen = fact_id in self._seen_facts.get(speaker, set())

                # Exception: show again if triggered
                should_force = False
                if tag == "SCENE" and force_scene:
                    should_force = True
                if tag == "STYLE" and force_style:
                    should_force = True

                if already_seen and not should_force:
                    continue

            # Select this fact
            selected.append(fact)
            seen_contents.add(fact.content)
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

            # Mark as seen for this session
            self._seen_facts[speaker].add(fact_id)

        return selected

    def get_current_triggers(self) -> list[str]:
        """Get triggers detected in the last search"""
        return self._current_triggers.copy()

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
        self._seen_facts.clear()
        self._current_triggers.clear()

    def to_log_entry(
        self,
        result: RAGResult,
        triggered_by: Optional[list[str]] = None,
    ) -> dict:
        """Convert RAGResult to log entry format for Phase 3.1 logging

        Args:
            result: RAGResult from search
            triggered_by: Optional list of triggers (overrides auto-detected)

        Returns:
            Dictionary suitable for RAGLogEntry
        """
        facts_log = []
        for i, fact in enumerate(result.facts):
            tag = self._get_fact_tag(fact)
            fact_id = self._get_fact_id(fact)

            facts_log.append({
                "tag": tag,
                "text": fact.content,
                "source": fact.source,
                "id": fact_id,
            })

        # Use auto-detected triggers if not provided
        triggers = triggered_by if triggered_by is not None else self._current_triggers

        return {
            "enabled": self._enabled,
            "triggered_by": triggers,
            "blocked_props": self.session_rag.get_blocked_props(),
            "facts": facts_log,
            "latency_ms": result.query_time_ms,
        }
