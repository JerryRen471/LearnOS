"""In-memory vector store with JSON persistence."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from zhicore.embedding import HashEmbedding, cosine_similarity
from zhicore.types import Chunk, SearchHit


@dataclass(slots=True)
class VectorRecord:
    chunk: Chunk
    embedding: list[float]


class InMemoryVectorStore:
    """Simple vector store used by the Phase 1 MVP."""

    def __init__(self, embedder: HashEmbedding | None = None) -> None:
        self.embedder = embedder or HashEmbedding()
        self.records: list[VectorRecord] = []

    def add_chunks(self, chunks: list[Chunk]) -> int:
        embeddings = self.embedder.embed_many([chunk.text for chunk in chunks])
        for chunk, embedding in zip(chunks, embeddings):
            self.records.append(VectorRecord(chunk=chunk, embedding=embedding))
        return len(chunks)

    def search(self, query: str, top_k: int = 4) -> list[SearchHit]:
        if top_k <= 0:
            raise ValueError("top_k must be > 0")
        if not self.records:
            return []
        query_embedding = self.embedder.embed(query)
        ranked = sorted(
            (
                SearchHit(score=cosine_similarity(query_embedding, record.embedding), chunk=record.chunk)
                for record in self.records
            ),
            key=lambda hit: hit.score,
            reverse=True,
        )
        return ranked[:top_k]

    def save(self, index_path: str) -> None:
        path = Path(index_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "dim": self.embedder.dim,
            "records": [
                {
                    "chunk": asdict(record.chunk),
                    "embedding": record.embedding,
                }
                for record in self.records
            ],
        }
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls, index_path: str) -> "InMemoryVectorStore":
        path = Path(index_path)
        if not path.exists():
            raise FileNotFoundError(f"Index file not found: {index_path}")
        raw = json.loads(path.read_text(encoding="utf-8"))
        store = cls(embedder=HashEmbedding(dim=raw["dim"]))
        for item in raw.get("records", []):
            chunk = Chunk(**item["chunk"])
            store.records.append(VectorRecord(chunk=chunk, embedding=item["embedding"]))
        return store
