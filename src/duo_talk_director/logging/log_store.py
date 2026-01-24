"""Log storage for duo-talk-director (Phase 2.3)

Provides centralized log storage with JSON Lines format.
"""

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

# Singleton instance
_log_store: "LogStore | None" = None


def get_log_store(base_dir: str | Path | None = None) -> "LogStore":
    """Get or create the global LogStore instance

    Args:
        base_dir: Base directory for logs (default: ./logs)

    Returns:
        LogStore singleton instance
    """
    global _log_store
    if _log_store is None:
        _log_store = LogStore(base_dir)
    return _log_store


def reset_log_store() -> None:
    """Reset the global LogStore instance (for testing)"""
    global _log_store
    _log_store = None


class LogStore:
    """Centralized log storage for director events

    Stores logs in JSON Lines format for easy analysis.
    """

    def __init__(self, base_dir: str | Path | None = None):
        """Initialize LogStore

        Args:
            base_dir: Base directory for logs (default: ./logs)
        """
        if base_dir is None:
            base_dir = Path("./logs")
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        # Session ID for grouping logs
        self._session_id: str | None = None

    def set_session_id(self, session_id: str) -> None:
        """Set current session ID for log grouping"""
        self._session_id = session_id

    def get_session_id(self) -> str:
        """Get current session ID, creating one if not set"""
        if self._session_id is None:
            self._session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        return self._session_id

    def clear_session(self) -> None:
        """Clear current session ID"""
        self._session_id = None

    def _get_log_path(self, log_type: str) -> Path:
        """Get log file path for a specific log type

        Args:
            log_type: Type of log (e.g., "sanitizer", "thought")

        Returns:
            Path to the log file
        """
        session_id = self.get_session_id()
        return self.base_dir / f"{log_type}_{session_id}.jsonl"

    def write(self, log_type: str, entry: Any) -> None:
        """Write a log entry

        Args:
            log_type: Type of log (e.g., "sanitizer", "thought")
            entry: Log entry (dataclass or dict)
        """
        path = self._get_log_path(log_type)

        # Convert dataclass to dict if needed
        if hasattr(entry, "__dataclass_fields__"):
            data = asdict(entry)
        else:
            data = dict(entry)

        # Add metadata
        data["_log_type"] = log_type
        data["_logged_at"] = datetime.now().isoformat()

        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")

    def read_all(self, log_type: str) -> list[dict]:
        """Read all entries for a log type in current session

        Args:
            log_type: Type of log

        Returns:
            List of log entries
        """
        path = self._get_log_path(log_type)
        if not path.exists():
            return []

        entries = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    entries.append(json.loads(line))
        return entries

    def get_stats(self, log_type: str) -> dict:
        """Get statistics for a log type

        Args:
            log_type: Type of log

        Returns:
            Statistics dictionary
        """
        entries = self.read_all(log_type)
        return {
            "count": len(entries),
            "session_id": self.get_session_id(),
            "log_file": str(self._get_log_path(log_type)),
        }
