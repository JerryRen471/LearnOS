"""Command-line interface for Phase 1."""

from __future__ import annotations

import argparse
import json

from zhicore.pipeline import ingest_documents, load_store
from zhicore.rag import RAGEngine


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="zhicore", description="ZhiCore Phase 1 CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest_parser = subparsers.add_parser("ingest", help="Ingest source files into index")
    ingest_parser.add_argument("--input", nargs="+", required=True, help="Input files or directories")
    ingest_parser.add_argument("--index-path", default=".zhicore/index.json", help="Index output path")
    ingest_parser.add_argument("--chunk-size", type=int, default=600, help="Chunk size in characters")
    ingest_parser.add_argument("--overlap", type=int, default=120, help="Chunk overlap in characters")

    ask_parser = subparsers.add_parser("ask", help="Ask questions against index")
    ask_parser.add_argument("--index-path", default=".zhicore/index.json", help="Index path")
    ask_parser.add_argument("--query", required=True, help="Question text")
    ask_parser.add_argument("--top-k", type=int, default=4, help="Top-k retrieval count")
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
        )
        print(json.dumps(stats, ensure_ascii=False))
        return

    if args.command == "ask":
        store = load_store(args.index_path)
        rag = RAGEngine(store)
        result = rag.ask(query=args.query, top_k=args.top_k)
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
