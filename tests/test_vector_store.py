from zhicore.types import Chunk
from zhicore.vector_store import HybridRetriever, InMemoryVectorStore


def test_search_returns_relevant_chunk() -> None:
    store = InMemoryVectorStore()
    chunks = [
        Chunk(
            chunk_id="c1",
            document_id="d1",
            source="a.md",
            text="FastAPI is a modern Python web framework.",
            start=0,
            end=40,
        ),
        Chunk(
            chunk_id="c2",
            document_id="d1",
            source="a.md",
            text="Neo4j is commonly used for knowledge graph storage.",
            start=41,
            end=90,
        ),
    ]
    store.add_chunks(chunks)

    hits = store.search("what is a python web framework", top_k=1)
    assert len(hits) == 1
    assert hits[0].chunk.chunk_id == "c1"


def test_hybrid_retriever_dense_sparse_modes() -> None:
    chunks = [
        Chunk(
            chunk_id="c1",
            document_id="d1",
            source="a.md",
            text="FastAPI is a modern Python web framework.",
            start=0,
            end=40,
        ),
        Chunk(
            chunk_id="c2",
            document_id="d1",
            source="a.md",
            text="Surface code logical qubit improves error correction.",
            start=41,
            end=100,
        ),
    ]
    retriever = HybridRetriever(chunks=chunks)

    dense_hits = retriever.search("python web framework", top_k=1, retrieval_mode="dense")
    sparse_hits = retriever.search("logical qubit", top_k=2, retrieval_mode="sparse")
    hybrid_hits = retriever.search("logical qubit", top_k=2, retrieval_mode="hybrid")

    assert dense_hits[0].chunk.chunk_id == "c1"
    assert "c2" in {hit.chunk.chunk_id for hit in sparse_hits}
    assert "c2" in {hit.chunk.chunk_id for hit in hybrid_hits}
