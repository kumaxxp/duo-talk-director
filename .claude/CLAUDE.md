# duo-talk-director Project

## プロジェクト概要
AI姉妹対話の品質制御システム。
**Phase 2**: Directorによる対話品質モニタリングと制御。

## 現在の状態 (2026-01-23)
- **DirectorMinimal**: ✅ 静的チェックのみの実装完了
- **テスト**: ✅ 65テスト passed, カバレッジ96%
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
│   ├── interfaces.py         # DirectorProtocol, CheckResult, DirectorStatus
│   ├── director_minimal.py   # 静的チェックのみのDirector
│   └── checks/
│       ├── __init__.py
│       ├── tone_check.py     # 口調マーカー検証
│       ├── praise_check.py   # 褒め言葉検出
│       ├── setting_check.py  # 設定違反検出
│       └── format_check.py   # 応答長検証
├── tests/
│   ├── conftest.py           # テストフィクスチャ
│   ├── test_checks.py        # 個別チェッカーのテスト
│   ├── test_director_minimal.py
│   └── integration/
│       └── test_with_core.py # duo-talk-coreとの統合テスト
└── config/
    └── (設定ファイル用)
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

### Phase 2.1 (現在完了)
- ✅ DirectorMinimal実装
- ✅ 4つの静的チェッカー
- ✅ テスト96%カバレッジ

### Phase 2.2 (計画中)
- Director: LLMベースの5軸評価スコアリング
- より高度な品質判定

### Phase 2.3 (計画中)
- DirectorWithNovelty: 話題ループ検出
- NoveltyGuard実装
