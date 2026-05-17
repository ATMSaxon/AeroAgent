"""
Unit tests for TSR (Task Success Rate) — aerosafety/eval/tsr.py

Hand-computed expected values:
  Case 1 (all correct, N=3):   TSR = 3/3 = 1.0
  Case 2 (all wrong, N=3):     TSR = 0/3 = 0.0
  Case 3 (mixed, N=4):         TSR = 2/4 = 0.5
  Case 4 (single correct):     TSR = 1/1 = 1.0
  Case 5 (empty):              TSR = NaN, n_total = 0
"""

from __future__ import annotations

import math

import pytest

from aerosafety.eval.protocols import AgentTraceStub
from aerosafety.eval.tsr import task_success_rate


def _trace(task_id: str, pred: str, gold: str) -> AgentTraceStub:
    return AgentTraceStub(task_id=task_id, predicted_decision=pred, gold_decision=gold)


class TestTSRAllCorrect:
    def test_tsr_is_one(self):
        traces = [
            _trace("t1", "go", "go"),
            _trace("t2", "no-go", "no-go"),
            _trace("t3", "delay", "delay"),
        ]
        result = task_success_rate(traces)
        assert result["tsr"] == 1.0
        assert result["n_correct"] == 3
        assert result["n_total"] == 3

    def test_per_task_all_correct(self):
        traces = [_trace("t1", "go", "go"), _trace("t2", "no-go", "no-go")]
        result = task_success_rate(traces)
        assert all(entry["correct"] for entry in result["per_task"])


class TestTSRAllWrong:
    def test_tsr_is_zero(self):
        traces = [
            _trace("t1", "go", "no-go"),
            _trace("t2", "delay", "go"),
            _trace("t3", "no-go", "delay"),
        ]
        result = task_success_rate(traces)
        assert result["tsr"] == 0.0
        assert result["n_correct"] == 0

    def test_per_task_all_wrong(self):
        traces = [_trace("t1", "go", "no-go"), _trace("t2", "delay", "go")]
        result = task_success_rate(traces)
        assert all(not entry["correct"] for entry in result["per_task"])


class TestTSRMixed:
    def test_tsr_half(self):
        # 2 correct, 2 wrong → TSR = 0.5
        traces = [
            _trace("t1", "go", "go"),      # correct
            _trace("t2", "go", "no-go"),   # wrong
            _trace("t3", "delay", "delay"),# correct
            _trace("t4", "go", "delay"),   # wrong
        ]
        result = task_success_rate(traces)
        assert result["tsr"] == 0.5
        assert result["n_correct"] == 2
        assert result["n_total"] == 4

    def test_per_task_ids_preserved(self):
        traces = [
            _trace("alpha", "go", "go"),
            _trace("beta", "go", "no-go"),
        ]
        result = task_success_rate(traces)
        ids = [e["task_id"] for e in result["per_task"]]
        assert ids == ["alpha", "beta"]


class TestTSRSingleSample:
    def test_single_correct(self):
        traces = [_trace("only", "go", "go")]
        result = task_success_rate(traces)
        assert result["tsr"] == 1.0
        assert result["n_total"] == 1

    def test_single_wrong(self):
        traces = [_trace("only", "go", "no-go")]
        result = task_success_rate(traces)
        assert result["tsr"] == 0.0


class TestTSREmpty:
    def test_empty_returns_nan(self):
        result = task_success_rate([])
        assert math.isnan(result["tsr"])
        assert result["n_total"] == 0
        assert result["n_correct"] == 0
        assert result["per_task"] == []
