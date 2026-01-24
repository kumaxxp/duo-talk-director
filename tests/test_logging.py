"""Tests for logging module (Phase 2.3)"""

import json
import tempfile
from pathlib import Path

import pytest

from duo_talk_director.logging import (
    LogStore,
    SanitizerLogger,
    SanitizerLogEntry,
    ThoughtLogger,
    ThoughtLogEntry,
    get_log_store,
    reset_log_store,
)
from duo_talk_director.checks.action_sanitizer import SanitizerResult


class TestLogStore:
    """Tests for LogStore"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Reset global log store before each test"""
        reset_log_store()
        yield
        reset_log_store()

    def test_creates_log_directory(self, tmp_path):
        """LogStore creates directory if not exists"""
        log_dir = tmp_path / "logs"
        store = LogStore(log_dir)
        assert log_dir.exists()

    def test_write_and_read(self, tmp_path):
        """Can write and read log entries"""
        store = LogStore(tmp_path)
        store.set_session_id("test_session")

        entry = {"turn": 1, "speaker": "やな", "message": "テスト"}
        store.write("test", entry)

        entries = store.read_all("test")
        assert len(entries) == 1
        assert entries[0]["turn"] == 1
        assert entries[0]["speaker"] == "やな"

    def test_session_id_auto_generated(self, tmp_path):
        """Session ID is auto-generated if not set"""
        store = LogStore(tmp_path)
        session_id = store.get_session_id()
        assert session_id is not None
        assert len(session_id) > 0

    def test_writes_to_jsonl_format(self, tmp_path):
        """Writes entries in JSON Lines format"""
        store = LogStore(tmp_path)
        store.set_session_id("test_session")

        store.write("test", {"a": 1})
        store.write("test", {"b": 2})

        log_file = tmp_path / "test_test_session.jsonl"
        assert log_file.exists()

        with open(log_file) as f:
            lines = f.readlines()
            assert len(lines) == 2

    def test_get_stats(self, tmp_path):
        """Returns correct statistics"""
        store = LogStore(tmp_path)
        store.set_session_id("test_session")

        store.write("test", {"a": 1})
        store.write("test", {"b": 2})
        store.write("test", {"c": 3})

        stats = store.get_stats("test")
        assert stats["count"] == 3
        assert stats["session_id"] == "test_session"

    def test_clear_session(self, tmp_path):
        """Can clear session ID"""
        store = LogStore(tmp_path)
        store.set_session_id("old_session")
        store.clear_session()

        # Should generate new session ID
        new_id = store.get_session_id()
        assert new_id != "old_session"


