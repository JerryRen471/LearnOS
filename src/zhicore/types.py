"""Core data structures for the Phase 1 pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Document:
    """A normalized source document."""

    id: str
    source: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Chunk:
    """A text chunk generated from a document."""

    chunk_id: str
    document_id: str
    source: str
    text: str
    start: int
    end: int
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SearchHit:
    """A retrieval result with score."""

    score: float
    chunk: Chunk
