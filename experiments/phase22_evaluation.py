#!/usr/bin/env python3
"""Phase 2.2 LLMベースDirector評価テスト

DirectorLLM と DirectorHybrid の動作検証
"""

import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from duo_talk_director import (
    DirectorMinimal,
    DirectorLLM,
    DirectorHybrid,
    DirectorStatus,
    ThresholdConfig,
)


# LLMクライアント（duo-talk-coreから）
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "duo-talk-core" / "src"))
from duo_talk_core.llm_client import create_client


def create_test_responses():
    """テスト用レスポンスを作成"""
    return {
        "yana_good": {
            "speaker": "やな",
            "response": "Thought: (おお、面白そう！)\nOutput: *目を輝かせて* 「えー、それすっごいじゃん！あゆも一緒にやろうよ！」",
            "expected_status": DirectorStatus.PASS,
            "description": "やな: 良い応答（キャラクター一貫性OK）",
        },
        "yana_medium": {
            "speaker": "やな",
            "response": "Thought: (うーん)\nOutput: 「そうだね」",
            "expected_status": DirectorStatus.WARN,  # May be WARN due to lack of concreteness
            "description": "やな: 中程度の応答（短すぎる）",
        },
        "ayu_good": {
            "speaker": "あゆ",
            "response": "Thought: (また姉様の無謀な計画か…)\nOutput: *ため息をついて* 「姉様、その計画は論理的に破綻しています。...とはいえ、仕方ありませんね。」",
            "expected_status": DirectorStatus.PASS,
            "description": "あゆ: 良い応答（慇懃無礼スタイル）",
        },
        "ayu_bad_tone": {
            "speaker": "あゆ",
            "response": "Thought: (うわー楽しそう！)\nOutput: 「いいじゃんいいじゃん！やろうやろう！」",
            "expected_status": DirectorStatus.RETRY,
            "description": "あゆ: 悪い応答（口調違反：カジュアルすぎる）",
        },
        "yana_too_long": {
            "speaker": "やな",
            "response": "Thought: (考え中)\nOutput: 「セリフ1」\n「セリフ2」\n「セリフ3」\n「セリフ4」\n「セリフ5」\n「セリフ6」\n「セリフ7」\n「セリフ8」\n「セリフ9」\n「セリフ10」",
            "expected_status": DirectorStatus.RETRY,
            "description": "やな: 悪い応答（長すぎる：10行）",
        },
    }


def run_evaluation_test(director, test_cases, director_name):
    """評価テストを実行"""
    print(f"\n{'='*60}")
    print(f"Director: {director_name}")
    print(f"{'='*60}")

    results = []
    total_time = 0

    for name, case in test_cases.items():
        print(f"\n--- Test: {case['description']} ---")

        start_time = time.time()
        try:
            evaluation = director.evaluate_response(
                speaker=case["speaker"],
                response=case["response"],
                topic="テスト",
                history=[],
                turn_number=0,
            )
            elapsed = time.time() - start_time
            total_time += elapsed

            status_match = "✅" if evaluation.status == case["expected_status"] else "❌"
            print(f"Status: {evaluation.status.value} (expected: {case['expected_status'].value}) {status_match}")
            print(f"Time: {elapsed:.2f}s")
            print(f"Reason: {evaluation.reason[:100]}..." if len(evaluation.reason) > 100 else f"Reason: {evaluation.reason}")

            results.append({
                "name": name,
                "status": evaluation.status,
                "expected": case["expected_status"],
                "match": evaluation.status == case["expected_status"],
                "time": elapsed,
                "reason": evaluation.reason,
            })

        except Exception as e:
            print(f"Error: {e}")
            results.append({
                "name": name,
                "status": None,
                "expected": case["expected_status"],
                "match": False,
                "time": 0,
                "reason": str(e),
            })

    # Summary
    passed = sum(1 for r in results if r["match"])
    print(f"\n--- Summary for {director_name} ---")
    print(f"Passed: {passed}/{len(results)}")
    print(f"Total time: {total_time:.2f}s")
    print(f"Average time: {total_time/len(results):.2f}s per evaluation")

    return results


def main():
    print("=" * 60)
    print("Phase 2.2 LLMベースDirector評価テスト")
    print("=" * 60)

    # LLMクライアント作成
    print("\nInitializing LLM client (gemma3:12b)...")
    try:
        llm_client = create_client(backend="ollama", model="gemma3:12b")
        if not llm_client.is_available():
            print("Error: Ollama is not available")
            return
        print("LLM client ready.")
    except Exception as e:
        print(f"Error creating LLM client: {e}")
        return

    # テストケース
    test_cases = create_test_responses()

    # 各Director でテスト
    directors = [
        ("DirectorMinimal（静的チェックのみ）", DirectorMinimal()),
        ("DirectorLLM（LLM評価のみ）", DirectorLLM(llm_client)),
        ("DirectorHybrid（静的+LLM）", DirectorHybrid(llm_client)),
    ]

    all_results = {}
    for name, director in directors:
        results = run_evaluation_test(director, test_cases, name)
        all_results[name] = results

    # 比較レポート
    print("\n" + "=" * 60)
    print("比較レポート")
    print("=" * 60)

    print("\n| テストケース | DirectorMinimal | DirectorLLM | DirectorHybrid |")
    print("|-------------|-----------------|-------------|----------------|")

    for case_name in test_cases.keys():
        row = f"| {test_cases[case_name]['description'][:20]} |"
        for director_name in ["DirectorMinimal（静的チェックのみ）", "DirectorLLM（LLM評価のみ）", "DirectorHybrid（静的+LLM）"]:
            result = next((r for r in all_results[director_name] if r["name"] == case_name), None)
            if result:
                status = result["status"].value if result["status"] else "ERROR"
                match = "✅" if result["match"] else "❌"
                row += f" {status} {match} |"
            else:
                row += " - |"
        print(row)

    # 時間比較
    print("\n| Director | 平均時間 | 合計時間 |")
    print("|----------|----------|----------|")
    for director_name, results in all_results.items():
        total = sum(r["time"] for r in results)
        avg = total / len(results)
        print(f"| {director_name[:25]} | {avg:.2f}s | {total:.2f}s |")


if __name__ == "__main__":
    main()
