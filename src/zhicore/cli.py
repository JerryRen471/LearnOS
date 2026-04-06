"""Command-line interface for optimized Phase 1 RAG."""

from __future__ import annotations

import argparse
import json

from zhicore.pipeline import ingest_documents, load_store
from zhicore.phase2 import build_or_update_kg, query_graph_rag, query_subgraph
from zhicore.rag import RAGEngine


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="zhicore", description="ZhiCore Phase 1+ CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest_parser = subparsers.add_parser("ingest", help="Ingest source files into index")
    ingest_parser.add_argument("--input", nargs="+", required=True, help="Input files or directories")
    ingest_parser.add_argument("--index-path", default=".zhicore/index.json", help="Index output path")
    ingest_parser.add_argument("--chunk-size", type=int, default=600, help="Chunk size in characters")
    ingest_parser.add_argument("--overlap", type=int, default=120, help="Chunk overlap in characters")
    ingest_parser.add_argument(
        "--embedding-provider",
        choices=["hash", "sentence-transformers"],
        default="hash",
        help="Embedding backend used for dense retrieval",
    )
    ingest_parser.add_argument(
        "--embedding-model",
        default="sentence-transformers/all-MiniLM-L6-v2",
        help="Embedding model name when provider=sentence-transformers",
    )
    ingest_parser.add_argument(
        "--dense-backend",
        choices=["cosine", "faiss"],
        default="cosine",
        help="Dense retrieval backend",
    )

    ask_parser = subparsers.add_parser("ask", help="Ask questions against index")
    ask_parser.add_argument("--index-path", default=".zhicore/index.json", help="Index path")
    ask_parser.add_argument("--query", required=True, help="Question text")
    ask_parser.add_argument("--top-k", type=int, default=4, help="Top-k retrieval count")
    ask_parser.add_argument("--dense-k", type=int, default=12, help="Dense retrieval candidate count")
    ask_parser.add_argument("--sparse-k", type=int, default=12, help="Sparse BM25 candidate count")
    ask_parser.add_argument("--rrf-k", type=int, default=60, help="RRF fusion constant")
    ask_parser.add_argument(
        "--retrieval-mode",
        choices=["hybrid", "dense", "sparse"],
        default="hybrid",
        help="Retrieval strategy: hybrid (RRF), dense-only, or sparse-only",
    )
    ask_parser.add_argument(
        "--embedding-provider",
        choices=["auto", "hash", "sentence-transformers"],
        default="auto",
        help="Override embedding provider for loading advanced indexes",
    )
    ask_parser.add_argument(
        "--embedding-model",
        default="sentence-transformers/all-MiniLM-L6-v2",
        help="Embedding model when provider=sentence-transformers",
    )
    ask_parser.add_argument(
        "--dense-backend",
        choices=["auto", "cosine", "faiss"],
        default="auto",
        help="Override dense backend for advanced indexes",
    )
    ask_parser.add_argument("--json", action="store_true", help="Output JSON")

    kg_build_parser = subparsers.add_parser(
        "kg-build",
        help="Build or update knowledge graph from inputs",
    )
    kg_build_parser.add_argument("--input", nargs="+", required=True, help="Input files or directories")
    kg_build_parser.add_argument("--graph-path", default=".zhicore/graph.json", help="Knowledge graph path")
    kg_build_parser.add_argument("--index-path", default=".zhicore/index.json", help="Index path")
    kg_build_parser.add_argument("--chunk-size", type=int, default=600, help="Chunk size in characters")
    kg_build_parser.add_argument("--overlap", type=int, default=120, help="Chunk overlap in characters")
    kg_build_parser.add_argument(
        "--embedding-provider",
        choices=["hash", "sentence-transformers"],
        default="hash",
        help="Embedding backend used for dense retrieval",
    )
    kg_build_parser.add_argument(
        "--embedding-model",
        default="sentence-transformers/all-MiniLM-L6-v2",
        help="Embedding model name when provider=sentence-transformers",
    )
    kg_build_parser.add_argument(
        "--dense-backend",
        choices=["cosine", "faiss"],
        default="cosine",
        help="Dense retrieval backend",
    )
    kg_build_parser.add_argument(
        "--incremental",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable incremental upsert (default: true)",
    )

    kg_subgraph_parser = subparsers.add_parser(
        "kg-subgraph",
        help="Fetch subgraph by concept or query",
    )
    kg_subgraph_parser.add_argument("--graph-path", default=".zhicore/graph.json", help="Knowledge graph path")
    kg_subgraph_parser.add_argument("--query", default=None, help="Query text used to locate seed concepts")
    kg_subgraph_parser.add_argument("--concept", default=None, help="Seed concept name")
    kg_subgraph_parser.add_argument("--hops", type=int, default=1, help="Subgraph expansion hops")
    kg_subgraph_parser.add_argument("--max-nodes", type=int, default=80, help="Max nodes in returned subgraph")
    kg_subgraph_parser.add_argument("--json", action="store_true", help="Output JSON (default behavior)")

    graph_ask_parser = subparsers.add_parser(
        "graph-ask",
        help="Ask question via Graph-RAG (vector + graph evidence)",
    )
    graph_ask_parser.add_argument("--query", required=True, help="Question text")
    graph_ask_parser.add_argument("--index-path", default=".zhicore/index.json", help="Index path")
    graph_ask_parser.add_argument("--graph-path", default=".zhicore/graph.json", help="Knowledge graph path")
    graph_ask_parser.add_argument("--top-k", type=int, default=4, help="Top-k retrieval count")
    graph_ask_parser.add_argument("--dense-k", type=int, default=12, help="Dense retrieval candidate count")
    graph_ask_parser.add_argument("--sparse-k", type=int, default=12, help="Sparse retrieval candidate count")
    graph_ask_parser.add_argument("--rrf-k", type=int, default=60, help="RRF fusion constant")
    graph_ask_parser.add_argument(
        "--retrieval-mode",
        choices=["hybrid", "dense", "sparse"],
        default="hybrid",
        help="Retrieval strategy: hybrid (RRF), dense-only, or sparse-only",
    )
    graph_ask_parser.add_argument("--graph-hops", type=int, default=1, help="Graph expansion hops")
    graph_ask_parser.add_argument(
        "--embedding-provider",
        choices=["auto", "hash", "sentence-transformers"],
        default="auto",
        help="Override embedding provider for loading advanced indexes",
    )
    graph_ask_parser.add_argument(
        "--embedding-model",
        default="sentence-transformers/all-MiniLM-L6-v2",
        help="Embedding model when provider=sentence-transformers",
    )
    graph_ask_parser.add_argument(
        "--dense-backend",
        choices=["auto", "cosine", "faiss"],
        default="auto",
        help="Override dense backend for advanced indexes",
    )
    graph_ask_parser.add_argument("--json", action="store_true", help="Output JSON")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "ingest":
        stats = ingest_documents(
            inputs=args.input,
            index_path=args.index_path,
            chunk_size=args.chunk_size,
            overlap=args.overlap,
            embedding_provider=args.embedding_provider,
            embedding_model=args.embedding_model,
            dense_backend=args.dense_backend,
        )
        print(json.dumps(stats, ensure_ascii=False))
        return

    if args.command == "ask":
        store = load_store(
            args.index_path,
            embedding_provider=args.embedding_provider,
            embedding_model=args.embedding_model,
            dense_backend=args.dense_backend,
        )
        rag = RAGEngine(store)
        result = rag.ask(
            query=args.query,
            top_k=args.top_k,
            dense_k=args.dense_k,
            sparse_k=args.sparse_k,
            rrf_k=args.rrf_k,
            retrieval_mode=args.retrieval_mode,
        )
        if args.json:
            payload = {
                "answer": result.answer,
                "citations": [
                    {
                        "index": citation.index,
                        "source": citation.source,
                        "chunk_id": citation.chunk_id,
                        "score": citation.score,
                        "excerpt": citation.excerpt,
                    }
                    for citation in result.citations
                ],
            }
            print(json.dumps(payload, ensure_ascii=False))
            return

        print(result.answer)
        if result.citations:
            print("\nSources:")
            for citation in result.citations:
                print(
                    f"[{citation.index}] {citation.source} | "
                    f"{citation.chunk_id} | score={citation.score:.4f}"
                )
        return

    if args.command == "kg-build":
        stats = build_or_update_kg(
            inputs=args.input,
            graph_path=args.graph_path,
            index_path=args.index_path,
            chunk_size=args.chunk_size,
            overlap=args.overlap,
            embedding_provider=args.embedding_provider,
            embedding_model=args.embedding_model,
            dense_backend=args.dense_backend,
            incremental=args.incremental,
        )
        print(json.dumps(stats, ensure_ascii=False))
        return

    if args.command == "kg-subgraph":
        subgraph = query_subgraph(
            graph_path=args.graph_path,
            query=args.query,
            concept=args.concept,
            hops=args.hops,
            max_nodes=args.max_nodes,
        )
        print(json.dumps(subgraph, ensure_ascii=False))
        return

    if args.command == "graph-ask":
        result = query_graph_rag(
            query=args.query,
            index_path=args.index_path,
            graph_path=args.graph_path,
            top_k=args.top_k,
            dense_k=args.dense_k,
            sparse_k=args.sparse_k,
            rrf_k=args.rrf_k,
            retrieval_mode=args.retrieval_mode,
            graph_hops=args.graph_hops,
            embedding_provider=args.embedding_provider,
            embedding_model=args.embedding_model,
            dense_backend=args.dense_backend,
        )
        payload = {
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
        if args.json:
            print(json.dumps(payload, ensure_ascii=False))
            return

        print(result.answer)
        if result.text_evidence:
            print("\nText evidence:")
            for item in result.text_evidence:
                print(f"[{item.index}] {item.source} | {item.chunk_id} | score={item.score:.4f}")
        if result.graph_evidence:
            print("\nGraph evidence:")
            for item in result.graph_evidence[:12]:
                print(
                    f"[{item.index}] {item.source} --{item.edge_type}--> {item.target} "
                    f"(chunk={item.evidence_chunk_id})"
                )
        return

    raise RuntimeError(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
