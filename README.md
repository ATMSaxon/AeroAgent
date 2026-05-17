# AeroSafetyEval

**PROTOTYPE ONLY — research code under active development.**

AeroSafetyEval is the executable environment for the study:

> *Reliability Limits of Agentic AI in Aviation Operations and Safety:
> A Systematic Study Across Safety-Critical Decision Workflows*

This repository implements the evaluation infrastructure, agent systems,
tools layer, task families, and analysis pipelines described in the research
proposal. It is a research prototype and is **not** suitable for operational
aviation use. All outputs are advisory and require human expert review.

---

## Repository map

```
aerosafety/
  __init__.py          — package entry-point, re-exports shared types
  io.py                — shared Pydantic schemas (TaskCard, AgentTrace, …)
  determinism.py       — seed locking, prompt hashing, eval-mode guard
  config/
    __init__.py        — config loader (raises on missing keys)
    base.yaml          — default configuration
    model_registry.yaml — registered evaluation models
  logging/
    __init__.py        — public logging API
    logger.py          — ExperimentLogger (JSONL) + get_logger (stderr JSON)
tests/
  conftest.py          — shared pytest fixtures
pyproject.toml         — dependencies and tool config
.env.example           — required environment variables (copy to .env)
```

---

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
# Fill in API keys in .env
```

## Running tests

```bash
pytest tests/
```

## Running evaluation

```bash
AEROSAFETY_EVAL_MODE=1 python -m aerosafety.eval.run --config configs/exp1.yaml
```

**NOT IMPLEMENTED** — evaluation entry-point is under construction.

---

## Constraints

This project follows strict research integrity constraints documented in
`CLAUDE.md`. No results, metrics, or model outputs in this repository are
fabricated. All synthetic data is explicitly labelled. All failure cases are
preserved. See `CLAUDE.md` for the full constraint set.
