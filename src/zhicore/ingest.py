"""Document ingestion for Phase 1."""

from __future__ import annotations

import hashlib
from pathlib import Path

from zhicore.types import Document

SUPPORTED_EXTENSIONS = {".md", ".txt", ".pdf"}


def collect_input_files(inputs: list[str]) -> list[Path]:
    """Expand file and directory inputs into a deterministic file list."""
    files: set[Path] = set()
    for raw in inputs:
        path = Path(raw).expanduser()
        if not path.exists():
            raise FileNotFoundError(f"Input path not found: {path}")
        if path.is_file():
            if path.suffix.lower() in SUPPORTED_EXTENSIONS:
                files.add(path.resolve())
            continue
        for ext in SUPPORTED_EXTENSIONS:
            for match in path.rglob(f"*{ext}"):
                if match.is_file():
                    files.add(match.resolve())
    if not files:
        raise ValueError("No supported files found (.md/.txt/.pdf).")
    return sorted(files)


def load_document(path: Path) -> Document:
    """Load one file into a normalized Document structure."""
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported extension: {suffix}")
    if suffix in {".md", ".txt"}:
        text = path.read_text(encoding="utf-8")
    else:
        text = _read_pdf(path)
    normalized_text = _normalize_text(text)
    document_id = hashlib.sha1(str(path.resolve()).encode("utf-8")).hexdigest()[:16]
    return Document(
        id=document_id,
        source=str(path),
        text=normalized_text,
        metadata={"extension": suffix},
    )


def ingest_inputs(inputs: list[str]) -> list[Document]:
    """Ingest one or many file/directory inputs."""
    files = collect_input_files(inputs)
    return [load_document(path) for path in files]


def _read_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - import guard
        raise RuntimeError(
            "PDF ingestion requires pypdf. Install with: pip install '.[pdf]'"
        ) from exc

    reader = PdfReader(str(path))
    pages: list[str] = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return "\n\n".join(pages)


def _normalize_text(text: str) -> str:
    lines = [line.rstrip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    normalized = "\n".join(lines).strip()
    if not normalized:
        return ""
    return normalized + "\n"
