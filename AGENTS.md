# AGENTS.md

## Cursor Cloud specific instructions

### Project overview

LearnOS is an intelligent personal knowledge system powered by LLMs, RAG, and Knowledge Graphs. The project is Python-based (Python 3.12+).

### Repository state

- Python package source lives in `src/zhicore`.
- Tests live in `tests`.
- Packaging and test configuration are defined in `pyproject.toml`.
- A CLI entrypoint exists: `zhicore = zhicore.cli:main`.

### Environment

- **Python**: 3.12.3 is available system-wide.
- **Default interpreter**: use `python3` (Python 3.12.x).
- **Dependency file**: `pyproject.toml` is the source of truth.
- **Services**: no external services are required for core local tests.
- **Startup script**: run `python3 -m pip install -e ".[dev]"` on agent startup.

### Setup commands

- Install package + test dependencies: `python3 -m pip install -e ".[dev]"`
- Install optional PDF support: `python3 -m pip install -e ".[pdf]"`
- Install optional RAG stack: `python3 -m pip install -e ".[rag]"`

### Validation commands

- Run focused tests: `python3 -m pytest tests`
- Run a specific test module when iterating: `python3 -m pytest tests/test_pipeline.py`
- Check CLI wiring: `python3 -m zhicore.cli --help`

### Agent working notes

- Keep edits tightly scoped to the user's explicit request.
- For documentation-only changes, validate by re-reading updated files.
- Update this file whenever setup, test, run, or dependency conventions change.
