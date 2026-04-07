# AGENTS.md

## Cursor Cloud specific instructions

### Project overview

LearnOS (ZhiCore/CogniCore) is an intelligent personal knowledge system powered by LLMs, RAG, and Knowledge Graphs.

### Repository state

- Source package: `src/zhicore`
- Tests: `tests`
- Project config: `pyproject.toml`
- CLI entrypoint: `zhicore = zhicore.cli:main`

### Environment

- **Python**: 3.12.3 is available system-wide.
- **Project requirement**: `requires-python = ">=3.10"` (from `pyproject.toml`).
- **Dependency source of truth**: `pyproject.toml`.
- **Services**: no external services are required for core local tests.
- **Test runner**: `pytest` is provided via the `dev` extra (`.[dev]`) and is not assumed to be preinstalled.

### Setup commands

- Install package + test dependencies: `python3 -m pip install -e ".[dev]"`
- Install optional PDF support: `python3 -m pip install -e ".[pdf]"`
- Install optional RAG stack: `python3 -m pip install -e ".[rag]"`
- Install all cloud extras: `python3 -m pip install -e ".[cloud]"`

### Validation commands

- Install test deps (once): `python3 -m pip install -e ".[dev]"`
- Run focused tests: `python3 -m pytest tests`
- Run a specific test module when iterating: `python3 -m pytest tests/test_pipeline.py`
- Check CLI wiring (editable install): `python3 -m zhicore.cli --help`
- Check CLI wiring (without install): `PYTHONPATH=src python3 -m zhicore.cli --help`

### Agent working notes

- Keep edits tightly scoped to the user's explicit request.
- For documentation-only changes, validate by re-reading updated files.
- Update this file whenever setup, test, run, or dependency conventions change.
