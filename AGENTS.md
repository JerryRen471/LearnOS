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
- **Dependency file**: `pyproject.toml` is the source of truth.
- **Services**: no external services are required for core local tests.

### Setup commands

- Install package + test dependencies: `python -m pip install -e ".[dev]"`
- Install optional PDF support: `python -m pip install -e ".[pdf]"`
- Install optional RAG stack: `python -m pip install -e ".[rag]"`

### Validation commands

- Run focused tests: `pytest tests`
- Run a specific test module when iterating: `pytest tests/test_pipeline.py`
- Check CLI wiring: `python -m zhicore.cli --help`

### Agent working notes

- Keep edits tightly scoped to the user's explicit request.
- For documentation-only changes, validate by re-reading updated files.
- Update this file whenever setup, test, run, or dependency conventions change.