class TestSanitizerLogger:
    """Tests for SanitizerLogger"""

    @pytest.fixture
    def logger(self, tmp_path):
        """Create logger with temp log store"""
        reset_log_store()
        store = LogStore(tmp_path)
        store.set_session_id("test_session")
        return SanitizerLogger(store)

    def test_log_sanitization_event(self, logger):
        """Logs sanitization event correctly"""
        result = SanitizerResult(
            sanitized_text="（小さく頷く）「おはよう」",
            action_replaced=True,
            blocked_props=["コーヒー"],
            original_action="コーヒーを飲みながら",
        )

        entry = logger.log(
            turn_number=1,
            speaker="やな",
            result=result,
            scene_items=["ソファ", "テーブル"],
        )

        assert entry.turn_number == 1
        assert entry.speaker == "やな"
        assert entry.action_replaced is True
        assert entry.blocked_props == ["コーヒー"]
        assert entry.original_action == "コーヒーを飲みながら"

    def test_log_action_removed(self, logger):
        """Logs action removal correctly"""
        result = SanitizerResult(
            sanitized_text="「おはよう」",
            action_removed=True,
            blocked_props=["スマホ"],
            original_action="スマホを見ながら",
        )

        entry = logger.log(turn_number=2, speaker="あゆ", result=result)

        assert entry.action_removed is True
        assert entry.action_replaced is False

    def test_get_blocked_props_stats(self, logger):
        """Returns correct blocked props statistics"""
        # Log multiple events with blocked props
        for prop in ["コーヒー", "コーヒー", "スマホ", "コーヒー"]:
            result = SanitizerResult(
                sanitized_text="「テスト」",
                action_replaced=True,
                blocked_props=[prop],
                original_action=f"{prop}を使う",
            )
            logger.log(turn_number=1, speaker="やな", result=result)

        stats = logger.get_blocked_props_stats()
        assert stats["コーヒー"] == 3
        assert stats["スマホ"] == 1

    def test_get_character_stats(self, logger):
        """Returns correct character statistics"""
        # Log events for やな
        for _ in range(3):
            result = SanitizerResult(
                sanitized_text="「テスト」",
                action_replaced=True,
                blocked_props=["コーヒー"],
            )
            logger.log(turn_number=1, speaker="やな", result=result)

        # Log events for あゆ
        for _ in range(2):
            result = SanitizerResult(
                sanitized_text="「テスト」",
                action_removed=True,
                blocked_props=["スマホ"],
            )
            logger.log(turn_number=1, speaker="あゆ", result=result)

        stats = logger.get_character_stats()
        assert stats["やな"]["total"] == 3
        assert stats["やな"]["replaced"] == 3
        assert stats["あゆ"]["total"] == 2
        assert stats["あゆ"]["removed"] == 2

    def test_get_summary(self, logger):
        """Returns correct summary"""
        # Log various events
        logger.log(
            turn_number=1,
            speaker="やな",
            result=SanitizerResult(sanitized_text="「テスト」", action_replaced=True, blocked_props=["コーヒー"]),
        )
        logger.log(
            turn_number=2,
            speaker="あゆ",
            result=SanitizerResult(sanitized_text="「テスト」", action_removed=True, blocked_props=["スマホ"]),
        )
        logger.log(
            turn_number=3,
            speaker="やな",
            result=SanitizerResult(sanitized_text="（微笑んで）「テスト」"),
        )

        summary = logger.get_summary()
        assert summary["total_events"] == 3
        assert summary["action_replaced"] == 1
        assert summary["action_removed"] == 1
        assert summary["unchanged"] == 1


