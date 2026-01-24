"""RAG module for fact-based context retrieval (Phase 3.1)

Provides:
- FactCard: Single fact representation
- RAGResult: Collection of facts from RAG search
- PersonaRAG: Character settings and rules retrieval
- SessionRAG: Scene and session memory retrieval
- RAGManager: Unified RAG interface
"""

from .fact_card import FactCard, RAGResult
from .persona_rag import PersonaRAG
from .session_rag import SessionRAG
from .rag_manager import RAGManager

__all__ = [
    "FactCard",
    "RAGResult",
    "PersonaRAG",
    "SessionRAG",
    "RAGManager",
]
