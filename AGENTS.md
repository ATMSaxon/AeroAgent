# Repository Guidelines

## Project Structure & Module Organization

This repository contains the `aerosafety` Python package for AeroSafetyEval. Core code lives in `aerosafety/`: agents in `aerosafety/agents/`, metrics and runners in `aerosafety/eval/`, tools in `aerosafety/tools/`, training utilities in `aerosafety/training/`, and schemas/downloaders in `aerosafety/data/`. Task families and JSONL taskcards are under `aerosafety/tasks/<task_name>/taskcards/`. Tests mirror these areas under `tests/`, including `tests/tools/`, `tests/eval/`, `tests/agents/`, and `tests/training/`. Raw and multimodal assets live under `data/`; preserve manifests and provenance files.

## Build, Test, and Development Commands

- `python -m pip install -e ".[dev]"`: install the package in editable mode with development tools.
- `pytest`: run the full test suite defined in `pyproject.toml`.
- `pytest tests/tools/test_metar_parser.py`: run a focused test file during iteration.
- `ruff check aerosafety tests`: lint imports, naming, pyupgrade, and common Python errors.
- `mypy aerosafety`: run strict type checks for package code.

There is no production server entry point; treat evaluation and training scripts as research tooling unless marked complete.

## Coding Style & Naming Conventions

Use Python 3.11 and keep lines within 100 characters. Follow Ruff rules in `pyproject.toml`, including sorted imports and snake_case names for modules, functions, and variables. Use PascalCase for Pydantic models and classes. Keep task files named by existing patterns, for example `typeA_knowledge.jsonl`, `typeB_hazard.jsonl`, and `sources.md`. Prefer typed interfaces and explicit errors over silent fallbacks.

## Testing Guidelines

Use pytest for all tests. Place new tests next to the related subsystem and name files `test_*.py`. Add regressions for bug fixes and schema/tool changes. For data or taskcard edits, run relevant task tests, for example `pytest tests/tasks/`, plus affected integrity or schema tests. Do not relax warnings, determinism checks, or assertions to make tests pass.

## Commit & Pull Request Guidelines

Recent history uses concise imperative summaries and Conventional Commit-style prefixes, especially `fix(data): ...`; follow that pattern where useful. PRs should describe the behavior or data change, list tests run, and identify affected task families or data sources. For UI or document changes, include screenshots or rendered outputs when applicable.

## Research Integrity & Configuration

Follow `CLAUDE.md`: do not fabricate data, metrics, citations, expert labels, or implementation status. Mark synthetic data clearly and preserve source, access date, license, and preprocessing details. Keep secrets out of the repo; use local `.env` files or environment variables.
