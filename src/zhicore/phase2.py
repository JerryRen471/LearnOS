"""Phase 2 services: KG build/update, subgraph query, Graph-RAG query."""

from __future__ import annotations

from pathlib import Path

from zhicore.chunking import chunk_documents
from zhicore.graph_rag import GraphRAGEngine, GraphRAGResult
from zhicore.kg import KnowledgeGraph, build_knowledge_graph
from zhicore.pipeline import _build_embedder, _read_index_meta, load_store
from zhicore.types import Chunk
from zhicore.vector_store import HybridRetriever, InMemoryVectorStore
from zhicore.ingest import ingest_inputs


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
    documents = ingest_inputs(inputs)
    chunks = chunk_documents(documents, chunk_size=chunk_size, overlap=overlap)
    if not chunks:
        raise ValueError("No chunks generated from inputs.")

    _upsert_index(
        chunks=chunks,
        index_path=index_path,
        incremental=incremental,
        embedding_provider=embedding_provider,
        embedding_model=embedding_model,
        dense_backend=dense_backend,
    )
    graph = _upsert_graph(chunks=chunks, graph_path=graph_path, incremental=incremental)
    return {
        "documents": len(documents),
        "chunks": len(chunks),
        "nodes": len(graph.nodes),
        "edges": len(graph.edges),
    }


def query_subgraph(
    graph_path: str,
    query: str | None = None,
    concept: str | None = None,
    hops: int = 1,
    max_nodes: int = 80,
) -> dict[str, list[dict]]:
    graph = KnowledgeGraph.load(graph_path)
    seed = graph.find_concepts(concept or query or "", max_results=12)
    return graph.subgraph(seed_node_ids=seed, hops=hops, max_nodes=max_nodes)


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


def _upsert_graph(chunks: list[Chunk], graph_path: str, incremental: bool) -> KnowledgeGraph:
    new_graph = build_knowledge_graph(chunks)
    path = Path(graph_path)
    if incremental and path.exists():
        current = KnowledgeGraph.load(graph_path)
        current.merge(new_graph)
        current.save(graph_path)
        return current
    new_graph.save(graph_path)
    return new_graph


def _upsert_index(
    chunks: list[Chunk],
    index_path: str,
    incremental: bool,
    embedding_provider: str,
    embedding_model: str,
    dense_backend: str,
) -> None:
    combined_chunks = chunks
    provider = embedding_provider
    backend = dense_backend
    path = Path(index_path)
    if incremental and path.exists():
        existing_store = load_store(index_path=index_path)
        existing_chunks = _extract_chunks(existing_store)
        existing_map = {chunk.chunk_id: chunk for chunk in existing_chunks}
        for chunk in chunks:
            existing_map[chunk.chunk_id] = chunk
        combined_chunks = list(existing_map.values())

        meta = _read_index_meta(index_path)
        provider = str(meta.get("embedder", embedding_provider))
        backend = str(meta.get("dense_backend", dense_backend))

    embedder = _build_embedder(
        embedding_provider=provider,
        embedding_model=embedding_model,
    )
    retriever = HybridRetriever(chunks=combined_chunks, embedder=embedder, dense_backend=backend)
    retriever.save(index_path=index_path)


def _extract_chunks(store: InMemoryVectorStore | HybridRetriever) -> list[Chunk]:
    if isinstance(store, HybridRetriever):
        return list(store.chunks)
    return [record.chunk for record in store.records]
