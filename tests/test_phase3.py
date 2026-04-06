from pathlib import Path

from zhicore.phase2 import build_or_update_kg
from zhicore.phase3 import get_agent_run, retry_agent_run, run_agent_query
from zhicore.pipeline import ingest_documents


def test_agent_orchestration_with_trace_and_retry(tmp_path: Path) -> None:
    source = tmp_path / "agent.md"
    source.write_text(
        "FastAPI is framework.\nGraphRAG used in LearnOS.\nFastAPI used in LearnOS.\n",
        encoding="utf-8",
    )
    graph_path = tmp_path / "graph.json"
    index_path = tmp_path / "index.json"
    build_or_update_kg(
        inputs=[str(source)],
        graph_path=str(graph_path),
        index_path=str(index_path),
        incremental=False,
    )

    run = run_agent_query(
        query="FastAPI 和 LearnOS 的关系是什么？",
        index_path=str(index_path),
        graph_path=str(graph_path),
        top_k=2,
    )
    assert run["status"] == "succeeded"
    assert run["run_id"].startswith("run-")
    assert run["plan"]["query_type"] in {"关系推理", "定义解释", "综合问答"}
    assert len(run["steps"]) >= 3
    assert run["answer"]
    assert run["evaluation"]["confidence"] > 0

    loaded = get_agent_run(run_id=run["run_id"])
    assert loaded["run_id"] == run["run_id"]
    assert loaded["steps"]

    retried = retry_agent_run(run_id=run["run_id"])
    assert retried["status"] == "succeeded"
    assert retried["retry_of"] == run["run_id"]
    assert retried["run_id"] != run["run_id"]


def test_agent_orchestration_fallback_to_rag_when_graph_missing(tmp_path: Path) -> None:
    source = tmp_path / "fallback.md"
    source.write_text(
        "RAG combines retrieval and generation.\nFastAPI supports API building.\n",
        encoding="utf-8",
    )
    index_path = tmp_path / "index.json"
    ingest_documents(inputs=[str(source)], index_path=str(index_path))
    missing_graph_path = tmp_path / "missing-graph.json"

    run = run_agent_query(
        query="RAG 和 FastAPI 的关系是什么？",
        index_path=str(index_path),
        graph_path=str(missing_graph_path),
        top_k=2,
    )
    assert run["status"] == "succeeded"
    assert run["fallback"] is not None
    assert run["fallback"]["triggered"] is True
    assert run["fallback"]["mode"] == "rag"
    assert run["answer"]
    assert run["text_evidence"]
