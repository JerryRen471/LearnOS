"""Phase 4 services: learning loop with planning, practice, and mastery tracking."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from threading import Lock
from typing import Any
from uuid import uuid4

from zhicore.kg import KnowledgeGraph

QUESTION_TYPES = {"concept", "judgement", "cloze", "derivation"}


def _now() -> datetime:
    return datetime.now(tz=UTC).replace(microsecond=0)


def _now_iso() -> str:
    return _now().isoformat()


@dataclass(slots=True)
class ConceptState:
    user_id: str
    concept_id: str
    concept_name: str
    mastery: float = 0.3
    last_review_at: str | None = None
    next_review_at: str | None = None
    repetition: int = 0
    interval_days: int = 0
    ease_factor: float = 2.5
    total_attempts: int = 0
    error_count: int = 0


@dataclass(slots=True)
class PracticeQuestion:
    question_id: str
    user_id: str
    concept_id: str
    concept_name: str
    question_type: str
    prompt: str
    reference_answer: str
    rubric: str
    created_at: str


@dataclass(slots=True)
class PracticeRecord:
    record_id: str
    question_id: str
    user_id: str
    concept_id: str
    concept_name: str
    question_type: str
    user_answer: str
    score: float
    error_type: str
    feedback: str
    timestamp: str


class LearningStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._states: dict[str, dict[str, ConceptState]] = {}
        self._questions: dict[str, PracticeQuestion] = {}
        self._records: list[PracticeRecord] = []

    def get_state(self, user_id: str, concept_id: str) -> ConceptState | None:
        with self._lock:
            return self._states.get(user_id, {}).get(concept_id)

    def upsert_state(self, state: ConceptState) -> None:
        with self._lock:
            bucket = self._states.setdefault(state.user_id, {})
            bucket[state.concept_id] = state

    def list_states(self, user_id: str) -> list[ConceptState]:
        with self._lock:
            return list(self._states.get(user_id, {}).values())

    def add_question(self, question: PracticeQuestion) -> None:
        with self._lock:
            self._questions[question.question_id] = question

    def get_question(self, question_id: str) -> PracticeQuestion | None:
        with self._lock:
            return self._questions.get(question_id)

    def add_record(self, record: PracticeRecord) -> None:
        with self._lock:
            self._records.append(record)

    def list_records(self, user_id: str) -> list[PracticeRecord]:
        with self._lock:
            return [item for item in self._records if item.user_id == user_id]


_LEARNING_STORE = LearningStore()


def create_learning_plan(
    user_id: str,
    graph_path: str,
    max_concepts: int = 8,
) -> dict[str, Any]:
    if not user_id.strip():
        raise ValueError("user_id must not be empty.")
    if max_concepts <= 0:
        raise ValueError("max_concepts must be > 0")

    graph = KnowledgeGraph.load(graph_path)
    concept_nodes = [node for node in graph.nodes.values() if node.node_type in {"Concept", "Entity", "Formula"}]
    if not concept_nodes:
        raise ValueError("No learnable concept nodes found in graph.")

    now = _now()
    ranked: list[tuple[float, int, str, str, str | None]] = []
    for node in concept_nodes:
        state = _LEARNING_STORE.get_state(user_id=user_id, concept_id=node.node_id)
        mastery = state.mastery if state is not None else 0.3
        next_review = state.next_review_at if state is not None else None
        due_flag = 1
        if next_review:
            due_flag = 1 if _parse_time(next_review) <= now else 0
        ranked.append((mastery, -due_flag, node.node_id, node.name, next_review))

    ranked.sort(key=lambda item: (item[0], item[1], item[3].lower()))
    selected = ranked[:max_concepts]
    concepts: list[dict[str, Any]] = []
    for mastery, _, concept_id, concept_name, next_review in selected:
        state = _LEARNING_STORE.get_state(user_id=user_id, concept_id=concept_id)
        if state is None:
            state = ConceptState(
                user_id=user_id,
                concept_id=concept_id,
                concept_name=concept_name,
                mastery=mastery,
                next_review_at=_now_iso(),
            )
            _LEARNING_STORE.upsert_state(state)
        reason = _plan_reason(mastery=state.mastery, next_review_at=state.next_review_at)
        concepts.append(
            {
                "concept_id": concept_id,
                "concept_name": concept_name,
                "mastery": round(state.mastery, 3),
                "next_review_at": state.next_review_at,
                "reason": reason,
            }
        )

    return {
        "user_id": user_id,
        "generated_at": _now_iso(),
        "strategy": "sm2_baseline",
        "recommended_concepts": concepts,
    }


def create_learning_session(
    user_id: str,
    graph_path: str,
    question_count: int = 6,
    question_types: list[str] | None = None,
) -> dict[str, Any]:
    if question_count <= 0:
        raise ValueError("question_count must be > 0")
    resolved_types = question_types or ["concept", "judgement", "cloze", "derivation"]
    for item in resolved_types:
        if item not in QUESTION_TYPES:
            raise ValueError(f"Unsupported question type: {item}")

    plan = create_learning_plan(user_id=user_id, graph_path=graph_path, max_concepts=max(1, question_count))
    if not plan["recommended_concepts"]:
        raise ValueError("No concepts available for session generation.")

    questions: list[dict[str, Any]] = []
    concepts = plan["recommended_concepts"]
    for idx in range(question_count):
        concept = concepts[idx % len(concepts)]
        question_type = resolved_types[idx % len(resolved_types)]
        question_id = f"q-{uuid4().hex[:12]}"
        prompt, reference, rubric = _make_question(
            concept_name=str(concept["concept_name"]),
            question_type=question_type,
        )
        question = PracticeQuestion(
            question_id=question_id,
            user_id=user_id,
            concept_id=str(concept["concept_id"]),
            concept_name=str(concept["concept_name"]),
            question_type=question_type,
            prompt=prompt,
            reference_answer=reference,
            rubric=rubric,
            created_at=_now_iso(),
        )
        _LEARNING_STORE.add_question(question)
        questions.append(asdict(question))

    return {
        "user_id": user_id,
        "generated_at": _now_iso(),
        "question_count": len(questions),
        "questions": questions,
    }


def submit_learning_answers(user_id: str, answers: list[dict[str, str]]) -> dict[str, Any]:
    if not answers:
        raise ValueError("answers must not be empty.")

    reviewed: list[dict[str, Any]] = []
    total_score = 0.0
    for item in answers:
        question_id = str(item.get("question_id", "")).strip()
        user_answer = str(item.get("answer", "")).strip()
        if not question_id:
            raise ValueError("question_id is required in every answer item.")

        question = _LEARNING_STORE.get_question(question_id)
        if question is None or question.user_id != user_id:
            raise KeyError(f"Question not found for user: {question_id}")

        score = _evaluate_answer(reference=question.reference_answer, answer=user_answer)
        error_type = _classify_error(score=score, question_type=question.question_type)
        feedback = _build_feedback(error_type=error_type, concept_name=question.concept_name)

        state = _LEARNING_STORE.get_state(user_id=user_id, concept_id=question.concept_id)
        if state is None:
            state = ConceptState(
                user_id=user_id,
                concept_id=question.concept_id,
                concept_name=question.concept_name,
            )
        _update_state_with_sm2(state=state, score=score)
        _LEARNING_STORE.upsert_state(state)

        record = PracticeRecord(
            record_id=f"r-{uuid4().hex[:12]}",
            question_id=question.question_id,
            user_id=user_id,
            concept_id=question.concept_id,
            concept_name=question.concept_name,
            question_type=question.question_type,
            user_answer=user_answer,
            score=score,
            error_type=error_type,
            feedback=feedback,
            timestamp=_now_iso(),
        )
        _LEARNING_STORE.add_record(record)

        reviewed.append(
            {
                "question_id": question.question_id,
                "concept_id": question.concept_id,
                "concept_name": question.concept_name,
                "question_type": question.question_type,
                "score": round(score, 3),
                "error_type": error_type,
                "feedback": feedback,
                "mastery": round(state.mastery, 3),
                "next_review_at": state.next_review_at,
            }
        )
        total_score += score

    average_score = total_score / len(reviewed)
    return {
        "user_id": user_id,
        "submitted_at": _now_iso(),
        "average_score": round(average_score, 3),
        "records": reviewed,
        "recommendation": _next_action(average_score=average_score),
    }


def get_learning_mastery_map(user_id: str) -> dict[str, Any]:
    states = _LEARNING_STORE.list_states(user_id=user_id)
    now = _now()
    concepts = sorted(states, key=lambda item: (item.mastery, item.concept_name.lower()))
    concept_payload = [
        {
            "concept_id": item.concept_id,
            "concept_name": item.concept_name,
            "mastery": round(item.mastery, 3),
            "last_review_at": item.last_review_at,
            "next_review_at": item.next_review_at,
            "repetition": item.repetition,
            "interval_days": item.interval_days,
            "ease_factor": round(item.ease_factor, 3),
            "total_attempts": item.total_attempts,
            "error_count": item.error_count,
        }
        for item in concepts
    ]
    due_count = 0
    for item in concepts:
        if item.next_review_at is None:
            due_count += 1
            continue
        if _parse_time(item.next_review_at) <= now:
            due_count += 1

    average = sum(item.mastery for item in concepts) / len(concepts) if concepts else 0.0
    return {
        "user_id": user_id,
        "summary": {
            "concept_count": len(concepts),
            "average_mastery": round(average, 3),
            "due_count": due_count,
            "record_count": len(_LEARNING_STORE.list_records(user_id=user_id)),
        },
        "concepts": concept_payload,
    }


def _make_question(concept_name: str, question_type: str) -> tuple[str, str, str]:
    if question_type == "concept":
        return (
            f"请解释概念「{concept_name}」并给出一个应用场景。",
            f"{concept_name} 的定义应清晰，并至少给出一个真实或学习场景中的应用。",
            "定义准确 + 场景贴合。",
        )
    if question_type == "judgement":
        return (
            f"判断题：{concept_name} 只适用于单一场景。请回答“正确/错误”并说明理由。",
            f"错误。{concept_name} 通常可在多个相关任务中复用，理由需与其核心作用有关。",
            "判断结论正确 + 理由与概念作用一致。",
        )
    if question_type == "cloze":
        return (
            f"填空题：在知识系统中，{concept_name} 的核心作用是 ________。",
            f"{concept_name} 的核心作用是组织、解释或连接相关知识。",
            "填空语义正确，能表达核心作用。",
        )
    if question_type == "derivation":
        return (
            f"推导题：给定学习目标，说明如何利用 {concept_name} 逐步得到可执行的学习策略。",
            f"先明确目标，再用 {concept_name} 拆解关键知识点，最后形成练习与复习计划。",
            "步骤完整、逻辑连贯。",
        )
    raise ValueError(f"Unsupported question type: {question_type}")


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9\u4e00-\u9fff]+", text.lower())


def _evaluate_answer(reference: str, answer: str) -> float:
    if not answer.strip():
        return 0.0
    ref_tokens = set(_tokenize(reference))
    ans_tokens = _tokenize(answer)
    if not ref_tokens:
        return 1.0 if ans_tokens else 0.0
    overlap = len(ref_tokens.intersection(ans_tokens)) / len(ref_tokens)
    length_factor = min(1.0, len(ans_tokens) / max(1, len(ref_tokens)))
    return max(0.0, min(1.0, overlap * 0.8 + length_factor * 0.2))


def _classify_error(score: float, question_type: str) -> str:
    if score >= 0.8:
        return "none"
    if score >= 0.5:
        return "表达不完整"
    if question_type == "derivation":
        return "推理错误"
    return "概念错误"


def _build_feedback(error_type: str, concept_name: str) -> str:
    if error_type == "none":
        return f"{concept_name} 掌握较好，可进入间隔复习。"
    if error_type == "表达不完整":
        return f"{concept_name} 的关键点已覆盖，但表达不完整，建议补充术语和例子。"
    if error_type == "推理错误":
        return f"{concept_name} 的推理链不完整，建议按“目标-步骤-结果”重新组织答案。"
    return f"{concept_name} 的核心概念有偏差，建议先复习定义与基础示例。"


def _quality_from_score(score: float) -> int:
    if score >= 0.9:
        return 5
    if score >= 0.75:
        return 4
    if score >= 0.6:
        return 3
    if score >= 0.4:
        return 2
    if score >= 0.2:
        return 1
    return 0


def _update_state_with_sm2(state: ConceptState, score: float) -> None:
    quality = _quality_from_score(score)
    if quality < 3:
        state.repetition = 0
        state.interval_days = 1
    else:
        if state.repetition == 0:
            state.repetition = 1
            state.interval_days = 1
        elif state.repetition == 1:
            state.repetition = 2
            state.interval_days = 6
        else:
            state.repetition += 1
            state.interval_days = max(1, int(round(state.interval_days * state.ease_factor)))

    delta = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    state.ease_factor = max(1.3, state.ease_factor + delta)
    state.last_review_at = _now_iso()
    state.next_review_at = (_now() + timedelta(days=state.interval_days or 1)).isoformat()
    state.mastery = max(0.0, min(1.0, state.mastery * 0.65 + score * 0.35))
    state.total_attempts += 1
    if score < 0.6:
        state.error_count += 1


def _next_action(average_score: float) -> str:
    if average_score >= 0.8:
        return "建议进入下一主题，并保留当前主题间隔复习。"
    if average_score >= 0.5:
        return "建议再完成一轮同主题练习，重点补齐表达与细节。"
    return "建议立即复习基础概念后再开始下一轮练习。"


def _plan_reason(mastery: float, next_review_at: str | None) -> str:
    if mastery < 0.4:
        return "薄弱概念，优先复习"
    if next_review_at is None:
        return "尚无复习记录，建议尽快练习"
    if _parse_time(next_review_at) <= _now():
        return "已到复习时间窗口"
    return "建议巩固以提升掌握度"


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)

