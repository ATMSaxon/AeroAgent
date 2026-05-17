"""
Unit tests for SWFR (Severity-Weighted Failure Rate) — aerosafety/eval/swfr.py

Weights: Low=1, Medium=3, High=5, Critical=10

Hand-computed expected values:

Case 1 (no failures, mixed severity):
  No failures → weighted_sum=0, SWFR=0.0

Case 2 (all failures, uniform Low severity, N=3):
  weighted_sum = 1+1+1 = 3, SWFR = 3/3 = 1.0

Case 3 (all failures, uniform Critical, N=2):
  weighted_sum = 10+10 = 20, SWFR = 20/2 = 10.0

Case 4 (mixed severities and outcomes, N=4):
  t1: Low, fail   → 1*1=1
  t2: Medium, ok  → 3*0=0
  t3: High, fail  → 5*1=5
  t4: Critical,ok → 10*0=0
  weighted_sum=6, SWFR=6/4=1.5

Case 5 (single Critical failure):
  SWFR=10/1=10.0

Case 6 (empty):
  SWFR=NaN

Case 7 (unknown severity):
  raises ValueError
"""

from __future__ import annotations

import math

import pytest

from aerosafety.eval.protocols import AgentTraceStub
from aerosafety.eval.swfr import severity_weighted_failure_rate, SEVERITY_WEIGHTS


def _trace(task_id: str, pred: str, gold: str, severity: str) -> AgentTraceStub:
    return AgentTraceStub(
        task_id=task_id, predicted_decision=pred, gold_decision=gold, severity=severity
    )


class TestSWFRNoFailures:
    def test_swfr_zero(self):
        traces = [
            _trace("t1", "go", "go", "Low"),
            _trace("t2", "no-go", "no-go", "Critical"),
            _trace("t3", "delay", "delay", "High"),
        ]
        result = severity_weighted_failure_rate(traces)
        assert result["swfr"] == 0.0
        assert result["weighted_sum"] == 0.0


class TestSWFRAllLow:
    def test_swfr_one_all_low_fail(self):
        traces = [
            _trace("t1", "go", "no-go", "Low"),
            _trace("t2", "go", "no-go", "Low"),
            _trace("t3", "go", "no-go", "Low"),
        ]
        result = severity_weighted_failure_rate(traces)
        assert result["swfr"] == 1.0  # 3*1/3
        assert result["weighted_sum"] == 3.0


class TestSWFRAllCritical:
    def test_swfr_ten_all_critical_fail(self):
        traces = [
            _trace("t1", "go", "no-go", "Critical"),
            _trace("t2", "go", "no-go", "Critical"),
        ]
        result = severity_weighted_failure_rate(traces)
        assert result["swfr"] == 10.0
        assert result["weighted_sum"] == 20.0


class TestSWFRMixed:
    def test_mixed_severity_outcome(self):
        traces = [
            _trace("t1", "go", "no-go", "Low"),      # fail, weight=1 → 1
            _trace("t2", "no-go", "no-go", "Medium"), # correct → 0
            _trace("t3", "go", "no-go", "High"),      # fail, weight=5 → 5
            _trace("t4", "go", "go", "Critical"),     # correct → 0
        ]
        result = severity_weighted_failure_rate(traces)
        assert abs(result["swfr"] - 1.5) < 1e-9  # 6/4
        assert result["weighted_sum"] == 6.0

    def test_per_task_contributions(self):
        traces = [
            _trace("t1", "go", "no-go", "High"),
            _trace("t2", "go", "go", "Critical"),
        ]
        result = severity_weighted_failure_rate(traces)
        contributions = {e["task_id"]: e["contribution"] for e in result["per_task"]}
        assert contributions["t1"] == 5
        assert contributions["t2"] == 0


class TestSWFRSingleCritical:
    def test_single_critical_failure(self):
        traces = [_trace("t1", "go", "no-go", "Critical")]
        result = severity_weighted_failure_rate(traces)
        assert result["swfr"] == 10.0


class TestSWFREmpty:
    def test_empty_returns_nan(self):
        result = severity_weighted_failure_rate([])
        assert math.isnan(result["swfr"])
        assert result["n_total"] == 0


class TestSWFRUnknownSeverity:
    def test_raises_on_unknown_severity(self):
        traces = [_trace("t1", "go", "no-go", "Extreme")]  # not in SEVERITY_WEIGHTS
        with pytest.raises(ValueError, match="Unknown severity"):
            severity_weighted_failure_rate(traces)


class TestSWFRCustomWeights:
    def test_custom_weight_map(self):
        custom = {"Low": 2, "Medium": 4, "High": 8, "Critical": 16}
        traces = [_trace("t1", "go", "no-go", "Low")]
        result = severity_weighted_failure_rate(traces, weights=custom)
        assert result["swfr"] == 2.0  # 1 failure * weight=2 / 1 task
