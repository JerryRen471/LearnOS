import json
import sys
from pathlib import Path

import pytest

from zhicore.cli import main
from zhicore.phase2 import build_or_update_kg


def _run_cli_json(args: list[str], monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> dict:
    monkeypatch.setattr(sys, "argv", ["zhicore", *args])
    main()
    output = capsys.readouterr().out.strip()
    return json.loads(output)


def test_cli_phase4_end_to_end(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    source = tmp_path / "cli-phase4.md"
    source.write_text(
        "RAG is retrieval augmented generation.\nFastAPI used in service layer.\n",
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

    user_id = "u-cli-phase4"
    plan = _run_cli_json(
        [
            "learning-plan",
            "--user-id",
            user_id,
            "--graph-path",
            str(graph_path),
            "--max-concepts",
            "3",
        ],
        monkeypatch,
        capsys,
    )
    assert plan["user_id"] == user_id
    assert plan["recommended_concepts"]

    session = _run_cli_json(
        [
            "learning-session",
            "--user-id",
            user_id,
            "--graph-path",
            str(graph_path),
            "--question-count",
            "2",
            "--question-types",
            "concept",
            "judgement",
        ],
        monkeypatch,
        capsys,
    )
    assert session["question_count"] == 2
    assert len(session["questions"]) == 2

    answers = [
        {"question_id": item["question_id"], "answer": item["reference_answer"]}
        for item in session["questions"]
    ]
    submit = _run_cli_json(
        [
            "learning-submit",
            "--user-id",
            user_id,
            "--answers-json",
            json.dumps(answers, ensure_ascii=False),
        ],
        monkeypatch,
        capsys,
    )
    assert submit["user_id"] == user_id
    assert len(submit["records"]) == 2

    mastery_map = _run_cli_json(
        ["learning-mastery-map", "--user-id", user_id],
        monkeypatch,
        capsys,
    )
    assert mastery_map["summary"]["concept_count"] >= 1
    assert mastery_map["summary"]["record_count"] == 2


def test_cli_learning_submit_rejects_invalid_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "zhicore",
            "learning-submit",
            "--user-id",
            "u1",
            "--answers-json",
            "{bad json",
        ],
    )
    with pytest.raises(ValueError):
        main()
