"""Phase 2 package: KG build/update, subgraph query, Graph-RAG query.

This package replaces the legacy `zhicore.phase2` module while keeping the same
public import surface:

    from zhicore.phase2 import build_or_update_kg, query_subgraph, kg_stats, query_graph_rag
"""

from zhicore.phase2.build import build_or_update_kg
from zhicore.phase2.graph_rag import query_graph_rag
from zhicore.phase2.stats import kg_stats
from zhicore.phase2.subgraph import query_subgraph

__all__ = ["build_or_update_kg", "kg_stats", "query_subgraph", "query_graph_rag"]

