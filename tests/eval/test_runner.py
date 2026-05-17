"""
Unit tests for EvalRunner — aerosafety/eval/runner.py

Tests:
1. assert_eval_mode() fires — run() raises RuntimeError without AEROSAFETY_EVAL_MODE=1
2. With AEROSAFETY_EVAL_MODE=1, run() returns expected structure keys
3. per-task JSONL is written and failures are preserved
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from aerosafety.eval.protocols import AgentTraceStub, TaskCardStub, ToolCallStub
from aerosafety.eval.runner import EvalRunner


class _StubAgent:
    """Deterministic stub agent that always returns a pre-set trace."""

    def __init__(self, traces: list[AgentTraceStub]) -> None:
        self._traces = iter(traces)

    def run(self, task_card):
        return next(self._traces)


def _make_trace(task_id: str, pred: str, gold: str, unsafe: bool = False) -> AgentTraceStub:
    return AgentTraceStub(
        task_id=task_id,
        predicted_decision=pred,
        gold_decision=gold,
        unsafe_recommendation=unsafe,
        severity="Low",
        token_count=10,
        tool_call_count=0,
        latency_seconds=0.1,
    )


def _make_card(task_id: str, gold: str) -> TaskCardStub:
    return TaskCardStub(
        task_id=task_id,
        required_safety_constraints=[],
        required_tool_names=[],
        ground_truth_consequence_points=[],
        severity="Low",
    )


class TestEvalRunnerEvalModeGuard:
    def test_raises_without_eval_mode(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("AEROSAFETY_EVAL_MODE", raising=False)
        card = _make_card("t1", "go")
        trace = _make_trace("t1", "go", "go")
        runner = EvalRunner(_StubAgent([trace]), [card], output_dir=tmp_path)
        with pytest.raises(RuntimeError, match="AEROSAFETY_EVAL_MODE"):
            runner.run()

    def test_passes_with_eval_mode(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("AEROSAFETY_EVAL_MODE", "1")
        card = _make_card("t1", "go")
        trace = _make_trace("t1", "go", "go")
        runner = EvalRunner(_StubAgent([trace]), [card], output_dir=tmp_path)
        result = runner.run()
        assert "aggregate" in result
        assert "per_task" in result


class TestEvalRunnerOutputStructure:
    def test_result_keys_present(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("AEROSAFETY_EVAL_MODE", "1")
        cards = [_make_card("t1", "go"), _make_card("t2", "no-go")]
        traces = [_make_trace("t1", "go", "go"), _make_trace("t2", "go", "no-go", unsafe=True)]
        runner = EvalRunner(_StubAgent(traces), cards, output_dir=tmp_path, n_bootstrap=10)
        result = runner.run()

        assert "traces" in result
        assert "per_task" in result
        assert "aggregate" in result
        assert "jsonl_path" in result
        assert "summary_path" in result
        assert "run_metadata" in result

    def test_aggregate_contains_main_metrics(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("AEROSAFETY_EVAL_MODE", "1")
        cards = [_make_card("t1", "go")]
        traces = [_make_trace("t1", "go", "go")]
        runner = EvalRunner(_StubAgent(traces), cards, output_dir=tmp_path, n_bootstrap=10)
        result = runner.run()
        agg = result["aggregate"]

        for key in ("tsr", "svr", "scor", "ofr", "swfr", "cass", "n_total"):
            assert key in agg, f"missing key: {key}"

    def test_jsonl_written(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("AEROSAFETY_EVAL_MODE", "1")
        cards = [_make_card("t1", "go")]
        traces = [_make_trace("t1", "go", "go")]
        runner = EvalRunner(_StubAgent(traces), cards, output_dir=tmp_path, n_bootstrap=10)
        result = runner.run()
        jsonl_path = result["jsonl_path"]
        assert jsonl_path.exists()
        lines = [json.loads(l) for l in jsonl_path.read_text().strip().splitlines()]
        assert len(lines) == 1

    def test_failure_preserved_in_jsonl(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("AEROSAFETY_EVAL_MODE", "1")
        cards = [_make_card("t1", "go"), _make_card("t2", "no-go")]
        traces = [
            _make_trace("t1", "go", "go"),
            _make_trace("t2", "go", "no-go", unsafe=True),  # failure + unsafe
        ]
        runner = EvalRunner(_StubAgent(traces), cards, output_dir=tmp_path, n_bootstrap=10)
        result = runner.run()
        lines = [json.loads(l) for l in result["jsonl_path"].read_text().strip().splitlines()]
        task_ids = {r["task_id"] for r in lines}
        # t2 is a failure — must not be suppressed
        assert "t2" in task_ids

    def test_n_total_correct(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("AEROSAFETY_EVAL_MODE", "1")
        n = 3
        cards = [_make_card(f"t{i}", "go") for i in range(n)]
        traces = [_make_trace(f"t{i}", "go", "go") for i in range(n)]
        runner = EvalRunner(_StubAgent(traces), cards, output_dir=tmp_path, n_bootstrap=10)
        result = runner.run()
        assert result["aggregate"]["n_total"] == n
