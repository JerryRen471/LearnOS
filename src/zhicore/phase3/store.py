"""In-memory store for agent runs."""

from __future__ import annotations

from threading import Lock

from zhicore.phase3.types import AgentRun


class AgentRunStore:
    def __init__(self) -> None:
        self._runs: dict[str, AgentRun] = {}
        self._lock = Lock()

    def upsert(self, run: AgentRun) -> None:
        with self._lock:
            self._runs[run.run_id] = run

    def get(self, run_id: str) -> AgentRun | None:
        with self._lock:
            return self._runs.get(run_id)


RUN_STORE = AgentRunStore()

from zhicore.phase3.types import now_iso

