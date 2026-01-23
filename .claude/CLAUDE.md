# duo-talk-director Project

## プロジェクト概要
AI姉妹対話の品質制御システム。
**Phase 2**: Directorによる対話品質モニタリングと制御。

## 現在の状態 (2026-01-24)
- **DirectorMinimal**: ✅ 静的チェックのみの実装完了
- **DirectorLLM**: ✅ LLM5軸評価実装完了
- **DirectorHybrid**: ✅ ハイブリッド方式実装完了
- **テスト**: ✅ 190テスト passed, カバレッジ94%
- **A/Bテスト**: ✅ 実行済み（duo-talk-evaluation）

## Git管理方針

**重要**: このプロジェクトは独自のgitリポジトリを持ちます。

### ローカルリポジトリ
- **場所**: `/home/owner/work/duo-talk-ecosystem/duo-talk-director/`
- **ブランチ**: `main`

### コミットルール
1. **コミットメッセージは日本語で記述**
2. Conventional Commits形式を使用:
   - `feat:` 新機能
   - `fix:` バグ修正
   - `refactor:` リファクタリング
   - `test:` テスト追加/修正
   - `docs:` ドキュメント
3. 作業終了時は必ずコミット

### GitHubリポジトリ設定手順
```bash
# 1. GitHubでリポジトリを作成（Web UIまたはgh CLI）
# リポジトリ名: duo-talk-director

# 2. リモート追加
cd /home/owner/work/duo-talk-ecosystem/duo-talk-director
git remote add origin git@github.com:<username>/duo-talk-director.git

# 3. プッシュ
git push -u origin main
```

## アーキテクチャ

```
duo-talk-director/
├── src/duo_talk_director/
│   ├── __init__.py           # パッケージエクスポート
│   ├── interfaces.py         # DirectorProtocol, LLMEvaluationScore
│   ├── director_minimal.py   # 静的チェックのみのDirector
│   ├── director_llm.py       # LLM5軸評価Director (Phase 2.2)
│   ├── director_hybrid.py    # ハイブリッドDirector (Phase 2.2)
│   ├── checks/               # 静的チェッカー
│   │   ├── tone_check.py     # 口調マーカー検証
│   │   ├── praise_check.py   # 褒め言葉検出
│   │   ├── setting_check.py  # 設定違反検出
│   │   └── format_check.py   # 応答長検証
│   ├── llm/                  # LLM評価モジュール (Phase 2.2)
│   │   ├── evaluator.py      # LLM評価ロジック
│   │   └── prompts.py        # 評価プロンプト
│   └── config/               # 設定 (Phase 2.2)
│       └── thresholds.py     # 閾値設定
├── tests/
│   ├── test_director_llm.py  # LLM Directorテスト
│   ├── test_director_hybrid.py # Hybrid Directorテスト
│   ├── test_llm_evaluator.py # LLM評価器テスト
│   ├── test_thresholds.py    # 閾値テスト
│   └── integration/
│       └── test_with_core.py # duo-talk-coreとの統合テスト
└── config/
    └── evaluation_thresholds.yaml # 閾値設定ファイル
```

## 主要コンポーネント

### DirectorMinimal
静的チェックのみを実行する軽量Director:
```python
from duo_talk_director import DirectorMinimal

director = DirectorMinimal()
evaluation = director.evaluate_response(
    speaker="やな",
    response="いいじゃんいいじゃん！あゆ、あとはよろしくね～",
    topic="今日のおやつ",
    history=[],
    turn_number=0,
)
print(evaluation.status)  # DirectorStatus.PASS
```

### DirectorLLM (Phase 2.2)
LLMを使用した5軸評価Director:
```python
from duo_talk_director import DirectorLLM

# LLMクライアントが必要
from duo_talk_core.llm_client import create_client
client = create_client(backend="ollama", model="gemma3:12b")

director = DirectorLLM(client)
evaluation = director.evaluate_response(
    speaker="やな",
    response="Thought: (楽しそう)\nOutput: えー、すっごいじゃん！",
    topic="テスト",
    history=[],
    turn_number=0,
)
print(evaluation.status)  # DirectorStatus.PASS
```

