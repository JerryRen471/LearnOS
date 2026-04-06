import json
from pathlib import Path

from fastapi.testclient import TestClient

from zhicore.api import app
from zhicore.phase2 import build_or_update_kg
from zhicore.phase4 import (
    generate_learning_plan,
    generate_learning_session,
    get_mastery_map,
    submit_learning_session,
)


def test_learning_loop_end_to_end(tmp_path: Path) -> None:
    source = tmp_path / "learning.md"
    source.write_text(
        (
            "FastAPI is framework.\n"
            "RAG used in LearnOS.\n"
            "Neo4j is graph database.\n"
            "GraphRAG derived from RAG.\n"
        ),
        encoding="utf-8",
    )
    graph_path = tmp_path / "graph.json"
    index_path = tmp_path / "index.json"
    state_path = tmp_path / "learning_state.json"

    build_or_update_kg(
        inputs=[str(source)],
        graph_path=str(graph_path),
        index_path=str(index_path),
        incremental=False,
    )

    plan = generate_learning_plan(
        user_id="u-001",
        graph_path=str(graph_path),
        state_path=str(state_path),
        max_concepts=5,
    )
    assert plan["focus_concepts"]

    session = generate_learning_session(
        user_id="u-001",
        graph_path=str(graph_path),
        state_path=str(state_path),
        question_count=4,
    )
    assert len(session["questions"]) == 4
    assert all("reference_answer" not in item for item in session["questions"])

    state = json.loads(state_path.read_text(encoding="utf-8"))
    session_id = session["session_id"]
    stored_questions = state["sessions"][session_id]["questions"]
    answers = [
        {"question_id": stored_questions[0]["question_id"], "answer": stored_questions[0]["reference_answer"]},
        {"question_id": stored_questions[1]["question_id"], "answer": ""},
    ]
    submit_result = submit_learning_session(
        user_id="u-001",
        session_id=session_id,
        answers=answers,
        graph_path=str(graph_path),
        state_path=str(state_path),
    )
    assert submit_result["results"]
    assert 0.0 <= submit_result["overall_score"] <= 1.0
    assert len(submit_result["next_recommendations"]) <= 3

    mastery_map = get_mastery_map(
        user_id="u-001",
        graph_path=str(graph_path),
        state_path=str(state_path),
    )
    assert mastery_map["stats"]["practice_count"] >= 4
    assert mastery_map["concepts"]


def test_learning_api_endpoints(tmp_path: Path) -> None:
    source = tmp_path / "api_learning.md"
    source.write_text("FastAPI used in backend services.\nGraphRAG related to RAG.\n", encoding="utf-8")
    graph_path = tmp_path / "graph_api.json"
    index_path = tmp_path / "index_api.json"
    state_path = tmp_path / "learning_api_state.json"
    build_or_update_kg(
        inputs=[str(source)],
        graph_path=str(graph_path),
        index_path=str(index_path),
        incremental=False,
    )

    client = TestClient(app)
    plan_resp = client.post(
        "/learning/plan",
        json={
            "user_id": "u-api",
            "graph_path": str(graph_path),
            "state_path": str(state_path),
            "max_concepts": 3,
        },
    )
    assert plan_resp.status_code == 200
    assert plan_resp.json()["focus_concepts"]

    session_resp = client.post(
        "/learning/session",
        json={
            "user_id": "u-api",
            "graph_path": str(graph_path),
            "state_path": str(state_path),
            "question_count": 3,
        },
    )
    assert session_resp.status_code == 200
    session_payload = session_resp.json()
    session_id = session_payload["session_id"]
    question_ids = [item["question_id"] for item in session_payload["questions"]]

    submit_resp = client.post(
        "/learning/submit",
        json={
            "user_id": "u-api",
            "session_id": session_id,
            "graph_path": str(graph_path),
            "state_path": str(state_path),
            "answers": [{"question_id": question_ids[0], "answer": "test"}],
        },
    )
    assert submit_resp.status_code == 200
    assert submit_resp.json()["results"]

    mastery_resp = client.get(
        "/learning/mastery-map",
        params={
            "user_id": "u-api",
            "graph_path": str(graph_path),
            "state_path": str(state_path),
        },
    )
    assert mastery_resp.status_code == 200
    assert mastery_resp.json()["concepts"]
