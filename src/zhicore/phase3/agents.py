"""Phase 3 agent components: planner/retrieval/graph/evaluation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from zhicore.domain.agent.tools import ToolContext, ToolRegistry, ToolResult
from zhicore.domain.rag.interfaces import RetrievalParams
from zhicore.graph_rag import GraphRAGEngine
from zhicore.kg import KnowledgeGraph
from zhicore.types import SearchHit
from zhicore.vector_store import HybridRetriever, InMemoryVectorStore


@dataclass(slots=True)
class AgentPlan:
    query_type: str
    strategy: str
    retrieval_mode: str
    use_graph: bool


@dataclass(slots=True)
class RetrievalEvidence:
    index: int
    chunk_id: str
    source: str
    score: float
    excerpt: str


class PlannerAgent:
    def plan(self, query: str) -> AgentPlan:
        lowered = query.lower().strip()
        relation_markers = ["关系", "关联", "联系", "推理", "related", "relation", "path", "依赖"]
        definition_markers = ["是什么", "定义", "解释", "meaning", "what is", "定义为"]

        if any(marker in lowered for marker in relation_markers):
            return AgentPlan(
                query_type="关系推理",
                strategy="graph_rag_priority",
                retrieval_mode="hybrid",
                use_graph=True,
            )
        if any(marker in lowered for marker in definition_markers):
            return AgentPlan(
                query_type="定义解释",
                strategy="hybrid_with_optional_graph",
                retrieval_mode="hybrid",
                use_graph=True,
            )
        return AgentPlan(
            query_type="综合问答",
            strategy="hybrid_retrieval_first",
            retrieval_mode="hybrid",
            use_graph=False,
        )


class RetrievalAgent:
    def retrieve(
        self,
        store: InMemoryVectorStore | HybridRetriever,
        query: str,
        top_k: int,
        dense_k: int,
        sparse_k: int,
        rrf_k: int,
        retrieval_mode: str,
    ) -> list[RetrievalEvidence]:
        hits: list[SearchHit] = store.retrieve(
            RetrievalParams(
                query=query,
                top_k=top_k,
                dense_k=dense_k,
                sparse_k=sparse_k,
                rrf_k=rrf_k,
                retrieval_mode=retrieval_mode,
            )
        )
        evidence: list[RetrievalEvidence] = []
        for idx, hit in enumerate(hits, start=1):
            excerpt = " ".join(hit.chunk.text.split())
            if len(excerpt) > 220:
                excerpt = excerpt[:220] + "..."
            evidence.append(
                RetrievalEvidence(
                    index=idx,
                    chunk_id=hit.chunk.chunk_id,
                    source=hit.chunk.source,
                    score=float(hit.score),
                    excerpt=excerpt,
                )
            )
        return evidence


class GraphAgent:
    def __init__(self, tools: ToolRegistry | None = None) -> None:
        self._tools = tools or ToolRegistry()

    def run(
        self,
        store: InMemoryVectorStore | HybridRetriever,
        graph: KnowledgeGraph,
        query: str,
        top_k: int,
        dense_k: int,
        sparse_k: int,
        rrf_k: int,
        retrieval_mode: str,
    ) -> dict[str, Any]:
        # Backward-compatible: execute Graph-RAG via tool registry for modularity.
        if not self._tools.has("graph_rag"):
            self._tools.register(
                "graph_rag",
                lambda ctx, payload: ToolResult(
                    ok=True,
                    data=GraphRAGEngine(store=ctx.store, graph=ctx.graph).ask(
                        query=str(payload["query"]),
                        top_k=int(payload["top_k"]),
                        dense_k=int(payload["dense_k"]),
                        sparse_k=int(payload["sparse_k"]),
                        rrf_k=int(payload["rrf_k"]),
                        retrieval_mode=str(payload["retrieval_mode"]),
                        graph_hops=int(payload.get("graph_hops", 1)),
                    ),
                ),
            )
        tool_result = self._tools.run(
            "graph_rag",
            ctx=ToolContext(store=store, graph=graph),
            payload={
                "query": query,
                "top_k": top_k,
                "dense_k": dense_k,
                "sparse_k": sparse_k,
                "rrf_k": rrf_k,
                "retrieval_mode": retrieval_mode,
                "graph_hops": 1,
            },
        )
        if not tool_result.ok:
            raise RuntimeError(tool_result.error or "graph_rag tool failed")
        result = tool_result.data
        return {
            "answer": result.answer,
            "text_evidence": [asdict(item) for item in result.text_evidence],
            "graph_evidence": [asdict(item) for item in result.graph_evidence],
            "subgraph": result.subgraph,
        }


class EvaluationAgent:
    def evaluate(
        self,
        answer: str,
        text_evidence: list[dict[str, Any]],
        graph_evidence: list[dict[str, Any]],
        use_graph: bool,
    ) -> dict[str, Any]:
        text_score = min(1.0, len(text_evidence) / 4.0)
        graph_score = min(1.0, len(graph_evidence) / 4.0) if use_graph else 0.0
        coverage = round((text_score * 0.7 + graph_score * 0.3), 3)

        consistency = 0.2
        if answer.strip():
            consistency = 0.6 if text_evidence else 0.4
            if use_graph and graph_evidence:
                consistency = 0.85
        confidence = round(coverage * 0.6 + consistency * 0.4, 3)

        if confidence >= 0.75:
            band = "high"
        elif confidence >= 0.45:
            band = "medium"
        else:
            band = "low"
        return {
            "consistency_check": consistency >= 0.4,
            "coverage_score": coverage,
            "confidence": confidence,
            "confidence_band": band,
        }

