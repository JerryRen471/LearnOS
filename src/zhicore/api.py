"""FastAPI endpoints for Phase 2/3 services."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from zhicore.application.kg_service import build_or_update_kg, kg_stats, query_subgraph
from zhicore.application.query_service import query_graph_rag
from zhicore.phase3 import get_agent_run, retry_agent_run, run_agent_query

app = FastAPI(title="ZhiCore API", version="0.3.0")

# Add CORS middleware to allow requests from the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:3000", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


@app.get("/kg/stats")
def get_kg_stats(graph_path: str = ".zhicore/graph.json") -> dict:
    try:
        return kg_stats(graph_path=graph_path)
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
