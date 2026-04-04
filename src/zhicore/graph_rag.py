"""Graph-RAG orchestration: vector retrieval + subgraph expansion."""

from __future__ import annotations

from dataclasses import dataclass

from zhicore.kg import KnowledgeGraph
from zhicore.types import SearchHit
from zhicore.vector_store import HybridRetriever, InMemoryVectorStore


@dataclass(slots=True)
class TextEvidence:
    index: int
    chunk_id: str
    source: str
    score: float
    excerpt: str


@dataclass(slots=True)
class RelationEvidence:
    index: int
    edge_type: str
    source: str
    target: str
    evidence_chunk_id: str


@dataclass(slots=True)
class GraphRAGResult:
    answer: str
    text_evidence: list[TextEvidence]
    graph_evidence: list[RelationEvidence]
    subgraph: dict[str, list[dict]]


class GraphRAGEngine:
    """Graph-RAG retrieval chain for phase 2."""

    def __init__(
        self,
        store: InMemoryVectorStore | HybridRetriever,
        graph: KnowledgeGraph,
    ) -> None:
        self.store = store
        self.graph = graph

    def ask(
        self,
        query: str,
        top_k: int = 4,
        dense_k: int = 12,
        sparse_k: int = 12,
        rrf_k: int = 60,
        retrieval_mode: str = "hybrid",
        graph_hops: int = 1,
    ) -> GraphRAGResult:
        search_params = {"query": query, "top_k": top_k}
        if _accepts_hybrid_kwargs(self.store):
            search_params.update(
                {
                    "dense_k": dense_k,
                    "sparse_k": sparse_k,
                    "rrf_k": rrf_k,
                    "retrieval_mode": retrieval_mode,
                }
            )
        hits = self.store.search(**search_params)
        text_evidence = self._build_text_evidence(hits)

        seed_concepts = self.graph.concepts_for_chunks([item.chunk_id for item in text_evidence])
        if not seed_concepts:
            seed_concepts = self.graph.find_concepts(query, max_results=8)
        subgraph = self.graph.subgraph(seed_node_ids=seed_concepts, hops=graph_hops)
        graph_evidence = self._build_graph_evidence(subgraph)

        answer = self._compose_answer(query, text_evidence=text_evidence, graph_evidence=graph_evidence)
        return GraphRAGResult(
            answer=answer,
            text_evidence=text_evidence,
            graph_evidence=graph_evidence,
            subgraph=subgraph,
        )

    def _build_text_evidence(self, hits: list[SearchHit]) -> list[TextEvidence]:
        evidence: list[TextEvidence] = []
        for idx, hit in enumerate(hits, start=1):
            excerpt = " ".join(hit.chunk.text.split())
            if len(excerpt) > 220:
                excerpt = excerpt[:220] + "..."
            evidence.append(
                TextEvidence(
                    index=idx,
                    chunk_id=hit.chunk.chunk_id,
                    source=hit.chunk.source,
                    score=hit.score,
                    excerpt=excerpt,
                )
            )
        return evidence

    def _build_graph_evidence(self, subgraph: dict[str, list[dict]]) -> list[RelationEvidence]:
        nodes = {node["node_id"]: node for node in subgraph.get("nodes", [])}
        evidence: list[RelationEvidence] = []
        for idx, edge in enumerate(subgraph.get("edges", []), start=1):
            src = nodes.get(edge["source_id"], {}).get("name", edge["source_id"])
            dst = nodes.get(edge["target_id"], {}).get("name", edge["target_id"])
            evidence.append(
                RelationEvidence(
                    index=idx,
                    edge_type=edge["edge_type"],
                    source=src,
                    target=dst,
                    evidence_chunk_id=edge["evidence_chunk_id"],
                )
            )
        return evidence

    def _compose_answer(
        self,
        query: str,
        text_evidence: list[TextEvidence],
        graph_evidence: list[RelationEvidence],
    ) -> str:
        lines = [f"问题：{query}"]
        if text_evidence:
            lines.append("文本证据：")
            for item in text_evidence:
                lines.append(f"- [{item.index}] {item.excerpt}")
        else:
            lines.append("文本证据：未检索到相关片段。")

        if graph_evidence:
            lines.append("图谱关系证据：")
            for item in graph_evidence[:8]:
                lines.append(f"- [{item.index}] {item.source} --{item.edge_type}--> {item.target}")
        else:
            lines.append("图谱关系证据：未找到可用关系。")
        return "\n".join(lines)


def _accepts_hybrid_kwargs(store: object) -> bool:
    klass = store.__class__.__name__.lower()
    return "hybrid" in klass
