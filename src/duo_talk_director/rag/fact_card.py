"""FactCard and RAGResult data structures

FactCard represents a single fact retrieved from RAG.
RAGResult contains multiple FactCards from a search.
"""

from dataclasses import dataclass, field
from typing import Literal


MAX_FACT_LENGTH = 50
MAX_FACT_COUNT = 3

FactSource = Literal["persona", "session"]


@dataclass
class FactCard:
    """A single fact retrieved from RAG

    Attributes:
        content: Fact content (max 50 characters)
        source: "persona" or "session"
        priority: 1-4 (1 is highest priority)
        confidence: 0.0-1.0 confidence score
    """

    content: str
    source: FactSource
    priority: int = 4
    confidence: float = 1.0

    def __post_init__(self):
        """Validate fact card constraints"""
        if len(self.content) > MAX_FACT_LENGTH:
            raise ValueError(
                f"Fact content exceeds {MAX_FACT_LENGTH} chars: "
                f"{len(self.content)} chars"
            )
        if not 1 <= self.priority <= 4:
            raise ValueError(f"Priority must be 1-4, got {self.priority}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"Confidence must be 0.0-1.0, got {self.confidence}"
            )

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "content": self.content,
            "source": self.source,
            "priority": self.priority,
            "confidence": self.confidence,
        }

    def __str__(self) -> str:
        return f"FACT: {self.content}"


@dataclass
class RAGResult:
    """Result from RAG search

    Attributes:
        facts: List of FactCards (max 3)
        query_time_ms: Time taken for search in milliseconds
        sources_searched: List of sources that were searched
    """

    facts: list[FactCard] = field(default_factory=list)
    query_time_ms: float = 0.0
    sources_searched: list[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate result constraints"""
        if len(self.facts) > MAX_FACT_COUNT:
            raise ValueError(
                f"Too many facts: {len(self.facts)} > {MAX_FACT_COUNT}"
            )

    def add_fact(self, fact: FactCard) -> bool:
        """Add a fact if under limit

        Returns:
            True if added, False if limit reached
        """
        if len(self.facts) >= MAX_FACT_COUNT:
            return False
        self.facts.append(fact)
        return True

    def sort_by_priority(self) -> None:
        """Sort facts by priority (1 first)"""
        self.facts.sort(key=lambda f: f.priority)

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "facts": [f.to_dict() for f in self.facts],
            "query_time_ms": self.query_time_ms,
            "sources_searched": self.sources_searched,
        }

    def to_fact_string(self) -> str:
        """Convert to fact string format for logging"""
        return "\n".join(str(f) for f in self.facts)

    def __len__(self) -> int:
        return len(self.facts)

    def __bool__(self) -> bool:
        return len(self.facts) > 0
