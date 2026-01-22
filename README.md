# duo-talk-director

Dialogue quality monitoring and control for duo-talk-core.

## Overview

duo-talk-director provides optional quality control for duo-talk-core dialogue generation:

- **Static Checks**: Tone markers, forbidden words, setting consistency
- **LLM Scoring**: 5-axis quality evaluation (Phase 2.2)
- **Loop Detection**: NoveltyGuard for repetition prevention (Phase 2.3)

## Installation

```bash
# Development installation
pip install -e ".[dev]"

# With duo-talk-core integration
pip install -e ".[dev,core]"
```

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
print(f"Reason: {evaluation.reason}")
```

## Integration with duo-talk-core

```python
from duo_talk_core import create_dialogue_manager
from duo_talk_director import DirectorMinimal

# Create manager with director
director = DirectorMinimal()
manager = create_dialogue_manager(
    model="gemma3:12b",
    director=director,
)

# Generate dialogue with quality control
session = manager.run_session(
    topic="最近のAI技術について",
    turns=5,
)
```

## Director Types

| Type | Features | Latency |
|------|----------|---------|
| DirectorMinimal | Static checks only | <200ms |
| Director | LLM scoring + static | <2s |
| DirectorWithNovelty | Full features | <3s |

## Evaluation Status

- `PASS`: Quality OK, no intervention needed
- `WARN`: Minor issues, acceptable
- `RETRY`: Regenerate response
- `MODIFY`: Critical issue, may need to stop

## Testing

```bash
# Run tests
python -m pytest tests/ -v

# With coverage
python -m pytest tests/ -v --cov=src/duo_talk_director --cov-report=term-missing
```

## License

MIT
