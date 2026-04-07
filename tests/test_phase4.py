from pathlib import Path

import pytest

from zhicore.phase2 import build_or_update_kg
from zhicore.phase4 import (
    create_learning_plan,
    create_learning_session,
    get_learning_mastery_map,
    submit_learning_answers,
)


def test_phase4_learning_loop_end_to_end(tmp_path: Path) -> None:
    source = tmp_path / "learning.md"
    source.write_text(
        "RAG is retrieval augmented generation.\n"
        "FastAPI used in service layer.\n"
        "KnowledgeGraph used in GraphRAG.\n",
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

    user_id = "u-phase4"
    plan = create_learning_plan(user_id=user_id, graph_path=str(graph_path), max_concepts=3)
    assert plan["recommended_concepts"]
    assert plan["strategy"] == "sm2_baseline"

    session = create_learning_session(
        user_id=user_id,
        graph_path=str(graph_path),
        question_count=4,
        question_types=["concept", "judgement", "cloze", "derivation"],
    )
    assert session["question_count"] == 4
    assert len(session["questions"]) == 4

    answers = []
    for idx, question in enumerate(session["questions"]):
        if idx % 2 == 0:
            content = question["reference_answer"]
        else:
            content = "不太清楚。"
        answers.append({"question_id": question["question_id"], "answer": content})

    submit = submit_learning_answers(user_id=user_id, answers=answers)
    assert submit["records"]
    assert submit["average_score"] >= 0
    assert any(item["error_type"] != "none" for item in submit["records"])
    assert all(item["next_review_at"] for item in submit["records"])

    mastery_map = get_learning_mastery_map(user_id=user_id)
    assert mastery_map["summary"]["concept_count"] > 0
    assert mastery_map["summary"]["record_count"] == 4
    assert mastery_map["concepts"][0]["total_attempts"] >= 1
    assert mastery_map["concepts"][0]["next_review_at"] is not None


def test_phase4_submit_requires_existing_question(tmp_path: Path) -> None:
    source = tmp_path / "minimal.md"
    source.write_text("GraphRAG is method.", encoding="utf-8")
    graph_path = tmp_path / "graph.json"
    index_path = tmp_path / "index.json"
    build_or_update_kg(
        inputs=[str(source)],
        graph_path=str(graph_path),
        index_path=str(index_path),
        incremental=False,
    )

    create_learning_session(user_id="u2", graph_path=str(graph_path), question_count=1)
    with pytest.raises(KeyError):
        submit_learning_answers(
            user_id="u2",
            answers=[{"question_id": "q-missing", "answer": "answer"}],
        )

