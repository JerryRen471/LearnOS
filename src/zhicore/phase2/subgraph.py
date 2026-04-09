"""Phase 2: subgraph query wrapper (backward compatible)."""

from __future__ import annotations

from zhicore.application.kg_service import query_subgraph as _query_subgraph


def query_subgraph(
    graph_path: str,
    query: str | None = None,
    concept: str | None = None,
    hops: int = 1,
    max_nodes: int = 80,
) -> dict[str, list[dict]]:
    return _query_subgraph(
        graph_path=graph_path,
        query=query,
        concept=concept,
        hops=hops,
        max_nodes=max_nodes,
    )