class TestThoughtLogger:
    """Tests for ThoughtLogger"""

    @pytest.fixture
    def logger(self, tmp_path):
        """Create logger with temp log store"""
        reset_log_store()
        store = LogStore(tmp_path)
        store.set_session_id("test_session")
        return ThoughtLogger(store)

    def test_log_thought(self, logger):
        """Logs thought correctly"""
        entry = logger.log(
            turn_number=1,
            speaker="やな",
            thought="今日は楽しい一日になりそう！",
        )

        assert entry.turn_number == 1
        assert entry.speaker == "やな"
        assert entry.thought == "今日は楽しい一日になりそう！"
        assert entry.thought_length == len("今日は楽しい一日になりそう！")
        assert entry.thought_missing is False

    def test_log_empty_thought_as_missing(self, logger):
        """Empty thoughts are marked as missing"""
        entry = logger.log(
            turn_number=1,
            speaker="やな",
            thought="",
        )

        assert entry.thought_missing is True

    def test_log_default_thought_as_missing(self, logger):
        """Default thoughts are marked as missing"""
        entry = logger.log(
            turn_number=1,
            speaker="やな",
            thought="(特に懸念はない)",
        )

        assert entry.thought_missing is True

    def test_get_missing_rate(self, logger):
        """Returns correct missing rate"""
        # Log normal thoughts
        for _ in range(8):
            logger.log(turn_number=1, speaker="やな", thought="何か考えている")

        # Log missing thoughts
        for _ in range(2):
            logger.log(turn_number=1, speaker="やな", thought="")

        rate = logger.get_missing_rate()
        assert rate == 0.2  # 2 / 10

    def test_get_emotion_distribution(self, logger):
        """Returns correct emotion distribution"""

        # Create mock state objects
        class MockState:
            def __init__(self, emotion):
                self.emotion = emotion
                self.emotion_intensity = 0.7
                self.relationship_tone = "NEUTRAL"
                self.confidence = 0.8

        class MockEmotion:
            def __init__(self, value):
                self.value = value

        # Log thoughts with different emotions
        for emotion in ["JOY", "JOY", "JOY", "WORRY", "NEUTRAL"]:
            state = MockState(MockEmotion(emotion))
            logger.log(
                turn_number=1,
                speaker="やな",
                thought="テスト",
                state=state,
            )

        distribution = logger.get_emotion_distribution()
        assert distribution["JOY"] == 3
        assert distribution["WORRY"] == 1
        assert distribution["NEUTRAL"] == 1

    def test_get_character_stats(self, logger):
        """Returns correct character statistics"""
        # Log thoughts for やな
        for _ in range(5):
            logger.log(turn_number=1, speaker="やな", thought="テスト思考やな")

        # Log thoughts for あゆ (including missing)
        for _ in range(3):
            logger.log(turn_number=1, speaker="あゆ", thought="テスト思考あゆ")
        logger.log(turn_number=1, speaker="あゆ", thought="")

        stats = logger.get_character_stats()
        assert stats["やな"]["total"] == 5
        assert stats["やな"]["missing"] == 0
        assert stats["あゆ"]["total"] == 4
        assert stats["あゆ"]["missing"] == 1

    def test_get_summary(self, logger):
        """Returns correct summary"""
        # Log various thoughts
        # "普通の思考" = 5 chars, * 3 = 15 chars
        for _ in range(8):
            logger.log(turn_number=1, speaker="やな", thought="普通の思考" * 3)
        for _ in range(2):
            logger.log(turn_number=1, speaker="あゆ", thought="")

        summary = logger.get_summary()
        assert summary["total_thoughts"] == 10
        assert summary["missing_count"] == 2
        assert summary["missing_rate"] == 0.2
        # Average length: 8 * 15 / 10 = 12.0
        assert summary["avg_length"] == pytest.approx(12.0)


class TestSanitizerLogEntry:
    """Tests for SanitizerLogEntry dataclass"""

    def test_creates_entry(self):
        """Can create log entry"""
        entry = SanitizerLogEntry(
            timestamp="2026-01-24T12:00:00",
            turn_number=1,
            speaker="やな",
            blocked_props=["コーヒー"],
            action_removed=False,
            action_replaced=True,
            original_action="コーヒーを飲む",
        )

        assert entry.turn_number == 1
        assert entry.speaker == "やな"

    def test_default_values(self):
        """Has correct default values"""
        entry = SanitizerLogEntry(
            timestamp="2026-01-24T12:00:00",
            turn_number=1,
            speaker="やな",
        )

        assert entry.blocked_props == []
        assert entry.action_removed is False
        assert entry.action_replaced is False


class TestThoughtLogEntry:
    """Tests for ThoughtLogEntry dataclass"""

    def test_creates_entry(self):
        """Can create log entry"""
        entry = ThoughtLogEntry(
            timestamp="2026-01-24T12:00:00",
            turn_number=1,
            speaker="やな",
            thought="テスト思考",
        )

        assert entry.turn_number == 1
        assert entry.thought == "テスト思考"

    def test_calculates_thought_length(self):
        """Automatically calculates thought length"""
        entry = ThoughtLogEntry(
            timestamp="2026-01-24T12:00:00",
            turn_number=1,
            speaker="やな",
            thought="12345",
        )

        assert entry.thought_length == 5

    def test_default_values(self):
        """Has correct default values"""
        entry = ThoughtLogEntry(
            timestamp="2026-01-24T12:00:00",
            turn_number=1,
            speaker="やな",
            thought="テスト",
        )

        assert entry.thought_missing is False
        assert entry.emotion == "NEUTRAL"
        assert entry.emotion_intensity == 0.0
