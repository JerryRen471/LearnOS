"""FastAPI endpoints for Phase 2/3/4 services."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from zhicore.phase2 import build_or_update_kg, query_graph_rag, query_subgraph
from zhicore.phase3 import get_agent_run, retry_agent_run, run_agent_query
from zhicore.phase4 import (
    create_learning_plan,
    create_learning_session,
    get_learning_mastery_map,
    submit_learning_answers,
)

app = FastAPI(title="ZhiCore API", version="0.4.0")


class KGBuildRequest(BaseModel):
    inputs: list[str]
    graph_path: str = ".zhicore/graph.json"
    index_path: str = ".zhicore/index.json"
    chunk_size: int = 600
    overlap: int = 120
    embedding_provider: str = "hash"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    dense_backend: str = "cosine"
    incremental: bool = True


class SubgraphRequest(BaseModel):
    query: str | None = None
    concept: str | None = None
    graph_path: str = ".zhicore/graph.json"
    hops: int = Field(default=1, ge=0, le=2)
    max_nodes: int = Field(default=80, ge=1, le=300)


class GraphRAGRequest(BaseModel):
    query: str
    index_path: str = ".zhicore/index.json"
    graph_path: str = ".zhicore/graph.json"
    top_k: int = Field(default=4, ge=1, le=20)
    dense_k: int = Field(default=12, ge=1, le=60)
    sparse_k: int = Field(default=12, ge=1, le=60)
    rrf_k: int = Field(default=60, ge=1, le=1000)
    retrieval_mode: str = "hybrid"
    graph_hops: int = Field(default=1, ge=0, le=2)
    embedding_provider: str = "auto"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    dense_backend: str = "auto"


class AgentQueryRequest(BaseModel):
    query: str
    index_path: str = ".zhicore/index.json"
    graph_path: str = ".zhicore/graph.json"
    top_k: int = Field(default=4, ge=1, le=20)
    dense_k: int = Field(default=12, ge=1, le=60)
    sparse_k: int = Field(default=12, ge=1, le=60)
    rrf_k: int = Field(default=60, ge=1, le=1000)
    embedding_provider: str = "auto"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    dense_backend: str = "auto"


class AgentRetryRequest(BaseModel):
    query: str | None = None
    top_k: int | None = Field(default=None, ge=1, le=20)
    dense_k: int | None = Field(default=None, ge=1, le=60)
    sparse_k: int | None = Field(default=None, ge=1, le=60)
    rrf_k: int | None = Field(default=None, ge=1, le=1000)
    embedding_provider: str | None = None
    embedding_model: str | None = None
    dense_backend: str | None = None


class LearningPlanRequest(BaseModel):
    user_id: str
    graph_path: str = ".zhicore/graph.json"
    max_concepts: int = Field(default=8, ge=1, le=50)


class LearningSessionRequest(BaseModel):
    user_id: str
    graph_path: str = ".zhicore/graph.json"
    question_count: int = Field(default=6, ge=1, le=60)
    question_types: list[str] | None = None


class LearningSubmitItem(BaseModel):
    question_id: str
    answer: str


class LearningSubmitRequest(BaseModel):
    user_id: str
    answers: list[LearningSubmitItem]


@app.post("/kg/build")
def build_kg_endpoint(payload: KGBuildRequest) -> dict[str, int]:
    try:
        return build_or_update_kg(
            inputs=payload.inputs,
            graph_path=payload.graph_path,
            index_path=payload.index_path,
            chunk_size=payload.chunk_size,
            overlap=payload.overlap,
            embedding_provider=payload.embedding_provider,
            embedding_model=payload.embedding_model,
            dense_backend=payload.dense_backend,
            incremental=payload.incremental,
        )
    except Exception as exc:  # pragma: no cover - framework wrapping
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/kg/subgraph")
def get_subgraph(
    graph_path: str = ".zhicore/graph.json",
    query: str | None = None,
    concept: str | None = None,
    hops: int = 1,
    max_nodes: int = 80,
) -> dict[str, list[dict]]:
    try:
        return query_subgraph(
            graph_path=graph_path,
            query=query,
            concept=concept,
            hops=hops,
            max_nodes=max_nodes,
        )
    except Exception as exc:  # pragma: no cover - framework wrapping
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/query/graph-rag")
def graph_rag_endpoint(payload: GraphRAGRequest) -> dict:
    if payload.retrieval_mode not in {"hybrid", "dense", "sparse"}:
        raise HTTPException(status_code=400, detail="retrieval_mode must be hybrid/dense/sparse")
    try:
        result = query_graph_rag(
            query=payload.query,
            index_path=payload.index_path,
            graph_path=payload.graph_path,
            top_k=payload.top_k,
            dense_k=payload.dense_k,
            sparse_k=payload.sparse_k,
            rrf_k=payload.rrf_k,
            retrieval_mode=payload.retrieval_mode,
            graph_hops=payload.graph_hops,
            embedding_provider=payload.embedding_provider,
            embedding_model=payload.embedding_model,
            dense_backend=payload.dense_backend,
        )
    except Exception as exc:  # pragma: no cover - framework wrapping
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "answer": result.answer,
        "text_evidence": [
            {
                "index": item.index,
                "chunk_id": item.chunk_id,
                "source": item.source,
                "score": item.score,
                "excerpt": item.excerpt,
            }
            for item in result.text_evidence
        ],
        "graph_evidence": [
            {
                "index": item.index,
                "edge_type": item.edge_type,
                "source": item.source,
                "target": item.target,
                "evidence_chunk_id": item.evidence_chunk_id,
            }
            for item in result.graph_evidence
        ],
        "subgraph": result.subgraph,
    }


@app.post("/agent/query")
def agent_query_endpoint(payload: AgentQueryRequest) -> dict:
    try:
        return run_agent_query(
            query=payload.query,
            index_path=payload.index_path,
            graph_path=payload.graph_path,
            top_k=payload.top_k,
            dense_k=payload.dense_k,
            sparse_k=payload.sparse_k,
            rrf_k=payload.rrf_k,
            embedding_provider=payload.embedding_provider,
            embedding_model=payload.embedding_model,
            dense_backend=payload.dense_backend,
        )
    except Exception as exc:  # pragma: no cover - framework wrapping
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/agent/runs/{run_id}")
def get_agent_run_endpoint(run_id: str) -> dict:
    try:
        return get_agent_run(run_id=run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - framework wrapping
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/agent/runs/{run_id}/retry")
def retry_agent_run_endpoint(run_id: str, payload: AgentRetryRequest) -> dict:
    try:
        return retry_agent_run(
            run_id=run_id,
            query=payload.query,
            top_k=payload.top_k,
            dense_k=payload.dense_k,
            sparse_k=payload.sparse_k,
            rrf_k=payload.rrf_k,
            embedding_provider=payload.embedding_provider,
            embedding_model=payload.embedding_model,
            dense_backend=payload.dense_backend,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - framework wrapping
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/learning/plan")
def learning_plan_endpoint(payload: LearningPlanRequest) -> dict:
    try:
        return create_learning_plan(
            user_id=payload.user_id,
            graph_path=payload.graph_path,
            max_concepts=payload.max_concepts,
        )
    except Exception as exc:  # pragma: no cover - framework wrapping
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/learning/session")
def learning_session_endpoint(payload: LearningSessionRequest) -> dict:
    if payload.question_types:
        allowed = {"concept", "judgement", "cloze", "derivation"}
        unknown = [item for item in payload.question_types if item not in allowed]
        if unknown:
            raise HTTPException(status_code=400, detail=f"Unsupported question_types: {unknown}")
    try:
        return create_learning_session(
            user_id=payload.user_id,
            graph_path=payload.graph_path,
            question_count=payload.question_count,
            question_types=payload.question_types,
        )
    except Exception as exc:  # pragma: no cover - framework wrapping
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/learning/submit")
def learning_submit_endpoint(payload: LearningSubmitRequest) -> dict:
    if not payload.answers:
        raise HTTPException(status_code=400, detail="answers must not be empty")
    try:
        return submit_learning_answers(
            user_id=payload.user_id,
            answers=[{"question_id": item.question_id, "answer": item.answer} for item in payload.answers],
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - framework wrapping
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/learning/mastery-map")
def learning_mastery_map_endpoint(user_id: str) -> dict:
    try:
        return get_learning_mastery_map(user_id=user_id)
    except Exception as exc:  # pragma: no cover - framework wrapping
        raise HTTPException(status_code=400, detail=str(exc)) from exc
