from pathlib import Path

from zhicore.pipeline import ingest_documents, load_store
from zhicore.rag import RAGEngine


def test_end_to_end_ingest_and_ask(tmp_path: Path) -> None:
    source = tmp_path / "intro.md"
    source.write_text(
        "# ZhiCore\n\nZhiCore supports RAG over personal knowledge documents.\n",
        encoding="utf-8",
    )

    index_path = tmp_path / "index.json"
    stats = ingest_documents(inputs=[str(source)], index_path=str(index_path))
    assert stats["documents"] == 1
    assert stats["indexed"] > 0

    store = load_store(str(index_path))
    result = RAGEngine(store).ask("What does ZhiCore support?", top_k=2)
    assert "RAG" in result.answer
    assert result.citations
