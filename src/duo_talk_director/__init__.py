"""duo-talk-director: Dialogue quality monitoring and control

Phase 2 of duo-talk-ecosystem: Optional quality control for duo-talk-core.
Provides static checks, LLM scoring, and loop detection.
"""

from .interfaces import (
    DirectorStatus,
    DirectorEvaluation,
    DirectorProtocol,
)
from .director_minimal import DirectorMinimal

__version__ = "1.0.0"
__all__ = [
    "DirectorStatus",
    "DirectorEvaluation",
    "DirectorProtocol",
    "DirectorMinimal",
]
