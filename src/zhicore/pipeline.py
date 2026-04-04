"""Pipeline helpers for ingestion and retrieval runtime."""

from __future__ import annotations

import json
from pathlib import Path

from zhicore.chunking import chunk_documents
from zhicore.embedding import HashEmbedding, SentenceTransformerEmbedding
from zhicore.ingest import ingest_inputs
from zhicore.vector_store import HybridRetriever, InMemoryVectorStore


def ingest_documents(
    inputs: list[str],
    index_path: str,
    chunk_size: int = 600,
    overlap: int = 120,
    embedding_provider: str = "hash",
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
    dense_backend: str = "cosine",
) -> dict[str, int]:
    """Run ingestion -> chunking -> indexing and persist index."""
    documents = ingest_inputs(inputs)
    chunks = chunk_documents(documents, chunk_size=chunk_size, overlap=overlap)
    embedder = _build_embedder(
        embedding_provider=embedding_provider,
        embedding_model=embedding_model,
    )
    retriever = HybridRetriever(chunks=chunks, embedder=embedder, dense_backend=dense_backend)
    retriever.save(index_path=index_path)
    return {"documents": len(documents), "chunks": len(chunks), "indexed": len(chunks)}


def load_store(
    index_path: str,
    embedding_provider: str = "auto",
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
    dense_backend: str = "auto",
):
    """Load either advanced hybrid index or legacy dense index."""
    meta = _read_index_meta(index_path)
    if int(meta.get("version", 1)) < 2:
        return InMemoryVectorStore.load(index_path=index_path)

    provider = embedding_provider
    if provider == "auto":
        provider = str(meta.get("embedder", "hash"))
    backend = dense_backend if dense_backend != "auto" else str(meta.get("dense_backend", "cosine"))
    embedder = _build_embedder(
        embedding_provider=provider,
        embedding_model=embedding_model,
        dim=int(meta.get("embedder_dim", 384)),
    )
    return HybridRetriever.load(index_path=index_path, embedder=embedder, dense_backend=backend)


def _build_embedder(
    embedding_provider: str,
    embedding_model: str,
    dim: int | None = None,
):
    if embedding_provider == "hash":
        return HashEmbedding(dim=dim or 384)
    if embedding_provider == "sentence-transformers":
        return SentenceTransformerEmbedding(model_name=embedding_model)
    raise ValueError(f"Unsupported embedding provider: {embedding_provider}")


def _read_index_meta(index_path: str) -> dict:
    path = Path(index_path)
    if not path.exists():
        raise FileNotFoundError(f"Index file not found: {index_path}")
    return json.loads(path.read_text(encoding="utf-8"))
