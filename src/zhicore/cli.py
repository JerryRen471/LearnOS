"""Command-line interface for optimized Phase 1 RAG."""

from __future__ import annotations

import argparse
import json

from zhicore.pipeline import ingest_documents, load_store
from zhicore.phase4 import (
    create_learning_plan,
    create_learning_session,
    get_learning_mastery_map,
    submit_learning_answers,
)
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

    learning_plan_parser = subparsers.add_parser("learning-plan", help="Create personalized learning plan")
    learning_plan_parser.add_argument("--user-id", required=True, help="User id")
    learning_plan_parser.add_argument("--graph-path", default=".zhicore/graph.json", help="Knowledge graph path")
    learning_plan_parser.add_argument(
        "--max-concepts",
        type=int,
        default=8,
        help="Maximum recommended concepts",
    )

    learning_session_parser = subparsers.add_parser("learning-session", help="Generate practice questions")
    learning_session_parser.add_argument("--user-id", required=True, help="User id")
    learning_session_parser.add_argument("--graph-path", default=".zhicore/graph.json", help="Knowledge graph path")
    learning_session_parser.add_argument(
        "--question-count",
        type=int,
        default=6,
        help="Number of generated questions",
    )
    learning_session_parser.add_argument(
        "--question-types",
        nargs="+",
        choices=["concept", "judgement", "cloze", "derivation"],
        help="Question types to include",
    )

    learning_submit_parser = subparsers.add_parser("learning-submit", help="Submit answers for a learning session")
    learning_submit_parser.add_argument("--user-id", required=True, help="User id")
    learning_submit_parser.add_argument(
        "--answers-json",
        required=True,
        help='JSON list, e.g. \'[{"question_id":"q1","answer":"..."}]\'',
    )

    learning_mastery_parser = subparsers.add_parser("learning-mastery-map", help="Get user mastery map")
    learning_mastery_parser.add_argument("--user-id", required=True, help="User id")
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

    if args.command == "learning-plan":
        result = create_learning_plan(
            user_id=args.user_id,
            graph_path=args.graph_path,
            max_concepts=args.max_concepts,
        )
        print(json.dumps(result, ensure_ascii=False))
        return

    if args.command == "learning-session":
        result = create_learning_session(
            user_id=args.user_id,
            graph_path=args.graph_path,
            question_count=args.question_count,
            question_types=args.question_types,
        )
        print(json.dumps(result, ensure_ascii=False))
        return

    if args.command == "learning-submit":
        answers = _parse_answers_json(args.answers_json)
        result = submit_learning_answers(user_id=args.user_id, answers=answers)
        print(json.dumps(result, ensure_ascii=False))
        return

    if args.command == "learning-mastery-map":
        result = get_learning_mastery_map(user_id=args.user_id)
        print(json.dumps(result, ensure_ascii=False))
        return

    raise RuntimeError(f"Unknown command: {args.command}")


def _parse_answers_json(raw: str) -> list[dict[str, str]]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("answers-json must be a valid JSON list.") from exc
    if not isinstance(payload, list):
        raise ValueError("answers-json must be a JSON list.")

    normalized: list[dict[str, str]] = []
    for idx, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError(f"answers-json[{idx}] must be an object.")
        normalized.append(
            {
                "question_id": str(item.get("question_id", "")),
                "answer": str(item.get("answer", "")),
            }
        )
    return normalized


if __name__ == "__main__":
    main()
