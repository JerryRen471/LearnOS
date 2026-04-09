"""Phase 3 domain types: agent run tracing payloads.

This module is internal to the `zhicore.phase3` package.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any


def now_iso() -> str:
    return datetime.now(tz=UTC).replace(microsecond=0).isoformat()


@dataclass(slots=True)
class AgentStep:
    name: str
    status: str
    detail: dict[str, Any]
    started_at: str
    finished_at: str


@dataclass(slots=True)
class AgentRun:
    run_id: str
    query: str
    index_path: str
    graph_path: str
    config: dict[str, Any]
    status: str = "running"
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)
    retry_of: str | None = None
    plan: dict[str, Any] = field(default_factory=dict)
    steps: list[AgentStep] = field(default_factory=list)
    answer: str = ""
    text_evidence: list[dict[str, Any]] = field(default_factory=list)
    graph_evidence: list[dict[str, Any]] = field(default_factory=list)
    subgraph: dict[str, list[dict[str, Any]]] = field(default_factory=lambda: {"nodes": [], "edges": []})
    evaluation: dict[str, Any] = field(default_factory=dict)
    fallback: dict[str, Any] | None = None
    error: str | None = None

    def add_step(
        self,
        *,
        name: str,
        status: str,
        detail: dict[str, Any],
        started_at: str,
        finished_at: str,
    ) -> None:
        self.steps.append(
            AgentStep(
                name=name,
                status=status,
                detail=detail,
                started_at=started_at,
                finished_at=finished_at,
            )
        )
        self.updated_at = now_iso()

    def to_payload(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "query": self.query,
            "status": self.status,
            "retry_of": self.retry_of,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "plan": self.plan,
            "steps": [asdict(step) for step in self.steps],
            "answer": self.answer,
            "text_evidence": self.text_evidence,
            "graph_evidence": self.graph_evidence,
            "subgraph": self.subgraph,
            "evaluation": self.evaluation,
            "fallback": self.fallback,
            "error": self.error,
        }

