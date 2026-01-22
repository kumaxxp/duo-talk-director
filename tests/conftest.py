"""Pytest fixtures for duo-talk-director tests"""

import pytest

from duo_talk_director.interfaces import DirectorStatus


@pytest.fixture
def yana_speaker() -> str:
    """やな (elder sister) speaker name"""
    return "やな"


@pytest.fixture
def ayu_speaker() -> str:
    """あゆ (younger sister) speaker name"""
    return "あゆ"


@pytest.fixture
def yana_good_response() -> str:
    """Good response from やな with proper tone markers"""
    return "えー、それってすっごい面白そうじゃん！やってみようよ～"


@pytest.fixture
def yana_bad_response() -> str:
    """Bad response from やな - missing all tone markers (score=0)"""
    return "わかりました。了解です。"


@pytest.fixture
def ayu_good_response() -> str:
    """Good response from あゆ with proper tone markers"""
    return "つまり、一般的に言えばそういうことですね。推奨される方法ですよ。"


@pytest.fixture
def ayu_bad_response() -> str:
    """Bad response from あゆ - missing polite markers"""
    return "うん、いいじゃん！やってみよう～"


@pytest.fixture
def ayu_praise_response() -> str:
    """Response from あゆ with inappropriate praise"""
    return "さすがですね、あなたの考えは素晴らしいです。"


@pytest.fixture
def setting_breaking_response() -> str:
    """Response that breaks the setting (sisters living separately)"""
    return "実家ではよくお茶を飲んでいました。"


@pytest.fixture
def long_response() -> str:
    """Response that is too long (8+ lines) but has やな tone markers"""
    lines = [f"えー、これは{i}行目だよね～" for i in range(1, 10)]
    return "\n".join(lines)


@pytest.fixture
def medium_response() -> str:
    """Response that triggers warning (6-7 lines) with あゆ tone markers"""
    lines = [f"これは{i}行目ですね。" for i in range(1, 7)]
    return "\n".join(lines)


@pytest.fixture
def sample_history() -> list[dict]:
    """Sample conversation history"""
    return [
        {"speaker": "やな", "content": "おはよー！今日は何しようか～"},
        {"speaker": "あゆ", "content": "姉様、おはようございます。"},
    ]
