"""duo-talk-director: Dialogue quality monitoring and control

Phase 2 of duo-talk-ecosystem: Optional quality control for duo-talk-core.
Provides static checks, LLM scoring, and loop detection.

Phase 2.3: Added logging for ActionSanitizer and Thought generation.
"""

from .interfaces import (
    DirectorStatus,
    DirectorEvaluation,
    DirectorProtocol,
    LLMEvaluationScore,
    RAGFactEntry,
    RAGLogEntry,
    RAGSummary,
)
from .director_minimal import DirectorMinimal
from .director_llm import DirectorLLM
from .director_hybrid import DirectorHybrid
from .config.thresholds import ThresholdConfig
from .logging import (
    SanitizerLogger,
    SanitizerLogEntry,
    ThoughtLogger,
    ThoughtLogEntry,
    LogStore,
    get_log_store,
    reset_log_store,
)

__version__ = "3.1.0"  # Phase 3.1: RAG integration (log only)
__all__ = [
    # Interfaces
    "DirectorStatus",
    "DirectorEvaluation",
    "DirectorProtocol",
    "LLMEvaluationScore",
    # RAG types (Phase 3.1)
    "RAGFactEntry",
    "RAGLogEntry",
    "RAGSummary",
    # Directors
    "DirectorMinimal",
    "DirectorLLM",
    "DirectorHybrid",
    # Config
    "ThresholdConfig",
    # Logging (Phase 2.3)
    "SanitizerLogger",
    "SanitizerLogEntry",
    "ThoughtLogger",
    "ThoughtLogEntry",
    "LogStore",
    "get_log_store",
    "reset_log_store",
]
