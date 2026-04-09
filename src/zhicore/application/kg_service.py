"""Application services for knowledge graph operations (Phase 2)."""

from __future__ import annotations

from pathlib import Path

from zhicore.chunking import chunk_documents
from zhicore.ingest import ingest_inputs
from zhicore.kg import KnowledgeGraph, build_knowledge_graph
from zhicore.types import Chunk


def build_or_update_kg(
    *,
    inputs: list[str],
    graph_path: str,
    index_upsert: callable[[list[Chunk]], None],
    chunk_size: int = 600,
    overlap: int = 120,
    incremental: bool = True,
) -> dict[str, int]:
    """Build/update KG and delegate index updates to caller-provided upsert."""
    documents = ingest_inputs(inputs)
    chunks = chunk_documents(documents, chunk_size=chunk_size, overlap=overlap)
    if not chunks:
        raise ValueError("No chunks generated from inputs.")

    index_upsert(chunks)
    graph = _upsert_graph(chunks=chunks, graph_path=graph_path, incremental=incremental)
    return {"documents": len(documents), "chunks": len(chunks), "nodes": len(graph.nodes), "edges": len(graph.edges)}


def query_subgraph(
    *,
    graph_path: str,
    query: str | None = None,
    concept: str | None = None,
    hops: int = 1,
    max_nodes: int = 80,
) -> dict[str, list[dict]]:
    graph = KnowledgeGraph.load(graph_path)
    seed = graph.find_concepts(concept or query or "", max_results=12)
    return graph.subgraph(seed_node_ids=seed, hops=hops, max_nodes=max_nodes)


def kg_stats(*, graph_path: str) -> dict:
    graph = KnowledgeGraph.load(graph_path)
    return graph.stats()


def _upsert_graph(*, chunks: list[Chunk], graph_path: str, incremental: bool) -> KnowledgeGraph:
    new_graph = build_knowledge_graph(chunks)
    path = Path(graph_path)
    if incremental and path.exists():
        current = KnowledgeGraph.load(graph_path)
        current.merge(new_graph)
        current.save(graph_path)
        return current
    new_graph.save(graph_path)
    return new_graph

