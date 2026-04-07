from pathlib import Path

import pytest

from zhicore.phase2 import build_or_update_kg
from zhicore.phase4 import create_learning_session, generate_learning_plan, get_mastery_map, submit_learning_answers


def _prepare_graph(tmp_path: Path) -> tuple[str, str]:
    source = tmp_path / "learning.md"
    source.write_text(
        """
        FastAPI is API framework.
        GraphRAG used in LearnOS.
        LearnOS is knowledge system.
        """,
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
    return str(graph_path), str(index_path)


def test_learning_flow_plan_session_submit_mastery(tmp_path: Path) -> None:
    graph_path, _ = _prepare_graph(tmp_path)

    plan = generate_learning_plan(user_id="u1", graph_path=graph_path, top_k=3)
    assert plan["recommended_concepts"]
    concept = plan["recommended_concepts"][0]
    assert "mastery" in concept
    assert "next_review_at" in concept
    assert "reason" in concept

    session = create_learning_session(
        user_id="u1",
        graph_path=graph_path,
        question_count=4,
        question_types=["concept", "judgement"],
    )
    assert session["question_count"] == 4
    assert session["distribution"]["concept"] == 2
    assert session["distribution"]["judgement"] == 2

    answers = [
        {"question_id": question["question_id"], "answer": f"回答 {question['concept_name']} 是关键概念"}
        for question in session["questions"]
    ]
    submit = submit_learning_answers(
        session_id=session["session_id"],
        user_id="u1",
        answers=answers,
    )
    assert submit["average_score"] >= 0
    assert len(submit["records"]) == 4
    assert submit["recommendation"]

    mastery = get_mastery_map(user_id="u1", graph_path=graph_path)
    assert mastery["summary"]["concept_count"] > 0
    assert mastery["summary"]["record_count"] == 4
    assert mastery["concepts"]


def test_learning_session_invalid_type_rejected(tmp_path: Path) -> None:
    graph_path, _ = _prepare_graph(tmp_path)

    with pytest.raises(ValueError, match="Invalid question_types"):
        create_learning_session(
            user_id="u2",
            graph_path=graph_path,
            question_count=2,
            question_types=["concept", "invalid"],
        )


def test_learning_submit_requires_complete_answers(tmp_path: Path) -> None:
    graph_path, _ = _prepare_graph(tmp_path)

    session = create_learning_session(
        user_id="u3",
        graph_path=graph_path,
        question_count=2,
        question_types=["concept"],
    )
    first_question = session["questions"][0]

    with pytest.raises(ValueError, match="Missing answers"):
        submit_learning_answers(
            session_id=session["session_id"],
            user_id="u3",
            answers=[{"question_id": first_question["question_id"], "answer": "only one"}],
        )
