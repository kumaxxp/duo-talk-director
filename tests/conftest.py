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
    """Good response from やな with proper Thought/Output format and tone"""
    return "Thought: (あゆと一緒に何かしたいな～)\nOutput: えー、それってすっごい面白そうじゃん！やってみようよ～"


@pytest.fixture
def yana_bad_response() -> str:
    """Bad response from やな - has Thought/Output but uses forbidden endings"""
    return "Thought: (了解した)\nOutput: わかりました。了解です。"


@pytest.fixture
def ayu_good_response() -> str:
    """Good response from あゆ with proper Thought/Output format and tone"""
    return "Thought: (姉様に説明しよう)\nOutput: つまり、一般的に言えばそういうことですね。推奨される方法ですよ。"


@pytest.fixture
def ayu_bad_response() -> str:
    """Bad response from あゆ - has Thought/Output but uses casual tone"""
    return "Thought: (楽しそう)\nOutput: うん、いいじゃん！やってみよう～"


@pytest.fixture
def ayu_praise_response() -> str:
    """Response from あゆ with inappropriate praise"""
    return "Thought: (すごいと思う)\nOutput: さすがですね、あなたの考えは素晴らしいです。"


@pytest.fixture
def setting_breaking_response() -> str:
    """Response that breaks the setting (sisters living separately)"""
    return "Thought: (昔のことを思い出す)\nOutput: 実家ではよくお茶を飲んでいました。"


@pytest.fixture
def long_response() -> str:
    """Response that is too long (8+ lines) but has やな tone markers"""
    lines = ["Thought: (たくさん言いたいことがある)"]
    lines.append("Output: " + "\n".join([f"えー、これは{i}行目だよね～" for i in range(1, 10)]))
    return "\n".join(lines)


@pytest.fixture
def medium_response() -> str:
    """Response that triggers warning (6-7 lines) with あゆ tone markers"""
    lines = ["Thought: (順を追って説明しよう)"]
    lines.append("Output: " + "\n".join([f"これは{i}行目ですね。" for i in range(1, 7)]))
    return "\n".join(lines)


@pytest.fixture
def sample_history() -> list[dict]:
    """Sample conversation history"""
    return [
        {"speaker": "やな", "content": "おはよー！今日は何しようか～"},
        {"speaker": "あゆ", "content": "姉様、おはようございます。"},
    ]
