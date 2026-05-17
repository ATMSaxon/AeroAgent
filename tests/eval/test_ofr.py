"""
Unit tests for OFR (Overconfident Failure Rate) — aerosafety/eval/ofr.py

Default confidence_threshold = 0.8

Hand-computed expected values:

Case 1 (no wrong answers):
  All correct → OFR = NaN (denominator is n_wrong=0)

Case 2 (all wrong, all high-confidence, N=3):
  n_wrong=3, n_wrong_high_conf=3 → OFR=1.0

Case 3 (all wrong, none high-confidence):
  n_wrong=3, n_wrong_high_conf=0 → OFR=0.0

Case 4 (mixed, N=4):
  t1: wrong, conf=0.9 (>=0.8) → overconfident
  t2: correct, conf=0.95      → not applicable
  t3: wrong, conf=0.5 (<0.8)  → not overconfident
  t4: wrong, conf=0.85        → overconfident
  n_wrong=3, n_wrong_high_conf=2 → OFR=2/3

Case 5 (single wrong, high-confidence):
  OFR=1.0

Case 6 (empty):
  OFR=NaN
"""

from __future__ import annotations

import math

from aerosafety.eval.ofr import overconfident_failure_rate
from aerosafety.eval.protocols import AgentTraceStub


def _trace(task_id: str, pred: str, gold: str, confidence: float) -> AgentTraceStub:
    return AgentTraceStub(
        task_id=task_id,
        predicted_decision=pred,
        gold_decision=gold,
        confidence=confidence,
    )


class TestOFRNoWrong:
    def test_nan_when_all_correct(self):
        traces = [
            _trace("t1", "go", "go", 0.95),
            _trace("t2", "no-go", "no-go", 0.9),
        ]
        result = overconfident_failure_rate(traces)
        assert math.isnan(result["ofr"])
        assert result["n_wrong"] == 0


class TestOFRAllWrongHighConf:
    def test_ofr_one(self):
        traces = [
            _trace("t1", "go", "no-go", 0.9),
            _trace("t2", "delay", "go", 0.95),
            _trace("t3", "no-go", "delay", 0.88),
        ]
        result = overconfident_failure_rate(traces)
        assert result["ofr"] == 1.0
        assert result["n_wrong_high_confidence"] == 3


class TestOFRAllWrongLowConf:
    def test_ofr_zero_when_all_low_confidence(self):
        traces = [
            _trace("t1", "go", "no-go", 0.3),
            _trace("t2", "delay", "go", 0.5),
            _trace("t3", "no-go", "delay", 0.7),
        ]
        result = overconfident_failure_rate(traces, confidence_threshold=0.8)
        assert result["ofr"] == 0.0
        assert result["n_wrong_high_confidence"] == 0


class TestOFRMixed:
    def test_ofr_two_thirds(self):
        traces = [
            _trace("t1", "go", "no-go", 0.9),     # wrong, high-conf → overconfident
            _trace("t2", "no-go", "no-go", 0.95), # correct
            _trace("t3", "go", "no-go", 0.5),     # wrong, low-conf → NOT overconfident
            _trace("t4", "go", "no-go", 0.85),    # wrong, high-conf → overconfident
        ]
        result = overconfident_failure_rate(traces)
        assert abs(result["ofr"] - 2.0 / 3.0) < 1e-9
        assert result["n_wrong"] == 3
        assert result["n_wrong_high_confidence"] == 2


class TestOFRSingleWrong:
    def test_single_overconfident(self):
        traces = [_trace("t1", "go", "no-go", 0.99)]
        result = overconfident_failure_rate(traces)
        assert result["ofr"] == 1.0


class TestOFREmpty:
    def test_empty_returns_nan(self):
        result = overconfident_failure_rate([])
        assert math.isnan(result["ofr"])
        assert result["n_total"] == 0


class TestOFRThreshold:
    def test_custom_threshold(self):
        traces = [
            _trace("t1", "go", "no-go", 0.75),   # wrong; at threshold 0.7 → overconfident
            _trace("t2", "go", "no-go", 0.6),    # wrong; at threshold 0.7 → NOT overconfident
        ]
        result = overconfident_failure_rate(traces, confidence_threshold=0.7)
        assert abs(result["ofr"] - 0.5) < 1e-9
