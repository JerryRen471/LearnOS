"""Phase 2 Graph-RAG query wrapper (backward compatible)."""

from __future__ import annotations

from zhicore.application.query_service import query_graph_rag as _query_graph_rag
from zhicore.graph_rag import GraphRAGResult


def query_graph_rag(
    query: str,
    index_path: str,
    graph_path: str,
    top_k: int = 4,
    dense_k: int = 12,
    sparse_k: int = 12,
    rrf_k: int = 60,
    retrieval_mode: str = "hybrid",
    graph_hops: int = 1,
    embedding_provider: str = "auto",
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
    dense_backend: str = "auto",
) -> GraphRAGResult:
    return _query_graph_rag(
        query=query,
        index_path=index_path,
        graph_path=graph_path,
        top_k=top_k,
        dense_k=dense_k,
        sparse_k=sparse_k,
        rrf_k=rrf_k,
        retrieval_mode=retrieval_mode,
        graph_hops=graph_hops,
        embedding_provider=embedding_provider,
        embedding_model=embedding_model,
        dense_backend=dense_backend,
    )

