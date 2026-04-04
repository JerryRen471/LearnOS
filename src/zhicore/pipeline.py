"""Pipeline helpers to run Phase 1 end-to-end."""

from __future__ import annotations

from zhicore.chunking import chunk_documents
from zhicore.ingest import ingest_inputs
from zhicore.vector_store import InMemoryVectorStore


def ingest_documents(
    inputs: list[str],
    index_path: str,
    chunk_size: int = 600,
    overlap: int = 120,
) -> dict[str, int]:
    """Run ingestion -> chunking -> indexing and persist index."""
    documents = ingest_inputs(inputs)
    chunks = chunk_documents(documents, chunk_size=chunk_size, overlap=overlap)
    store = InMemoryVectorStore()
    added = store.add_chunks(chunks)
    store.save(index_path=index_path)
    return {"documents": len(documents), "chunks": len(chunks), "indexed": added}


def load_store(index_path: str) -> InMemoryVectorStore:
    """Load a persisted vector store."""
    return InMemoryVectorStore.load(index_path=index_path)