### DirectorHybrid (Phase 2.2 推奨)
静的チェック + LLM評価のハイブリッド方式:
```python
from duo_talk_director import DirectorHybrid

from duo_talk_core.llm_client import create_client
client = create_client(backend="ollama", model="gemma3:12b")

# 静的チェックでRETRYならLLMをスキップ（高速化）
director = DirectorHybrid(client, skip_llm_on_static_retry=True)
```

### 5軸評価メトリクス

| メトリクス | 説明 | 重み |
|-----------|------|------|
| character_consistency | キャラクター一貫性 | 0.25 |
| topic_novelty | 話題の新規性 | 0.20 |
| relationship_quality | 姉妹関係性 | 0.25 |
| naturalness | 対話の自然さ | 0.15 |
| concreteness | 情報の具体性 | 0.15 |

### 閾値設定

```python
from duo_talk_director import ThresholdConfig

config = ThresholdConfig(
    retry_overall=0.4,      # overall < 0.4 → RETRY
    retry_character=0.3,    # character_consistency < 0.3 → RETRY
    retry_relationship=0.3, # relationship_quality < 0.3 → RETRY
    warn_overall=0.6,       # overall < 0.6 → WARN
)
director = DirectorHybrid(client, threshold_config=config)
```

### 静的チェッカー

| チェッカー | 対象 | 検出内容 |
|-----------|------|----------|
| ToneChecker | やな/あゆ | 口調マーカーの有無（score < 2でRETRY） |
| PraiseChecker | あゆ | 「さすが」「流石」等の過剰な褒め言葉 |
| SettingChecker | 全員 | 「また遊びに来て」等の姉妹別居表現 |
| FormatChecker | 全員 | 8行以上の長すぎる応答 |

### DirectorStatus

| ステータス | 意味 | DialogueManagerの動作 |
|------------|------|----------------------|
| PASS | 品質OK | そのまま採用 |
| WARN | 軽微な問題 | 採用するが警告ログ |
| RETRY | 再生成必要 | max_retriesまで再生成 |
| MODIFY | 致命的問題 | セッション停止検討 |

## duo-talk-coreとの連携

```python
from duo_talk_core import create_dialogue_manager
from duo_talk_director import DirectorMinimal

director = DirectorMinimal()
manager = create_dialogue_manager(
    backend="ollama",
    model="gemma3:12b",
    director=director,
    max_retries=3,
)

# Directorが品質をチェックしながら対話生成
session = manager.run_session(topic="AI技術", turns=5)
```

## A/Bテスト結果 (2026-01-23)

| 条件 | 平均リトライ | 実行時間 |
|------|-------------|----------|
| Director無し | 0回 | 10.78秒 |
| Director有り | 10.67回 | 31.40秒 |

**結論**: キャラクター一貫性・関係性が向上するが、実行時間が約3倍に増加

## テスト実行

```bash
# conda環境で実行
conda activate duo-talk

# 全テスト
python -m pytest tests/ -v

# カバレッジ付き
python -m pytest tests/ -v --cov=src/duo_talk_director --cov-report=term-missing
```

## 依存関係

- **duo-talk-ecosystem内**:
  - duo-talk-core（Protocolのみ使用、実行時依存なし）

## Next Steps

### Phase 2.1 (完了)
- ✅ DirectorMinimal実装
- ✅ 4つの静的チェッカー
- ✅ テスト96%カバレッジ

### Phase 2.2 (完了)
- ✅ DirectorLLM: LLMベースの5軸評価スコアリング
- ✅ DirectorHybrid: 静的チェック + LLM評価のハイブリッド方式
- ✅ ThresholdConfig: 閾値設定による判定
- ✅ テスト190件、カバレッジ94%

### Phase 2.3 (計画中)
- DirectorWithNovelty: 話題ループ検出
- NoveltyGuard実装
