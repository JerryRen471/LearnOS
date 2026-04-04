"""Chunking utilities for Phase 1."""

from __future__ import annotations

from zhicore.types import Chunk, Document


def chunk_document(
    document: Document,
    chunk_size: int = 600,
    overlap: int = 120,
) -> list[Chunk]:
    """Split one document with fixed window + overlap."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0")
    if overlap < 0:
        raise ValueError("overlap must be >= 0")
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    text = document.text
    if not text.strip():
        return []

    chunks: list[Chunk] = []
    start = 0
    index = 0
    length = len(text)
    while start < length:
        end = min(start + chunk_size, length)
        end = _prefer_boundary(text, start, end, chunk_size)
        chunk_text = text[start:end].strip()
        if chunk_text:
            chunk_id = f"{document.id}-{index:04d}"
            chunks.append(
                Chunk(
                    chunk_id=chunk_id,
                    document_id=document.id,
                    source=document.source,
                    text=chunk_text,
                    start=start,
                    end=end,
                    metadata={"chunk_index": index},
                )
            )
            index += 1

        if end >= length:
            break
        next_start = max(end - overlap, start + 1)
        start = next_start
    return chunks


def chunk_documents(
    documents: list[Document],
    chunk_size: int = 600,
    overlap: int = 120,
) -> list[Chunk]:
    """Split many documents into one chunk list."""
    all_chunks: list[Chunk] = []
    for document in documents:
        all_chunks.extend(chunk_document(document, chunk_size=chunk_size, overlap=overlap))
    return all_chunks


def _prefer_boundary(text: str, start: int, end: int, chunk_size: int) -> int:
    if end >= len(text):
        return end
    # Try to end near a natural boundary without shrinking too much.
    search_start = max(start + chunk_size // 2, start)
    window = text[search_start:end]
    candidates = [window.rfind("\n"), window.rfind("。"), window.rfind("."), window.rfind("!"), window.rfind("?")]
    best = max(candidates)
    if best == -1:
        return end
    return search_start + best + 1
