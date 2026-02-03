# duo-talk-director

> 対話品質監視・RAG Injection・状態抽出

[![Version](https://img.shields.io/badge/Version-v1.0.0-blue)]()
[![Python](https://img.shields.io/badge/Python-3.11+-blue)]()
[![License](https://img.shields.io/badge/License-MIT-green)]()

---

## Overview

**duo-talk-director** は、duo-talk-coreの対話品質を監視・制御するコンポーネントです。

- **静的チェック**: トーンマーカー、禁止語、設定一貫性
- **LLMスコアリング**: 5軸品質評価
- **NoveltyGuard**: ループ検出・繰り返し防止
- **RAG Injection**: 事実情報の注入

---

## Features

| 機能 | 説明 |
|:-----|:-----|
| Static Checks | トーンマーカー検出、禁止語チェック |
| LLM Scoring | 5軸品質評価（キャラ性、自然さ等） |
| NoveltyGuard | 繰り返し・ループ検出 |
| RAG Observation | 状態監視・抽出 |
| RAG Injection | 事実情報の注入 |

---

## Installation

```bash
pip install -e .
```

---

## Quick Start

```python
from duo_talk_director import DirectorMinimal

# Create director
director = DirectorMinimal()

# Evaluate a response
evaluation = director.evaluate_response(
    speaker="やな",
    response="いいじゃんいいじゃん！あゆ、あとはよろしくね～",
    topic="今日のおやつ",
    history=[],
    turn_number=0,
)

print(f"Status: {evaluation.status}")  # PASS, WARN, RETRY, or MODIFY
```

---

## Director Types

| Type | Features | Latency | Use Case |
|:-----|:---------|:-------:|:---------|
| DirectorMinimal | 静的チェックのみ | <200ms | 軽量評価 |
| DirectorLLM | LLMスコアリング | <2s | 品質重視 |
| DirectorHybrid | 全機能 | <3s | 本番環境 |

---

## Evaluation Status

| Status | 説明 | アクション |
|:-------|:-----|:----------|
| `PASS` | 品質OK | 介入不要 |
| `WARN` | 軽微な問題 | 許容 |
| `RETRY` | 品質不足 | 再生成 |
| `MODIFY` | 重大な問題 | 停止検討 |

---

## Architecture

```
duo-talk-director/
├── src/duo_talk_director/
│   ├── director_minimal.py  # 静的チェック
│   ├── director_llm.py      # LLMスコアリング
│   ├── director_hybrid.py   # ハイブリッド
│   ├── novelty_guard.py     # ループ検出
│   └── rag_injector.py      # RAG Injection
└── tests/
```

---

## Ecosystem

```
duo-talk-ecosystem/
├── duo-talk-core/        # 対話生成エンジン
├── duo-talk-director/    # ← YOU ARE HERE
├── duo-talk-gm/          # 世界状態管理
└── duo-talk-evaluation/  # 統合評価・司令部 ⚓
```

詳細: [duo-talk-evaluation](https://github.com/kumaxxp/duo-talk-evaluation)

---

## License

MIT License
