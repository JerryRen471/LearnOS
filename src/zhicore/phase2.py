"""Phase 2 services: KG build/update, subgraph query, Graph-RAG query."""

from __future__ import annotations

from zhicore.application.kg_service import kg_stats as _kg_stats
from zhicore.application.kg_service import query_subgraph as _query_subgraph
from zhicore.application.query_service import query_graph_rag as _query_graph_rag

from zhicore.pipeline import load_store


def build_or_update_kg(
    inputs: list[str],
    graph_path: str,
    index_path: str,
    chunk_size: int = 600,
    overlap: int = 120,
    embedding_provider: str = "hash",
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
    dense_backend: str = "cosine",
    incremental: bool = True,
) -> dict[str, int]:
    from zhicore.application.kg_service import build_or_update_kg as _build_or_update_kg

    def _index_upsert(chunks):
        # Preserve the pre-refactor Phase 2 behavior: always rebuild/persist a HybridRetriever
        # index from chunks, merging with existing chunks when incremental=True and index exists.
        from pathlib import Path

        from zhicore.pipeline import _build_embedder, _read_index_meta
        from zhicore.vector_store import HybridRetriever

        combined = list(chunks)
        provider = embedding_provider
        backend = dense_backend
        path = Path(index_path)
        if incremental and path.exists():
            meta = _read_index_meta(index_path)
            provider = str(meta.get("embedder", embedding_provider))
            backend = str(meta.get("dense_backend", dense_backend))
            existing_store = load_store(
                index_path=index_path,
                embedding_provider=embedding_provider,
                embedding_model=embedding_model,
                dense_backend=dense_backend,
            )
            existing_chunks = list(getattr(existing_store, "chunks", []))
            existing_map = {c.chunk_id: c for c in existing_chunks}
            for c in chunks:
                existing_map[c.chunk_id] = c
            combined = list(existing_map.values())

        embedder = _build_embedder(embedding_provider=provider, embedding_model=embedding_model)
        HybridRetriever(chunks=combined, embedder=embedder, dense_backend=backend).save(index_path=index_path)

    return _build_or_update_kg(
        inputs=inputs,
        graph_path=graph_path,
        index_upsert=_index_upsert,
        chunk_size=chunk_size,
        overlap=overlap,
        incremental=incremental,
    )


def query_subgraph(
    graph_path: str,
    query: str | None = None,
    concept: str | None = None,
    hops: int = 1,
    max_nodes: int = 80,
) -> dict[str, list[dict]]:
    return _query_subgraph(
        graph_path=graph_path,
        query=query,
        concept=concept,
        hops=hops,
        max_nodes=max_nodes,
    )


def kg_stats(graph_path: str) -> dict:
    return _kg_stats(graph_path=graph_path)


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
