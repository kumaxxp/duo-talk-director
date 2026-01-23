"""duo-talk-director: Dialogue quality monitoring and control

Phase 2 of duo-talk-ecosystem: Optional quality control for duo-talk-core.
Provides static checks, LLM scoring, and loop detection.
"""

from .interfaces import (
    DirectorStatus,
    DirectorEvaluation,
    DirectorProtocol,
    LLMEvaluationScore,
)
from .director_minimal import DirectorMinimal
from .director_llm import DirectorLLM
from .director_hybrid import DirectorHybrid
from .config.thresholds import ThresholdConfig

__version__ = "2.0.0"  # Phase 2.2: LLM-based Director
__all__ = [
    # Interfaces
    "DirectorStatus",
    "DirectorEvaluation",
    "DirectorProtocol",
    "LLMEvaluationScore",
    # Directors
    "DirectorMinimal",
    "DirectorLLM",
    "DirectorHybrid",
    # Config
    "ThresholdConfig",
]
