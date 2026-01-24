"""ActionSanitizer logging (Phase 2.3)

Logs sanitization events for analysis:
- Which props are frequently blocked
- Character-specific patterns
- Scene vs Action mismatches

Log schema per PHASE2_3_SPEC.md:
- timestamp: ISO format
- turn_number: Turn number
- speaker: Speaker name
- blocked_props: List of blocked props
- action_removed: Whether action was removed
- action_replaced: Whether action was replaced
- original_action: Original action text
"""

from dataclasses import dataclass, field
from datetime import datetime

from .log_store import get_log_store


@dataclass
class SanitizerLogEntry:
    """Log entry for ActionSanitizer events

    Attributes:
        timestamp: ISO format timestamp
        turn_number: Turn number
        speaker: Speaker name
        blocked_props: List of blocked props
        action_removed: Whether action was removed
        action_replaced: Whether action was replaced
        original_action: Original action text
        sanitized_action: Result after sanitization (if replaced)
        scene_items: Items present in scene (for debugging)
    """

    timestamp: str
    turn_number: int
    speaker: str
    blocked_props: list[str] = field(default_factory=list)
    action_removed: bool = False
    action_replaced: bool = False
    original_action: str | None = None
    sanitized_action: str | None = None
    scene_items: list[str] = field(default_factory=list)


class SanitizerLogger:
    """Logger for ActionSanitizer events

    Usage:
        logger = SanitizerLogger()
        logger.log(
            turn_number=1,
            speaker="やな",
            result=sanitizer_result,
            scene_items=scene_items,
        )
    """

    LOG_TYPE = "sanitizer"

    def __init__(self, log_store=None):
        """Initialize SanitizerLogger

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
        result: "SanitizerResult",
        scene_items: list[str] | None = None,
    ) -> SanitizerLogEntry:
        """Log a sanitization event

        Args:
            turn_number: Current turn number
            speaker: Speaker name
            result: SanitizerResult from ActionSanitizer
            scene_items: Items present in scene

        Returns:
            Created log entry
        """
        from ..checks.action_sanitizer import SanitizerResult

        entry = SanitizerLogEntry(
            timestamp=datetime.now().isoformat(),
            turn_number=turn_number,
            speaker=speaker,
            blocked_props=result.blocked_props,
            action_removed=result.action_removed,
            action_replaced=result.action_replaced,
            original_action=result.original_action,
            sanitized_action=self._extract_sanitized_action(result)
            if result.action_replaced
            else None,
            scene_items=scene_items or [],
        )

        self.log_store.write(self.LOG_TYPE, entry)
        return entry

    def _extract_sanitized_action(self, result: "SanitizerResult") -> str | None:
        """Extract sanitized action from result text"""
        import re

        if not result.sanitized_text:
            return None

        match = re.match(r"^（([^）]+)）", result.sanitized_text)
        if match:
            return match.group(1)
        return None

    def get_blocked_props_stats(self) -> dict[str, int]:
        """Get frequency count of blocked props

        Returns:
            Dictionary of prop -> count
        """
        entries = self.log_store.read_all(self.LOG_TYPE)
        stats: dict[str, int] = {}

        for entry in entries:
            for prop in entry.get("blocked_props", []):
                stats[prop] = stats.get(prop, 0) + 1

        return dict(sorted(stats.items(), key=lambda x: -x[1]))

    def get_character_stats(self) -> dict[str, dict]:
        """Get sanitization stats by character

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
                    "removed": 0,
                    "replaced": 0,
                    "blocked_props": {},
                }

            stats[speaker]["total"] += 1
            if entry.get("action_removed"):
                stats[speaker]["removed"] += 1
            if entry.get("action_replaced"):
                stats[speaker]["replaced"] += 1

            for prop in entry.get("blocked_props", []):
                prop_stats = stats[speaker]["blocked_props"]
                prop_stats[prop] = prop_stats.get(prop, 0) + 1

        return stats

    def get_summary(self) -> dict:
        """Get summary statistics

        Returns:
            Summary dictionary with key metrics
        """
        entries = self.log_store.read_all(self.LOG_TYPE)

        total = len(entries)
        removed = sum(1 for e in entries if e.get("action_removed"))
        replaced = sum(1 for e in entries if e.get("action_replaced"))
        unchanged = total - removed - replaced

        return {
            "total_events": total,
            "action_removed": removed,
            "action_replaced": replaced,
            "unchanged": unchanged,
            "removal_rate": removed / total if total > 0 else 0.0,
            "replacement_rate": replaced / total if total > 0 else 0.0,
            "top_blocked_props": list(self.get_blocked_props_stats().items())[:5],
        }
