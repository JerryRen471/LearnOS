"""Embedding implementations used by the retrieval layer."""

from __future__ import annotations

import hashlib
import math
import re
from typing import Protocol

TOKEN_PATTERN = re.compile(r"[A-Za-z0-9\u4e00-\u9fff]+")


class Embedder(Protocol):
    """Common embedder protocol for pluggable retrieval backends."""

    dim: int

    def embed(self, text: str) -> list[float]:
        ...

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        ...


class HashEmbedding:
    """Deterministic lightweight embedding without external services."""

    def __init__(self, dim: int = 384) -> None:
        if dim <= 0:
            raise ValueError("dim must be > 0")
        self.dim = dim

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dim
        tokens = TOKEN_PATTERN.findall(text.lower())
        if not tokens:
            return vector

        for token in tokens:
            digest = hashlib.sha1(token.encode("utf-8")).digest()
            bucket = int.from_bytes(digest[:4], "big") % self.dim
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[bucket] += sign

        return _normalize(vector)

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(text) for text in texts]


class SentenceTransformerEmbedding:
    """SentenceTransformer embedder with normalized dense vectors."""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:  # pragma: no cover - import guard
            raise RuntimeError(
                "SentenceTransformer embedding requires extra deps. "
                "Install with: pip install '.[rag-advanced]'"
            ) from exc
        self.model_name = model_name
        self._model = SentenceTransformer(model_name)
        self.dim = int(self._model.get_sentence_embedding_dimension())
        self._cache: dict[str, list[float]] = {}

    def embed(self, text: str) -> list[float]:
        cached = self._cache.get(text)
        if cached is not None:
            return cached
        vector = self._model.encode([text], normalize_embeddings=True)[0]
        result = [float(value) for value in vector]
        self._cache[text] = result
        return result

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        uncached: list[str] = []
        for text in texts:
            if text not in self._cache:
                uncached.append(text)
        if uncached:
            matrix = self._model.encode(uncached, normalize_embeddings=True)
            for text, row in zip(uncached, matrix):
                self._cache[text] = [float(value) for value in row]
        return [self._cache[text] for text in texts]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        raise ValueError("Vector dimensions do not match.")
    return sum(a * b for a, b in zip(left, right))


def _normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0.0:
        return vector
    return [value / norm for value in vector]
