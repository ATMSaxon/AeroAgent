"""
Unit tests for SVR (Safety Violation Rate) — aerosafety/eval/svr.py

Hand-computed expected values:
  Case 1 (no violations, N=3):    SVR = 0/3 = 0.0
  Case 2 (all violations, N=3):   SVR = 3/3 = 1.0
  Case 3 (mixed, N=4):            SVR = 2/4 = 0.5
  Case 4 (single violation):      SVR = 1/1 = 1.0
  Case 5 (empty):                 SVR = NaN
  Case 6 (missing attribute):     raises AttributeError
"""

from __future__ import annotations

import math

import pytest

from aerosafety.eval.protocols import AgentTraceStub
from aerosafety.eval.svr import safety_violation_rate


def _trace(task_id: str, unsafe: bool) -> AgentTraceStub:
    return AgentTraceStub(
        task_id=task_id,
        predicted_decision="go",
        gold_decision="go",
        unsafe_recommendation=unsafe,
    )


class TestSVRNoViolations:
    def test_svr_zero(self):
        traces = [_trace("t1", False), _trace("t2", False), _trace("t3", False)]
        result = safety_violation_rate(traces)
        assert result["svr"] == 0.0
        assert result["n_violations"] == 0
        assert result["violation_task_ids"] == []


class TestSVRAllViolations:
    def test_svr_one(self):
        traces = [_trace("t1", True), _trace("t2", True), _trace("t3", True)]
        result = safety_violation_rate(traces)
        assert result["svr"] == 1.0
        assert result["n_violations"] == 3
        assert set(result["violation_task_ids"]) == {"t1", "t2", "t3"}


class TestSVRMixed:
    def test_svr_half(self):
        # 2 violations out of 4 → SVR = 0.5
        traces = [
            _trace("t1", True),
            _trace("t2", False),
            _trace("t3", True),
            _trace("t4", False),
        ]
        result = safety_violation_rate(traces)
        assert result["svr"] == 0.5
        assert result["n_violations"] == 2
        assert sorted(result["violation_task_ids"]) == ["t1", "t3"]


class TestSVRSingleSample:
    def test_single_violation(self):
        result = safety_violation_rate([_trace("x", True)])
        assert result["svr"] == 1.0

    def test_single_safe(self):
        result = safety_violation_rate([_trace("x", False)])
        assert result["svr"] == 0.0


class TestSVREmpty:
    def test_empty_returns_nan(self):
        result = safety_violation_rate([])
        assert math.isnan(result["svr"])
        assert result["n_total"] == 0


class TestSVRMissingAttribute:
    def test_raises_on_missing_unsafe_recommendation(self):
        class BadTrace:
            task_id = "bad"
            # deliberately omitting unsafe_recommendation

        with pytest.raises(AttributeError, match="unsafe_recommendation"):
            safety_violation_rate([BadTrace()])  # type: ignore[list-item]
