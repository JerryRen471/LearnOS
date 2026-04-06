"""Phase 3 services: multi-agent orchestration with run tracing and fallback."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from threading import Lock
from typing import Any
from uuid import uuid4

from zhicore.graph_rag import GraphRAGEngine
from zhicore.kg import KnowledgeGraph
from zhicore.pipeline import load_store
from zhicore.rag import RAGEngine
from zhicore.vector_store import HybridRetriever, InMemoryVectorStore


def run_agent_query(
    query: str,
    index_path: str,
    graph_path: str,
    top_k: int = 4,
    dense_k: int = 12,
    sparse_k: int = 12,
    rrf_k: int = 60,
    embedding_provider: str = "auto",
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
    dense_backend: str = "auto",
) -> dict[str, Any]:
    run = _execute_agent_run(
        query=query,
        index_path=index_path,
        graph_path=graph_path,
        top_k=top_k,
        dense_k=dense_k,
        sparse_k=sparse_k,
        rrf_k=rrf_k,
        embedding_provider=embedding_provider,
        embedding_model=embedding_model,
        dense_backend=dense_backend,
    )
    _RUN_STORE.upsert(run)
    return run.to_payload()


def get_agent_run(run_id: str) -> dict[str, Any]:
    run = _RUN_STORE.get(run_id)
    if run is None:
        raise KeyError(f"Agent run not found: {run_id}")
    return run.to_payload()


def retry_agent_run(
    run_id: str,
    query: str | None = None,
    top_k: int | None = None,
    dense_k: int | None = None,
    sparse_k: int | None = None,
    rrf_k: int | None = None,
    embedding_provider: str | None = None,
    embedding_model: str | None = None,
    dense_backend: str | None = None,
) -> dict[str, Any]:
    original = _RUN_STORE.get(run_id)
    if original is None:
        raise KeyError(f"Agent run not found: {run_id}")
    config = original.config
    rerun = _execute_agent_run(
        query=query or original.query,
        index_path=original.index_path,
        graph_path=original.graph_path,
        top_k=top_k if top_k is not None else int(config.get("top_k", 4)),
        dense_k=dense_k if dense_k is not None else int(config.get("dense_k", 12)),
        sparse_k=sparse_k if sparse_k is not None else int(config.get("sparse_k", 12)),
        rrf_k=rrf_k if rrf_k is not None else int(config.get("rrf_k", 60)),
        embedding_provider=embedding_provider or str(config.get("embedding_provider", "auto")),
        embedding_model=embedding_model
        or str(config.get("embedding_model", "sentence-transformers/all-MiniLM-L6-v2")),
        dense_backend=dense_backend or str(config.get("dense_backend", "auto")),
        retry_of=run_id,
    )
    _RUN_STORE.upsert(rerun)
    return rerun.to_payload()


@dataclass(slots=True)
class AgentPlan:
    query_type: str
    strategy: str
    retrieval_mode: str
    use_graph: bool


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
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)
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

    def add_step(self, name: str, status: str, detail: dict[str, Any], started_at: str, finished_at: str) -> None:
        self.steps.append(
            AgentStep(
                name=name,
                status=status,
                detail=detail,
                started_at=started_at,
                finished_at=finished_at,
            )
        )
        self.updated_at = _now_iso()

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
        search_params: dict[str, Any] = {"query": query, "top_k": top_k}
        if _accepts_hybrid_kwargs(store):
            search_params.update(
                {
                    "dense_k": dense_k,
                    "sparse_k": sparse_k,
                    "rrf_k": rrf_k,
                    "retrieval_mode": retrieval_mode,
                }
            )
        hits = store.search(**search_params)
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
        engine = GraphRAGEngine(store=store, graph=graph)
        result = engine.ask(
            query=query,
            top_k=top_k,
            dense_k=dense_k,
            sparse_k=sparse_k,
            rrf_k=rrf_k,
            retrieval_mode=retrieval_mode,
            graph_hops=1,
        )
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


_RUN_STORE = AgentRunStore()


def _execute_agent_run(
    query: str,
    index_path: str,
    graph_path: str,
    top_k: int,
    dense_k: int,
    sparse_k: int,
    rrf_k: int,
    embedding_provider: str,
    embedding_model: str,
    dense_backend: str,
    retry_of: str | None = None,
) -> AgentRun:
    run = AgentRun(
        run_id=f"run-{uuid4().hex[:12]}",
        query=query,
        index_path=index_path,
        graph_path=graph_path,
        retry_of=retry_of,
        config={
            "top_k": top_k,
            "dense_k": dense_k,
            "sparse_k": sparse_k,
            "rrf_k": rrf_k,
            "embedding_provider": embedding_provider,
            "embedding_model": embedding_model,
            "dense_backend": dense_backend,
        },
    )

    planner = PlannerAgent()
    retriever = RetrievalAgent()
    graph_agent = GraphAgent()
    evaluator = EvaluationAgent()

    try:
        started = _now_iso()
        plan = planner.plan(query)
        run.plan = asdict(plan)
        run.add_step(
            name="planner_agent",
            status="completed",
            detail=run.plan,
            started_at=started,
            finished_at=_now_iso(),
        )

        started = _now_iso()
        store = load_store(
            index_path=index_path,
            embedding_provider=embedding_provider,
            embedding_model=embedding_model,
            dense_backend=dense_backend,
        )
        retrieval_evidence = retriever.retrieve(
            store=store,
            query=query,
            top_k=top_k,
            dense_k=dense_k,
            sparse_k=sparse_k,
            rrf_k=rrf_k,
            retrieval_mode=plan.retrieval_mode,
        )
        run.add_step(
            name="retrieval_agent",
            status="completed",
            detail={
                "retrieval_mode": plan.retrieval_mode,
                "candidate_evidence_count": len(retrieval_evidence),
                "candidate_chunk_ids": [item.chunk_id for item in retrieval_evidence],
            },
            started_at=started,
            finished_at=_now_iso(),
        )

        if plan.use_graph:
            started = _now_iso()
            try:
                graph = KnowledgeGraph.load(graph_path)
                graph_result = graph_agent.run(
                    store=store,
                    graph=graph,
                    query=query,
                    top_k=top_k,
                    dense_k=dense_k,
                    sparse_k=sparse_k,
                    rrf_k=rrf_k,
                    retrieval_mode=plan.retrieval_mode,
                )
                run.answer = graph_result["answer"]
                run.text_evidence = graph_result["text_evidence"]
                run.graph_evidence = graph_result["graph_evidence"]
                run.subgraph = graph_result["subgraph"]
                run.add_step(
                    name="graph_agent",
                    status="completed",
                    detail={
                        "graph_nodes": len(run.subgraph.get("nodes", [])),
                        "graph_edges": len(run.subgraph.get("edges", [])),
                        "graph_evidence_count": len(run.graph_evidence),
                    },
                    started_at=started,
                    finished_at=_now_iso(),
                )
            except Exception as exc:
                run.fallback = {
                    "triggered": True,
                    "mode": "rag",
                    "reason": str(exc),
                }
                rag_result = RAGEngine(store).ask(
                    query=query,
                    top_k=top_k,
                    dense_k=dense_k,
                    sparse_k=sparse_k,
                    rrf_k=rrf_k,
                    retrieval_mode=plan.retrieval_mode,
                )
                run.answer = rag_result.answer
                run.text_evidence = [asdict(item) for item in rag_result.citations]
                run.graph_evidence = []
                run.subgraph = {"nodes": [], "edges": []}
                run.add_step(
                    name="graph_agent",
                    status="failed_with_fallback",
                    detail=run.fallback,
                    started_at=started,
                    finished_at=_now_iso(),
                )
        else:
            rag_result = RAGEngine(store).ask(
                query=query,
                top_k=top_k,
                dense_k=dense_k,
                sparse_k=sparse_k,
                rrf_k=rrf_k,
                retrieval_mode=plan.retrieval_mode,
            )
            run.answer = rag_result.answer
            run.text_evidence = [asdict(item) for item in rag_result.citations]
            run.graph_evidence = []
            run.subgraph = {"nodes": [], "edges": []}

        started = _now_iso()
        run.evaluation = evaluator.evaluate(
            answer=run.answer,
            text_evidence=run.text_evidence,
            graph_evidence=run.graph_evidence,
            use_graph=plan.use_graph and not bool(run.fallback),
        )
        run.add_step(
            name="evaluation_agent",
            status="completed",
            detail=run.evaluation,
            started_at=started,
            finished_at=_now_iso(),
        )
        run.status = "succeeded"
        run.updated_at = _now_iso()
        return run
    except Exception as exc:
        run.status = "failed"
        run.error = str(exc)
        run.updated_at = _now_iso()
        return run


def _accepts_hybrid_kwargs(store: object) -> bool:
    klass = store.__class__.__name__.lower()
    return "hybrid" in klass


def _now_iso() -> str:
    return datetime.now(tz=UTC).replace(microsecond=0).isoformat()
