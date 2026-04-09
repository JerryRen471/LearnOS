"""Application services for query execution (Graph-RAG + Agent) without HTTP bindings.

This module intentionally does NOT import `zhicore.phase2` to avoid circular imports.
"""

from __future__ import annotations

from zhicore.graph_rag import GraphRAGEngine, GraphRAGResult
from zhicore.kg import KnowledgeGraph
from zhicore.pipeline import load_store
from zhicore.phase3 import run_agent_query


def query_graph_rag(
    *,
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
    store = load_store(
        index_path=index_path,
        embedding_provider=embedding_provider,
        embedding_model=embedding_model,
        dense_backend=dense_backend,
    )
    graph = KnowledgeGraph.load(graph_path)
    engine = GraphRAGEngine(store=store, graph=graph)
    return engine.ask(
        query=query,
        top_k=top_k,
        dense_k=dense_k,
        sparse_k=sparse_k,
        rrf_k=rrf_k,
        retrieval_mode=retrieval_mode,
        graph_hops=graph_hops,
    )


def query_agent(**kwargs) -> dict:
    return run_agent_query(**kwargs)

