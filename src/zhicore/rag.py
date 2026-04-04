"""RAG orchestration for the optimized retrieval layer."""

from __future__ import annotations

from dataclasses import dataclass

from zhicore.types import SearchHit
from zhicore.vector_store import HybridRetriever, InMemoryVectorStore


@dataclass(slots=True)
class Citation:
    index: int
    source: str
    chunk_id: str
    score: float
    excerpt: str


@dataclass(slots=True)
class RAGResult:
    answer: str
    citations: list[Citation]


class RAGEngine:
    """Minimal RAG engine returning answer + citations."""

    def __init__(self, store: InMemoryVectorStore | HybridRetriever) -> None:
        self.store = store

    def ask(
        self,
        query: str,
        top_k: int = 4,
        dense_k: int = 12,
        sparse_k: int = 12,
        rrf_k: int = 60,
        retrieval_mode: str = "hybrid",
    ) -> RAGResult:
        search_params = {"query": query, "top_k": top_k}
        if _accepts_hybrid_kwargs(self.store):
            search_params.update(
                {
                    "dense_k": dense_k,
                    "sparse_k": sparse_k,
                    "rrf_k": rrf_k,
                    "retrieval_mode": retrieval_mode,
                }
            )
        hits = self.store.search(**search_params)
        if not hits:
            return RAGResult(answer="未检索到相关知识片段，请先执行 ingest。", citations=[])

        citations = self._build_citations(hits)
        answer = self._build_answer(query, citations)
        return RAGResult(answer=answer, citations=citations)

    def _build_citations(self, hits: list[SearchHit]) -> list[Citation]:
        citations: list[Citation] = []
        for idx, hit in enumerate(hits, start=1):
            excerpt = " ".join(hit.chunk.text.split())
            if len(excerpt) > 200:
                excerpt = excerpt[:200] + "..."
            citations.append(
                Citation(
                    index=idx,
                    source=hit.chunk.source,
                    chunk_id=hit.chunk.chunk_id,
                    score=hit.score,
                    excerpt=excerpt,
                )
            )
        return citations

    def _build_answer(self, query: str, citations: list[Citation]) -> str:
        lines = [f"问题：{query}", "基于检索到的上下文，可参考以下片段："]
        for citation in citations:
            lines.append(f"[{citation.index}] {citation.excerpt}")
        return "\n".join(lines)


def _accepts_hybrid_kwargs(store: object) -> bool:
    klass = store.__class__.__name__.lower()
    return "hybrid" in klass
