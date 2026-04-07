"""Phase 4 services: learning loop plan/session/submit/mastery APIs."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from threading import Lock
from typing import Any, Literal
from uuid import uuid4

from zhicore.kg import KnowledgeGraph

QuestionType = Literal["concept", "judgement", "cloze", "derivation"]

VALID_QUESTION_TYPES: set[str] = {"concept", "judgement", "cloze", "derivation"}


def _now() -> datetime:
    return datetime.now(tz=UTC).replace(microsecond=0)


def _now_iso() -> str:
    return _now().isoformat()


def _to_iso(value: datetime) -> str:
    return value.replace(microsecond=0).isoformat()


@dataclass(slots=True)
class ConceptState:
    concept_id: str
    concept_name: str
    mastery: float
    last_review_at: str | None
    next_review_at: str


@dataclass(slots=True)
class LearningQuestion:
    question_id: str
    type: QuestionType
    concept_id: str
    concept_name: str
    prompt: str


@dataclass(slots=True)
class LearningSession:
    session_id: str
    user_id: str
    graph_path: str
    questions: list[LearningQuestion]
    created_at: str


@dataclass(slots=True)
class PracticeRecord:
    question_id: str
    concept_id: str
    score: float
    error_type: str | None
    feedback: str
    timestamp: str


class LearningStateStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._states: dict[tuple[str, str], dict[str, ConceptState]] = {}
        self._sessions: dict[str, LearningSession] = {}
        self._records: dict[tuple[str, str], list[PracticeRecord]] = {}

    def ensure_states(self, user_id: str, graph_path: str) -> dict[str, ConceptState]:
        key = (user_id, graph_path)
        with self._lock:
            if key in self._states:
                return self._states[key]

            graph = KnowledgeGraph.load(graph_path)
            concept_nodes = [
                node for node in graph.nodes.values() if node.node_type in {"Concept", "Entity", "Formula"}
            ]
            if not concept_nodes:
                raise ValueError("No concepts found in graph. Build KG before learning.")

            states: dict[str, ConceptState] = {}
            for node in sorted(concept_nodes, key=lambda item: item.name.lower()):
                mastery = _initial_mastery(user_id=user_id, concept_id=node.node_id)
                next_review = _initial_next_review(mastery)
                states[node.node_id] = ConceptState(
                    concept_id=node.node_id,
                    concept_name=node.name,
                    mastery=mastery,
                    last_review_at=None,
                    next_review_at=_to_iso(next_review),
                )

            self._states[key] = states
            self._records[key] = []
            return states

    def get_session(self, session_id: str) -> LearningSession | None:
        with self._lock:
            return self._sessions.get(session_id)

    def save_session(self, session: LearningSession) -> None:
        with self._lock:
            self._sessions[session.session_id] = session

    def update_state_after_submit(
        self,
        user_id: str,
        graph_path: str,
        concept_scores: dict[str, float],
        records: list[PracticeRecord],
    ) -> None:
        key = (user_id, graph_path)
        with self._lock:
            states = self._states[key]
            now_iso = _now_iso()
            for concept_id, score in concept_scores.items():
                state = states[concept_id]
                new_mastery = round(max(0.0, min(1.0, state.mastery * 0.7 + score * 0.3)), 3)
                state.mastery = new_mastery
                state.last_review_at = now_iso
                state.next_review_at = _to_iso(_next_review_from_mastery(new_mastery))
            self._records[key].extend(records)

    def get_records(self, user_id: str, graph_path: str) -> list[PracticeRecord]:
        key = (user_id, graph_path)
        with self._lock:
            return list(self._records.get(key, []))


_STORE = LearningStateStore()


def generate_learning_plan(user_id: str, graph_path: str, top_k: int = 6) -> dict[str, Any]:
    states = _STORE.ensure_states(user_id=user_id, graph_path=graph_path)
    now = _now()

    ranked = sorted(
        states.values(),
        key=lambda item: (_is_due(item.next_review_at, now), -1.0 * (1 - item.mastery), item.concept_name.lower()),
        reverse=True,
    )

    concepts: list[dict[str, Any]] = []
    for state in ranked[: max(1, top_k)]:
        due = _is_due(state.next_review_at, now)
        concepts.append(
            {
                "concept_id": state.concept_id,
                "concept_name": state.concept_name,
                "mastery": state.mastery,
                "next_review_at": state.next_review_at,
                "reason": _plan_reason(state.mastery, due),
                "due": due,
            }
        )

    return {
        "user_id": user_id,
        "generated_at": _now_iso(),
        "recommended_concepts": concepts,
    }


def create_learning_session(
    user_id: str,
    graph_path: str,
    question_count: int,
    question_types: list[str],
) -> dict[str, Any]:
    if question_count < 1:
        raise ValueError("question_count must be >= 1")
    if not question_types:
        raise ValueError("question_types must not be empty")

    invalid = sorted(set(question_types) - VALID_QUESTION_TYPES)
    if invalid:
        raise ValueError(f"Invalid question_types: {', '.join(invalid)}")

    plan = generate_learning_plan(user_id=user_id, graph_path=graph_path, top_k=max(question_count, 6))
    concept_pool = plan["recommended_concepts"]
    if not concept_pool:
        raise ValueError("No concepts available for session generation")

    typed_questions: list[LearningQuestion] = []
    type_cycle = [question_type for question_type in question_types]
    for idx in range(question_count):
        question_type = type_cycle[idx % len(type_cycle)]
        concept = concept_pool[idx % len(concept_pool)]
        prompt = _build_question_prompt(question_type=question_type, concept_name=concept["concept_name"])
        typed_questions.append(
            LearningQuestion(
                question_id=f"q-{uuid4().hex[:10]}",
                type=question_type,  # type: ignore[arg-type]
                concept_id=concept["concept_id"],
                concept_name=concept["concept_name"],
                prompt=prompt,
            )
        )

    session = LearningSession(
        session_id=f"session-{uuid4().hex[:12]}",
        user_id=user_id,
        graph_path=graph_path,
        questions=typed_questions,
        created_at=_now_iso(),
    )
    _STORE.save_session(session)

    distribution: dict[str, int] = {}
    for item in typed_questions:
        distribution[item.type] = distribution.get(item.type, 0) + 1

    return {
        "session_id": session.session_id,
        "user_id": user_id,
        "question_count": len(typed_questions),
        "question_types": question_types,
        "distribution": distribution,
        "questions": [
            {
                "question_id": question.question_id,
                "prompt": question.prompt,
                "type": question.type,
                "concept_id": question.concept_id,
                "concept_name": question.concept_name,
            }
            for question in typed_questions
        ],
    }


def submit_learning_answers(
    session_id: str,
    user_id: str,
    answers: list[dict[str, str]],
) -> dict[str, Any]:
    session = _STORE.get_session(session_id)
    if session is None:
        raise KeyError(f"Learning session not found: {session_id}")
    if session.user_id != user_id:
        raise ValueError("session does not belong to user")

    answer_map = {
        str(item.get("question_id", "")).strip(): str(item.get("answer", "")).strip()
        for item in answers
    }
    required_ids = [question.question_id for question in session.questions]
    missing = [question_id for question_id in required_ids if not answer_map.get(question_id)]
    if missing:
        raise ValueError(f"Missing answers for question_ids: {', '.join(missing)}")

    records: list[PracticeRecord] = []
    concept_scores: dict[str, list[float]] = {}
    payload_records: list[dict[str, Any]] = []

    for question in session.questions:
        answer = answer_map[question.question_id]
        score, error_type, feedback = _score_answer(question=question, answer=answer)
        concept_scores.setdefault(question.concept_id, []).append(score)

        record = PracticeRecord(
            question_id=question.question_id,
            concept_id=question.concept_id,
            score=score,
            error_type=error_type,
            feedback=feedback,
            timestamp=_now_iso(),
        )
        records.append(record)
        payload_records.append(
            {
                "question_id": question.question_id,
                "concept_id": question.concept_id,
                "score": score,
                "error_type": error_type,
                "feedback": feedback,
            }
        )

    concept_avg_scores = {
        concept_id: round(sum(values) / len(values), 3) for concept_id, values in concept_scores.items()
    }
    _STORE.update_state_after_submit(
        user_id=user_id,
        graph_path=session.graph_path,
        concept_scores=concept_avg_scores,
        records=records,
    )

    average_score = round(sum(item.score for item in records) / len(records), 3)
    recommendation = _build_recommendation(user_id=user_id, graph_path=session.graph_path)

    return {
        "session_id": session_id,
        "average_score": average_score,
        "records": payload_records,
        "recommendation": recommendation,
    }


def get_mastery_map(user_id: str, graph_path: str) -> dict[str, Any]:
    states = _STORE.ensure_states(user_id=user_id, graph_path=graph_path)
    records = _STORE.get_records(user_id=user_id, graph_path=graph_path)
    now = _now()

    concepts = [
        {
            "concept_id": state.concept_id,
            "concept_name": state.concept_name,
            "mastery": state.mastery,
            "due": _is_due(state.next_review_at, now),
            "last_review_at": state.last_review_at,
            "next_review_at": state.next_review_at,
        }
        for state in sorted(states.values(), key=lambda item: (item.mastery, item.concept_name.lower()))
    ]

    due_count = sum(1 for item in concepts if item["due"])
    average_mastery = round(sum(state.mastery for state in states.values()) / len(states), 3)

    return {
        "summary": {
            "concept_count": len(concepts),
            "average_mastery": average_mastery,
            "due_count": due_count,
            "record_count": len(records),
        },
        "concepts": concepts,
    }


def _initial_mastery(user_id: str, concept_id: str) -> float:
    digest = hashlib.sha1(f"{user_id}|{concept_id}".encode("utf-8")).hexdigest()
    value = int(digest[:6], 16) / float(0xFFFFFF)
    return round(0.25 + value * 0.55, 3)


def _initial_next_review(mastery: float) -> datetime:
    now = _now()
    if mastery < 0.38:
        return now - timedelta(days=1)
    if mastery < 0.62:
        return now + timedelta(days=1)
    return now + timedelta(days=3)


def _next_review_from_mastery(mastery: float) -> datetime:
    now = _now()
    if mastery < 0.4:
        return now + timedelta(days=1)
    if mastery < 0.7:
        return now + timedelta(days=3)
    return now + timedelta(days=7)


def _is_due(next_review_at_iso: str, now: datetime) -> bool:
    try:
        return datetime.fromisoformat(next_review_at_iso) <= now
    except ValueError:
        return False


def _plan_reason(mastery: float, due: bool) -> str:
    if due and mastery < 0.45:
        return "due_and_low_mastery"
    if due:
        return "due_for_review"
    if mastery < 0.6:
        return "low_mastery"
    return "reinforcement"


def _build_question_prompt(question_type: str, concept_name: str) -> str:
    if question_type == "concept":
        return f"请用一句话解释概念：{concept_name}。"
    if question_type == "judgement":
        return f"判断正误并说明理由：{concept_name} 与检索增强流程直接相关。"
    if question_type == "cloze":
        return f"填空：在学习闭环中，{concept_name} 主要用于 ____。"
    return f"推导题：结合 {concept_name} 给出从问题到结论的两步推理。"


def _score_answer(question: LearningQuestion, answer: str) -> tuple[float, str | None, str]:
    normalized = answer.strip().lower()
    if not normalized:
        return 0.0, "missing_answer", "答案为空，请先完成作答。"

    score = 0.2
    error_type: str | None = None

    concept_token = question.concept_name.lower()
    if concept_token and concept_token in normalized:
        score += 0.35

    if len(normalized) >= 12:
        score += 0.25

    if question.type == "judgement":
        if any(flag in normalized for flag in ["是", "否", "true", "false", "对", "错"]):
            score += 0.2
        else:
            error_type = "format_error"
    elif question.type == "cloze":
        if "____" not in normalized and len(normalized.split()) >= 1:
            score += 0.2
        else:
            error_type = "incomplete_answer"
    elif question.type == "derivation":
        if any(marker in normalized for marker in ["因此", "所以", "because", "then", "步骤"]):
            score += 0.2
        else:
            error_type = "reasoning_gap"
    else:
        if len(normalized) >= 24:
            score += 0.15

    final_score = round(max(0.0, min(1.0, score)), 3)
    if final_score < 0.45 and error_type is None:
        error_type = "concept_miss"

    if final_score >= 0.8:
        feedback = "回答较完整，概念与表达都较清晰。"
    elif final_score >= 0.55:
        feedback = "回答基本正确，但仍可补充关键细节。"
    else:
        feedback = "回答较弱，建议回看概念定义与示例后再作答。"

    return final_score, error_type, feedback


def _build_recommendation(user_id: str, graph_path: str) -> str:
    mastery = get_mastery_map(user_id=user_id, graph_path=graph_path)
    weakest = mastery["concepts"][:3]
    if not weakest:
        return "继续保持当前学习节奏。"
    names = ", ".join(item["concept_name"] for item in weakest)
    return f"建议优先复习：{names}。"
