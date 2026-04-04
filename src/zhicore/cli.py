"""Command-line interface for optimized Phase 1 RAG."""

from __future__ import annotations

import argparse
import json

from zhicore.pipeline import ingest_documents, load_store
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

    raise RuntimeError(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
