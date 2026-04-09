"""Phase 2 module: KG stats query."""

from __future__ import annotations

from zhicore.application.kg_service import kg_stats as _kg_stats


def kg_stats(graph_path: str) -> dict:
    return _kg_stats(graph_path=graph_path)

