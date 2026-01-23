"""Evaluation prompts for LLM-based Director (Phase 2.2)

Based on duo-talk-evaluation/local_evaluator.py prompt design.
"""

SINGLE_TURN_PROMPT = """あなたは対話品質の評価専門家です。
以下の「{speaker}」の発言を5つの観点から評価してください。

## キャラクター設定
やな（姉）: 一人称「私」、直感的、行動派、砕けた口調
あゆ（妹）: 一人称「私」、分析的、慎重、慇懃無礼

## 会話履歴
{history}

## 評価対象
{speaker}: {response}

## 評価観点（各0.0-1.0でスコア）
1. character_consistency: キャラクター設定との一貫性（一人称、口調、性格）
2. topic_novelty: 話題の新規性（直前のターンとの比較で重複がないか）
3. relationship_quality: 姉妹らしい関係性表現（からかい、心配、協調）
4. naturalness: 応答の自然さ（テンポ、話題転換）
5. concreteness: 情報の具体性（具体例、数値、固有名詞）

## 出力形式（必ずJSONのみ）
{{
  "character_consistency": 0.0-1.0,
  "topic_novelty": 0.0-1.0,
  "relationship_quality": 0.0-1.0,
  "naturalness": 0.0-1.0,
  "concreteness": 0.0-1.0,
  "overall_score": 0.0-1.0,
  "issues": ["問題点があれば記載"],
  "strengths": ["良い点があれば記載"]
}}
"""


def format_history(history: list[dict]) -> str:
    """Format conversation history for prompt injection.

    Args:
        history: List of {speaker, content} dicts

    Returns:
        Formatted history string
    """
    if not history:
        return "（会話開始）"

    lines = []
    for turn in history:
        speaker = turn.get("speaker", "?")
        content = turn.get("content", "")
        lines.append(f"{speaker}: {content}")

    return "\n".join(lines)


def build_evaluation_prompt(
    speaker: str,
    response: str,
    topic: str,
    history: list[dict],
) -> str:
    """Build the complete evaluation prompt.

    Args:
        speaker: Character name ("やな" or "あゆ")
        response: Response text to evaluate
        topic: Conversation topic
        history: Previous conversation turns

    Returns:
        Complete prompt string
    """
    history_text = format_history(history)

    return SINGLE_TURN_PROMPT.format(
        speaker=speaker,
        response=response,
        history=history_text,
    )
