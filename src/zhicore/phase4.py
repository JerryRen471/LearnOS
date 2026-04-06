"""Phase 4 learning loop services: plan, practice, submit, and mastery map."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from zhicore.kg import KnowledgeGraph

_LEARNING_NODE_TYPES = {"Concept", "Entity"}
_QUESTION_TYPES = ("concept", "true_false", "fill_blank", "derive")
_TRUE_TOKENS = {"对", "正确", "true", "yes", "是"}
_FALSE_TOKENS = {"错", "错误", "false", "no", "否"}


def generate_learning_plan(
    user_id: str,
    graph_path: str,
    state_path: str = ".zhicore/learning_state.json",
    max_concepts: int = 6,
) -> dict[str, Any]:
    """Build a personalized plan from weak and due concepts."""
    if max_concepts <= 0:
        raise ValueError("max_concepts must be > 0")

    graph = KnowledgeGraph.load(graph_path)
    state = _load_state(state_path)
    now = _utcnow()
    user_state = _ensure_user_state(state, user_id=user_id)
    _seed_concept_states(user_state=user_state, graph=graph, now=now)
    _save_state(state_path, state)

    candidates = _plan_candidates(user_state=user_state, graph=graph, now=now)
    selected = candidates[:max_concepts]
    avg_mastery = (
        sum(item["mastery"] for item in candidates) / len(candidates)
        if candidates
        else 0.0
    )
    return {
        "user_id": user_id,
        "generated_at": _isoformat(now),
        "focus_concepts": selected,
        "summary": {
            "tracked_concepts": len(candidates),
            "due_concepts": sum(1 for item in candidates if item["is_due"]),
            "average_mastery": round(avg_mastery, 4),
        },
    }


def generate_learning_session(
    user_id: str,
    graph_path: str,
    state_path: str = ".zhicore/learning_state.json",
    question_count: int = 6,
) -> dict[str, Any]:
    """Generate a practice session from current learning plan."""
    if question_count <= 0:
        raise ValueError("question_count must be > 0")

    graph = KnowledgeGraph.load(graph_path)
    state = _load_state(state_path)
    now = _utcnow()
    user_state = _ensure_user_state(state, user_id=user_id)
    _seed_concept_states(user_state=user_state, graph=graph, now=now)

    candidates = _plan_candidates(user_state=user_state, graph=graph, now=now)
    concept_ids = [item["concept_id"] for item in candidates]
    if not concept_ids:
        raise ValueError("No concept nodes available. Build KG first.")

    session_id = _new_session_id(user_id=user_id, now=now, existing=len(state["sessions"]))
    selected_concepts = [concept_ids[idx % len(concept_ids)] for idx in range(question_count)]

    questions: list[dict[str, Any]] = []
    for idx, concept_id in enumerate(selected_concepts, start=1):
        question_type = _QUESTION_TYPES[(idx - 1) % len(_QUESTION_TYPES)]
        question = _build_question(
            graph=graph,
            concept_id=concept_id,
            question_type=question_type,
            session_id=session_id,
            index=idx,
        )
        questions.append(question)

    state["sessions"][session_id] = {
        "user_id": user_id,
        "created_at": _isoformat(now),
        "status": "open",
        "questions": questions,
    }
    _save_state(state_path, state)
    return {
        "session_id": session_id,
        "user_id": user_id,
        "generated_at": _isoformat(now),
        "questions": [_public_question(item) for item in questions],
    }


def submit_learning_session(
    user_id: str,
    session_id: str,
    answers: list[dict[str, str]],
    graph_path: str,
    state_path: str = ".zhicore/learning_state.json",
) -> dict[str, Any]:
    """Score answers, update mastery using SM-2 baseline, and return feedback."""
    graph = KnowledgeGraph.load(graph_path)
    state = _load_state(state_path)
    now = _utcnow()
    user_state = _ensure_user_state(state, user_id=user_id)
    _seed_concept_states(user_state=user_state, graph=graph, now=now)

    session = state["sessions"].get(session_id)
    if session is None:
        raise ValueError(f"Unknown session_id: {session_id}")
    if session.get("user_id") != user_id:
        raise ValueError("session_id does not belong to user_id.")

    answer_map = {
        str(item.get("question_id", "")).strip(): str(item.get("answer", "")).strip()
        for item in answers
    }
    results: list[dict[str, Any]] = []
    scores: list[float] = []
    for question in session.get("questions", []):
        question_id = str(question["question_id"])
        response = answer_map.get(question_id, "")
        score = _score_answer(
            response=response,
            reference_answer=str(question.get("reference_answer", "")),
            question_type=str(question.get("question_type", "concept")),
            rubric=[str(item) for item in question.get("rubric", [])],
        )
        error_type = _classify_error_type(score=score, response=response)
        feedback = _feedback_message(score=score, error_type=error_type, concept_name=question["concept_name"])
        quality = max(0, min(5, round(score * 5)))

        concept_state = user_state["concept_state"][question["concept_id"]]
        _update_mastery_sm2(concept_state=concept_state, quality=quality, score=score, now=now)
        user_state["practice_records"].append(
            {
                "session_id": session_id,
                "question_id": question_id,
                "question_type": question["question_type"],
                "concept_id": question["concept_id"],
                "answer": response,
                "score": round(score, 4),
                "error_type": error_type,
                "timestamp": _isoformat(now),
            }
        )
        results.append(
            {
                "question_id": question_id,
                "question_type": question["question_type"],
                "concept_id": question["concept_id"],
                "score": round(score, 4),
                "error_type": error_type,
                "feedback": feedback,
            }
        )
        scores.append(score)

    session["status"] = "submitted"
    session["submitted_at"] = _isoformat(now)
    _save_state(state_path, state)

    overall = (sum(scores) / len(scores)) if scores else 0.0
    next_plan = generate_learning_plan(
        user_id=user_id,
        graph_path=graph_path,
        state_path=state_path,
        max_concepts=3,
    )
    return {
        "user_id": user_id,
        "session_id": session_id,
        "submitted_at": _isoformat(now),
        "overall_score": round(overall, 4),
        "results": results,
        "next_recommendations": next_plan["focus_concepts"],
    }


def get_mastery_map(
    user_id: str,
    graph_path: str,
    state_path: str = ".zhicore/learning_state.json",
) -> dict[str, Any]:
    """Return concept mastery map for one user."""
    graph = KnowledgeGraph.load(graph_path)
    state = _load_state(state_path)
    now = _utcnow()
    user_state = _ensure_user_state(state, user_id=user_id)
    _seed_concept_states(user_state=user_state, graph=graph, now=now)
    _save_state(state_path, state)

    concepts: list[dict[str, Any]] = []
    for concept_id, concept_state in user_state["concept_state"].items():
        node = graph.nodes.get(concept_id)
        if node is None:
            continue
        concepts.append(
            {
                "concept_id": concept_id,
                "concept_name": node.name,
                "mastery": round(float(concept_state["mastery"]), 4),
                "last_review_at": concept_state.get("last_review_at"),
                "next_review_at": concept_state.get("next_review_at"),
                "repetition": int(concept_state.get("repetition", 0)),
                "interval_days": int(concept_state.get("interval_days", 1)),
                "ease_factor": round(float(concept_state.get("ease_factor", 2.5)), 4),
            }
        )

    concepts.sort(key=lambda item: (item["mastery"], item["concept_name"].lower()))
    avg_mastery = (
        sum(item["mastery"] for item in concepts) / len(concepts)
        if concepts
        else 0.0
    )
    return {
        "user_id": user_id,
        "updated_at": _isoformat(now),
        "concepts": concepts,
        "stats": {
            "tracked_concepts": len(concepts),
            "average_mastery": round(avg_mastery, 4),
            "practice_count": len(user_state["practice_records"]),
        },
    }


def _plan_candidates(
    user_state: dict[str, Any],
    graph: KnowledgeGraph,
    now: datetime,
) -> list[dict[str, Any]]:
    ranked: list[dict[str, Any]] = []
    for concept_id, concept_state in user_state["concept_state"].items():
        node = graph.nodes.get(concept_id)
        if node is None:
            continue
        next_review_at = _parse_time(str(concept_state.get("next_review_at", _isoformat(now))))
        mastery = float(concept_state.get("mastery", 0.0))
        is_due = next_review_at <= now
        reason = "mastery_low" if mastery < 0.35 else ("due_review" if is_due else "regular_review")
        ranked.append(
            {
                "concept_id": concept_id,
                "concept_name": node.name,
                "mastery": round(mastery, 4),
                "last_review_at": concept_state.get("last_review_at"),
                "next_review_at": concept_state.get("next_review_at"),
                "is_due": is_due,
                "reason": reason,
                "_sort": (mastery, 0 if is_due else 1, next_review_at, node.name.lower()),
            }
        )
    ranked.sort(key=lambda item: item["_sort"])
    for item in ranked:
        item.pop("_sort", None)
    return ranked


def _build_question(
    graph: KnowledgeGraph,
    concept_id: str,
    question_type: str,
    session_id: str,
    index: int,
) -> dict[str, Any]:
    node = graph.nodes.get(concept_id)
    if node is None:
        raise ValueError(f"Unknown concept id: {concept_id}")
    relations = _concept_relations(graph=graph, concept_id=concept_id)
    concept_name = node.name
    reference_answer = node.description.strip() or f"{concept_name} 是知识图谱中的核心概念。"
    rubric = [concept_name]
    prompt = f"概念题：请解释 {concept_name}。"

    if question_type == "true_false" and relations:
        edge_type, related_name = relations[0]
        prompt = f"判断题：{concept_name} 与 {related_name} 存在 {edge_type} 关系。请回答“对”或“错”。"
        reference_answer = "对"
        rubric = [concept_name, related_name, edge_type]
    elif question_type == "fill_blank" and relations:
        edge_type, related_name = relations[0]
        prompt = f"填空题：{concept_name} --{edge_type}--> ____"
        reference_answer = related_name
        rubric = [related_name]
    elif question_type == "derive":
        if relations:
            relation_text = "；".join(f"{concept_name} --{edge}--> {name}" for edge, name in relations[:2])
            prompt = f"推导题：请说明 {concept_name} 与关联概念的关系，并给出学习建议。"
            reference_answer = f"{relation_text}。建议结合原文证据进行复习。"
            rubric = [concept_name, *[name for _, name in relations[:2]]]
        else:
            prompt = f"推导题：请基于已知知识说明 {concept_name} 的作用。"
            reference_answer = f"{concept_name} 可结合上下文进行解释，并补充应用场景。"
            rubric = [concept_name]

    question_id = _new_question_id(
        session_id=session_id,
        concept_id=concept_id,
        question_type=question_type,
        index=index,
    )
    return {
        "question_id": question_id,
        "question_type": question_type,
        "concept_id": concept_id,
        "concept_name": concept_name,
        "prompt": prompt,
        "reference_answer": reference_answer,
        "rubric": rubric,
    }


def _public_question(question: dict[str, Any]) -> dict[str, Any]:
    return {
        "question_id": question["question_id"],
        "question_type": question["question_type"],
        "concept_id": question["concept_id"],
        "concept_name": question["concept_name"],
        "prompt": question["prompt"],
    }


def _concept_relations(graph: KnowledgeGraph, concept_id: str) -> list[tuple[str, str]]:
    relation_pairs: list[tuple[str, str]] = []
    for edge in graph.edges:
        if edge.source_id == concept_id:
            node = graph.nodes.get(edge.target_id)
            if node is not None:
                relation_pairs.append((edge.edge_type, node.name))
        elif edge.target_id == concept_id:
            node = graph.nodes.get(edge.source_id)
            if node is not None:
                relation_pairs.append((edge.edge_type, node.name))
    unique: dict[str, tuple[str, str]] = {}
    for edge_type, related_name in relation_pairs:
        key = f"{edge_type}|{related_name.lower()}"
        unique.setdefault(key, (edge_type, related_name))
    return sorted(unique.values(), key=lambda item: (item[0], item[1].lower()))


def _score_answer(
    response: str,
    reference_answer: str,
    question_type: str,
    rubric: list[str],
) -> float:
    response_norm = _normalize_text(response)
    reference_norm = _normalize_text(reference_answer)
    if not response_norm:
        return 0.0

    if question_type == "true_false":
        if reference_norm.startswith("对") and response_norm in _TRUE_TOKENS:
            return 1.0
        if reference_norm.startswith("错") and response_norm in _FALSE_TOKENS:
            return 1.0
        return 0.0

    if response_norm == reference_norm:
        return 1.0
    if reference_norm and reference_norm in response_norm:
        return 0.9

    keywords = [_normalize_text(item) for item in rubric if _normalize_text(item)]
    if not keywords and reference_norm:
        keywords = [token for token in reference_norm.split() if token]
    if not keywords:
        return 0.0

    covered = sum(1 for key in keywords if key in response_norm)
    coverage = covered / len(keywords)
    score = 0.2 + 0.8 * coverage
    return max(0.0, min(1.0, score))


def _classify_error_type(score: float, response: str) -> str:
    if score >= 0.8:
        return "无明显错误"
    if not response.strip():
        return "表达不完整"
    if score >= 0.5:
        return "表达不完整"
    if score >= 0.2:
        return "推理错误"
    return "概念错误"


def _feedback_message(score: float, error_type: str, concept_name: str) -> str:
    if score >= 0.8:
        return f"掌握较好：{concept_name} 的回答覆盖了关键点。"
    if error_type == "概念错误":
        return f"建议先回顾 {concept_name} 的定义，再完成 1-2 道基础题。"
    if error_type == "推理错误":
        return f"建议补充 {concept_name} 的关系链路，重点练习因果与依赖推理。"
    return f"建议完善答案结构，补充 {concept_name} 的关键术语与证据。"


def _update_mastery_sm2(
    concept_state: dict[str, Any],
    quality: int,
    score: float,
    now: datetime,
) -> None:
    repetition = int(concept_state.get("repetition", 0))
    interval_days = int(concept_state.get("interval_days", 1))
    ease_factor = float(concept_state.get("ease_factor", 2.5))

    if quality >= 3:
        if repetition == 0:
            interval_days = 1
        elif repetition == 1:
            interval_days = 6
        else:
            interval_days = max(1, round(interval_days * ease_factor))
        repetition += 1
    else:
        repetition = 0
        interval_days = 1

    ease_factor = max(
        1.3,
        ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)),
    )
    mastery = float(concept_state.get("mastery", 0.0))
    mastery = max(0.0, min(1.0, mastery * 0.7 + score * 0.3))

    concept_state["mastery"] = mastery
    concept_state["last_review_at"] = _isoformat(now)
    concept_state["next_review_at"] = _isoformat(now + timedelta(days=interval_days))
    concept_state["repetition"] = repetition
    concept_state["interval_days"] = interval_days
    concept_state["ease_factor"] = ease_factor


def _seed_concept_states(
    user_state: dict[str, Any],
    graph: KnowledgeGraph,
    now: datetime,
) -> None:
    concept_state = user_state["concept_state"]
    for node_id, node in graph.nodes.items():
        if node.node_type not in _LEARNING_NODE_TYPES:
            continue
        concept_state.setdefault(
            node_id,
            {
                "mastery": 0.0,
                "last_review_at": None,
                "next_review_at": _isoformat(now),
                "repetition": 0,
                "interval_days": 1,
                "ease_factor": 2.5,
            },
        )


def _ensure_user_state(state: dict[str, Any], user_id: str) -> dict[str, Any]:
    users = state.setdefault("users", {})
    if user_id not in users:
        users[user_id] = {"concept_state": {}, "practice_records": []}
    user_state = users[user_id]
    user_state.setdefault("concept_state", {})
    user_state.setdefault("practice_records", [])
    return user_state


def _load_state(state_path: str) -> dict[str, Any]:
    path = Path(state_path)
    if not path.exists():
        return {"version": 1, "users": {}, "sessions": {}}
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw.setdefault("version", 1)
    raw.setdefault("users", {})
    raw.setdefault("sessions", {})
    return raw


def _save_state(state_path: str, state: dict[str, Any]) -> None:
    path = Path(state_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")


def _normalize_text(value: str) -> str:
    lowered = value.strip().lower()
    normalized = re.sub(r"[^0-9a-z\u4e00-\u9fff]+", " ", lowered)
    return " ".join(normalized.split())


def _new_session_id(user_id: str, now: datetime, existing: int) -> str:
    digest = hashlib.sha1(f"{user_id}|{_isoformat(now)}|{existing}".encode("utf-8")).hexdigest()[:12]
    return f"sess-{digest}"


def _new_question_id(session_id: str, concept_id: str, question_type: str, index: int) -> str:
    digest = hashlib.sha1(f"{session_id}|{concept_id}|{question_type}|{index}".encode("utf-8")).hexdigest()[:12]
    return f"q-{digest}"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _isoformat(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)

