from zhicore.types import Chunk
from zhicore.vector_store import InMemoryVectorStore


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
