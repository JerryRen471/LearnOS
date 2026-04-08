"""Vector stores with dense/sparse/hybrid retrieval and persistence."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from zhicore.embedding import Embedder, HashEmbedding, cosine_similarity
from zhicore.domain.rag.interfaces import RetrievalParams
from zhicore.types import Chunk, SearchHit


@dataclass(slots=True)
class VectorRecord:
    chunk: Chunk
    embedding: list[float]


class InMemoryVectorStore:
    """Simple in-memory dense vector store."""

    def __init__(self, embedder: Embedder | None = None) -> None:
        self.embedder = embedder or HashEmbedding()
        self.records: list[VectorRecord] = []

    def add_chunks(self, chunks: list[Chunk]) -> int:
        embeddings = self.embedder.embed_many([chunk.text for chunk in chunks])
        for chunk, embedding in zip(chunks, embeddings):
            self.records.append(VectorRecord(chunk=chunk, embedding=embedding))
        return len(chunks)

    def retrieve(self, params: RetrievalParams) -> list[SearchHit]:
        return self.search(query=params.query, top_k=params.top_k)

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
        if type(self.embedder) is not HashEmbedding:
            raise RuntimeError("Dense JSON persistence only supports HashEmbedding for now.")
        path = Path(index_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "dim": self.embedder.dim,
            "embedder": "hash",
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
        if raw.get("embedder", "hash") != "hash":
            raise RuntimeError(
                "Dense index embedder is not hash. Load via HybridRetriever for advanced indexes."
            )
        store = cls(embedder=HashEmbedding(dim=raw["dim"]))
        for item in raw.get("records", []):
            chunk = Chunk(**item["chunk"])
            store.records.append(VectorRecord(chunk=chunk, embedding=item["embedding"]))
        return store


class HybridRetriever:
    """Hybrid retriever: dense + BM25 with reciprocal rank fusion."""

    def __init__(
        self,
        chunks: list[Chunk],
        embedder: Embedder | None = None,
        dense_backend: str = "cosine",
    ) -> None:
        self.chunks = chunks
        self.embedder = embedder or HashEmbedding()
        self.dense_backend = dense_backend
        self._dense_embeddings = self.embedder.embed_many([chunk.text for chunk in chunks]) if chunks else []
        self._bm25 = self._build_bm25(chunks)
        self._faiss_index = self._build_faiss_index(self._dense_embeddings) if chunks else None

    def search(
        self,
        query: str,
        top_k: int = 4,
        dense_k: int = 12,
        sparse_k: int = 12,
        rrf_k: int = 60,
        retrieval_mode: str = "hybrid",
    ) -> list[SearchHit]:
        if top_k <= 0:
            raise ValueError("top_k must be > 0")
        if not self.chunks:
            return []

        dense_hits = self._dense_search(query, top_k=max(top_k, dense_k))
        sparse_hits = self._sparse_search(query, top_k=max(top_k, sparse_k))
        if retrieval_mode == "dense":
            return dense_hits[:top_k]
        if retrieval_mode == "sparse":
            return sparse_hits[:top_k]
        if retrieval_mode != "hybrid":
            raise ValueError("retrieval_mode must be one of: hybrid, dense, sparse")
        fused = self._rrf_fuse(dense_hits, sparse_hits, rrf_k=rrf_k)
        return fused[:top_k]

    def retrieve(self, params: RetrievalParams) -> list[SearchHit]:
        return self.search(
            query=params.query,
            top_k=params.top_k,
            dense_k=params.dense_k,
            sparse_k=params.sparse_k,
            rrf_k=params.rrf_k,
            retrieval_mode=params.retrieval_mode,
        )

    def save(self, index_path: str) -> None:
        path = Path(index_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 2,
            "embedder": self._embedder_name(),
            "embedder_model": getattr(self.embedder, "model_name", None),
            "embedder_dim": self.embedder.dim,
            "dense_backend": self.dense_backend,
            "chunks": [asdict(chunk) for chunk in self.chunks],
            "embeddings": self._dense_embeddings,
        }
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(
        cls,
        index_path: str,
        embedder: Embedder | None = None,
        dense_backend: str | None = None,
    ) -> "HybridRetriever":
        path = Path(index_path)
        if not path.exists():
            raise FileNotFoundError(f"Index file not found: {index_path}")
        raw = json.loads(path.read_text(encoding="utf-8"))

        chunks = [Chunk(**item) for item in raw.get("chunks", [])]
        retriever = cls.__new__(cls)
        retriever.chunks = chunks
        retriever.embedder = embedder or HashEmbedding(dim=int(raw.get("embedder_dim", 384)))
        retriever.dense_backend = dense_backend or raw.get("dense_backend", "cosine")
        retriever._dense_embeddings = raw.get("embeddings", [])
        retriever._bm25 = retriever._build_bm25(chunks)
        retriever._faiss_index = retriever._build_faiss_index(retriever._dense_embeddings) if chunks else None
        return retriever

    def _embedder_name(self) -> str:
        klass = self.embedder.__class__.__name__.lower()
        if "sentence" in klass:
            return "sentence-transformers"
        if "hash" in klass:
            return "hash"
        return klass

    def _dense_search(self, query: str, top_k: int) -> list[SearchHit]:
        if self.dense_backend == "faiss" and self._faiss_index is not None:
            return self._dense_search_faiss(query, top_k)
        return self._dense_search_cosine(query, top_k)

    def _dense_search_cosine(self, query: str, top_k: int) -> list[SearchHit]:
        query_embedding = self.embedder.embed(query)
        ranked = sorted(
            (
                SearchHit(score=cosine_similarity(query_embedding, embedding), chunk=chunk)
                for chunk, embedding in zip(self.chunks, self._dense_embeddings)
            ),
            key=lambda hit: hit.score,
            reverse=True,
        )
        return ranked[:top_k]

    def _dense_search_faiss(self, query: str, top_k: int) -> list[SearchHit]:
        try:
            import numpy as np
        except ImportError as exc:  # pragma: no cover - import guard
            raise RuntimeError("FAISS backend requires numpy.") from exc

        query_vec = np.array([self.embedder.embed(query)], dtype="float32")
        scores, indices = self._faiss_index.search(query_vec, top_k)
        hits: list[SearchHit] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                continue
            hits.append(SearchHit(score=float(score), chunk=self.chunks[int(idx)]))
        return hits

    def _sparse_search(self, query: str, top_k: int) -> list[SearchHit]:
        if self._bm25 is None:
            return self._sparse_search_fallback(query, top_k)
        tokens = _tokenize(query)
        scores = self._bm25.get_scores(tokens)
        indexed = sorted(enumerate(scores), key=lambda item: float(item[1]), reverse=True)
        hits: list[SearchHit] = []
        for idx, score in indexed[:top_k]:
            hits.append(SearchHit(score=float(score), chunk=self.chunks[idx]))
        return hits

    def _sparse_search_fallback(self, query: str, top_k: int) -> list[SearchHit]:
        """Fallback sparse search when BM25 dependency is unavailable."""
        query_tokens = _tokenize(query)
        if not query_tokens:
            return []
        query_set = set(query_tokens)
        scored: list[tuple[int, float]] = []
        for idx, chunk in enumerate(self.chunks):
            chunk_tokens = _tokenize(chunk.text)
            if not chunk_tokens:
                continue
            overlap = len(query_set.intersection(chunk_tokens))
            if overlap <= 0:
                continue
            # lightweight lexical score: overlap normalized by query size
            score = overlap / max(1, len(query_set))
            scored.append((idx, float(score)))
        ranked = sorted(scored, key=lambda item: item[1], reverse=True)
        hits: list[SearchHit] = []
        for idx, score in ranked[:top_k]:
            hits.append(SearchHit(score=score, chunk=self.chunks[idx]))
        return hits

    def _rrf_fuse(self, dense_hits: list[SearchHit], sparse_hits: list[SearchHit], rrf_k: int) -> list[SearchHit]:
        accum: dict[str, dict[str, Any]] = {}
        self._accumulate_rrf(accum, dense_hits, rrf_k=rrf_k)
        self._accumulate_rrf(accum, sparse_hits, rrf_k=rrf_k)
        ranked = sorted(accum.values(), key=lambda item: float(item["score"]), reverse=True)
        return [SearchHit(score=float(item["score"]), chunk=item["chunk"]) for item in ranked]

    def _accumulate_rrf(
        self,
        accum: dict[str, dict[str, Any]],
        hits: list[SearchHit],
        rrf_k: int,
    ) -> None:
        for rank, hit in enumerate(hits, start=1):
            key = hit.chunk.chunk_id
            rrf_score = 1.0 / (rrf_k + rank)
            if key not in accum:
                accum[key] = {"chunk": hit.chunk, "score": 0.0}
            accum[key]["score"] += rrf_score

    def _build_bm25(self, chunks: list[Chunk]):
        if not chunks:
            return None
        try:
            from rank_bm25 import BM25Okapi
        except ImportError:  # pragma: no cover - import guard
            return None
        corpus = [_tokenize(chunk.text) for chunk in chunks]
        return BM25Okapi(corpus)

    def _build_faiss_index(self, embeddings: list[list[float]]):
        if self.dense_backend != "faiss":
            return None
        try:
            import faiss
            import numpy as np
        except ImportError as exc:  # pragma: no cover - import guard
            raise RuntimeError(
                "FAISS backend requires faiss-cpu and numpy. Install with: pip install '.[rag]'"
            ) from exc
        matrix = np.array(embeddings, dtype="float32")
        index = faiss.IndexFlatIP(matrix.shape[1])
        index.add(matrix)
        return index


def _tokenize(text: str) -> list[str]:
    import re

    tokens = re.findall(r"[A-Za-z0-9\u4e00-\u9fff]+", text.lower())
    return tokens if tokens else [text.lower()]
