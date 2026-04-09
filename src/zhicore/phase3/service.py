"""Phase 3 orchestration service (Agent query execution)."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any
from uuid import uuid4

from zhicore.kg import KnowledgeGraph
from zhicore.pipeline import load_store
from zhicore.rag import RAGEngine
from zhicore.phase3.agents import EvaluationAgent, GraphAgent, PlannerAgent, RetrievalAgent
from zhicore.phase3.store import AgentRun, AgentRunStore, RUN_STORE, now_iso


def execute_agent_run(
    *,
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
    run_store: AgentRunStore,
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
        started = now_iso()
        plan = planner.plan(query)
        run.plan = asdict(plan)
        run.add_step(
            name="planner_agent",
            status="completed",
            detail=run.plan,
            started_at=started,
            finished_at=now_iso(),
        )

        started = now_iso()
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
            finished_at=now_iso(),
        )

        if plan.use_graph:
            started = now_iso()
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
                    finished_at=now_iso(),
                )
            except Exception as exc:
                run.fallback = {"triggered": True, "mode": "rag", "reason": str(exc)}
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
                    finished_at=now_iso(),
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

        started = now_iso()
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
            finished_at=now_iso(),
        )
        run.status = "succeeded"
        run.updated_at = now_iso()
        run_store.upsert(run)
        return run
    except Exception as exc:
        run.status = "failed"
        run.error = str(exc)
        run.updated_at = now_iso()
        run_store.upsert(run)
        return run


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
    run = execute_agent_run(
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
        run_store=RUN_STORE,
    )
    return run.to_payload()


def get_agent_run(run_id: str) -> dict[str, Any]:
    run = RUN_STORE.get(run_id)
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
    original = RUN_STORE.get(run_id)
    if original is None:
        raise KeyError(f"Agent run not found: {run_id}")
    cfg = original.config
    run = execute_agent_run(
        query=query or original.query,
        index_path=original.index_path,
        graph_path=original.graph_path,
        top_k=top_k if top_k is not None else int(cfg.get("top_k", 4)),
        dense_k=dense_k if dense_k is not None else int(cfg.get("dense_k", 12)),
        sparse_k=sparse_k if sparse_k is not None else int(cfg.get("sparse_k", 12)),
        rrf_k=rrf_k if rrf_k is not None else int(cfg.get("rrf_k", 60)),
        embedding_provider=embedding_provider or str(cfg.get("embedding_provider", "auto")),
        embedding_model=embedding_model or str(cfg.get("embedding_model", "sentence-transformers/all-MiniLM-L6-v2")),
        dense_backend=dense_backend or str(cfg.get("dense_backend", "auto")),
        retry_of=run_id,
        run_store=RUN_STORE,
    )
    return run.to_payload()
