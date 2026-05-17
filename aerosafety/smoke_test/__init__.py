"""
aerosafety.smoke_test — end-to-end pipeline validation.

T8a scope: MockLLM-only. No real API calls.
T8b (real LLM execution) is a downstream task gated on API key + budget.

Modules:
    annotate.py  — rule-based EvalAnnotation from AgentTrace + TaskCard
    runner.py    — CLI entry point wiring agents × tasks × EvalRunner
    mock_run.py  — programmatic mock pipeline for testing
    report.py    — per-system comparison markdown with bootstrap CIs
"""
