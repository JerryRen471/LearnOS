"""Phase 2: build/update KG + index (legacy-compatible API)."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from zhicore.pipeline import _build_embedder, _read_index_meta, load_store
from zhicore.vector_store import HybridRetriever


def build_or_update_kg(
    *,
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

    def _index_upsert(chunks: Iterable) -> None:
        # Preserve pre-refactor Phase 2 behavior: rebuild/persist a HybridRetriever index
        # and merge chunks with existing index when incremental=True.
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

