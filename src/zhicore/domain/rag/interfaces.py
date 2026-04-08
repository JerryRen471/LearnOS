"""Domain interfaces for the retrieval layer (RAG)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from zhicore.types import SearchHit


@dataclass(frozen=True, slots=True)
class RetrievalParams:
    """Retrieval parameters shared across dense/sparse/hybrid backends."""

    query: str = ""
    top_k: int = 4
    dense_k: int = 12
    sparse_k: int = 12
    rrf_k: int = 60
    retrieval_mode: str = "hybrid"


class Retriever(Protocol):
    """Retriever interface for RAG pipelines."""

    def retrieve(self, params: RetrievalParams) -> list[SearchHit]:
        ...

