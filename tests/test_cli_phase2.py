import json
import sys
from pathlib import Path

from zhicore.cli import main


def _run_cli(monkeypatch, capsys, args: list[str]) -> str:
    monkeypatch.setattr(sys, "argv", ["zhicore", *args])
    main()
    return capsys.readouterr().out.strip()


def test_cli_phase2_build_and_subgraph(tmp_path: Path, monkeypatch, capsys) -> None:
    source = tmp_path / "kg.md"
    source.write_text("FastAPI is framework. RAG used in LearnOS.\n", encoding="utf-8")
    graph_path = tmp_path / "graph.json"
    index_path = tmp_path / "index.json"

    build_output = _run_cli(
        monkeypatch,
        capsys,
        [
            "kg-build",
            "--input",
            str(source),
            "--graph-path",
            str(graph_path),
            "--index-path",
            str(index_path),
        ],
    )
    build_payload = json.loads(build_output)
    assert build_payload["documents"] == 1
    assert build_payload["nodes"] > 0
    assert build_payload["edges"] > 0

    subgraph_output = _run_cli(
        monkeypatch,
        capsys,
        [
            "kg-subgraph",
            "--graph-path",
            str(graph_path),
            "--concept",
            "FastAPI",
            "--hops",
            "1",
        ],
    )
    subgraph_payload = json.loads(subgraph_output)
    assert subgraph_payload["nodes"]


def test_cli_phase2_graph_ask_json(tmp_path: Path, monkeypatch, capsys) -> None:
    source = tmp_path / "kg.md"
    source.write_text("FastAPI is framework. RAG used in LearnOS.\n", encoding="utf-8")
    graph_path = tmp_path / "graph.json"
    index_path = tmp_path / "index.json"

    _run_cli(
        monkeypatch,
        capsys,
        [
            "kg-build",
            "--input",
            str(source),
            "--graph-path",
            str(graph_path),
            "--index-path",
            str(index_path),
            "--no-incremental",
        ],
    )
    ask_output = _run_cli(
        monkeypatch,
        capsys,
        [
            "graph-ask",
            "--query",
            "What is FastAPI used in?",
            "--index-path",
            str(index_path),
            "--graph-path",
            str(graph_path),
            "--json",
        ],
    )
    ask_payload = json.loads(ask_output)
    assert "answer" in ask_payload
    assert ask_payload["text_evidence"]
    assert "graph_evidence" in ask_payload
