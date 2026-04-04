from pathlib import Path

from zhicore.phase2 import build_or_update_kg, query_graph_rag, query_subgraph


def test_build_and_query_graph_rag(tmp_path: Path) -> None:
    source = tmp_path / "kg.md"
    source.write_text(
        "FastAPI is framework.\nRAG used in LearnOS.\nE = mc2\n",
        encoding="utf-8",
    )
    graph_path = tmp_path / "graph.json"
    index_path = tmp_path / "index.json"

    stats = build_or_update_kg(
        inputs=[str(source)],
        graph_path=str(graph_path),
        index_path=str(index_path),
        incremental=False,
    )
    assert stats["documents"] == 1
    assert stats["chunks"] >= 1
    assert stats["nodes"] > 0
    assert stats["edges"] > 0

    result = query_graph_rag(
        query="What is FastAPI used in?",
        index_path=str(index_path),
        graph_path=str(graph_path),
        top_k=2,
        graph_hops=1,
    )
    assert result.text_evidence
    assert "文本证据" in result.answer

    subgraph = query_subgraph(
        graph_path=str(graph_path),
        concept="FastAPI",
        hops=1,
    )
    assert subgraph["nodes"]


def test_build_incremental_update(tmp_path: Path) -> None:
    graph_path = tmp_path / "graph.json"
    index_path = tmp_path / "index.json"

    a = tmp_path / "a.md"
    a.write_text("GraphRAG is method.\n", encoding="utf-8")
    b = tmp_path / "b.md"
    b.write_text("Neo4j used in GraphRAG.\n", encoding="utf-8")

    first = build_or_update_kg(
        inputs=[str(a)],
        graph_path=str(graph_path),
        index_path=str(index_path),
        incremental=True,
    )
    second = build_or_update_kg(
        inputs=[str(b)],
        graph_path=str(graph_path),
        index_path=str(index_path),
        incremental=True,
    )

    assert second["nodes"] >= first["nodes"]
