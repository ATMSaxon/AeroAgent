"""
Unit tests for SCOR (Safety Constraint Omission Rate) — aerosafety/eval/scor.py

Hand-computed expected values:
  Case 1 (no omissions):
    required = ["c1", "c2"], cited = {"c1", "c2"} → omitted=0, SCOR=0.0

  Case 2 (all omitted, N=1):
    required = ["c1", "c2"], cited = {} → omitted=2, SCOR=1.0

  Case 3 (partial, N=2 tasks):
    Task A: required=["c1","c2","c3"], cited={"c1"} → omitted=2
    Task B: required=["c4","c5"],     cited={"c4","c5"} → omitted=0
    total_constraints=5, total_omitted=2 → SCOR = 2/5 = 0.4

  Case 4 (empty constraints, N=1):
    required=[], cited=anything → SCOR = NaN (0/0)

  Case 5 (zero denominator across all tasks):
    All tasks have no required constraints → SCOR = NaN
"""

from __future__ import annotations

import math

import pytest

from aerosafety.eval.protocols import AgentTraceStub, TaskCardStub
from aerosafety.eval.scor import safety_constraint_omission_rate


def _trace(task_id: str, citations: list[str]) -> AgentTraceStub:
    return AgentTraceStub(task_id=task_id, predicted_decision="x", gold_decision="x", citations=citations)


def _card(task_id: str, required: list[str]) -> TaskCardStub:
    return TaskCardStub(task_id=task_id, required_safety_constraints=required)


class TestSCORNoneOmitted:
    def test_scor_zero_when_all_cited(self):
        traces = [_trace("t1", ["c1", "c2"])]
        cards = [_card("t1", ["c1", "c2"])]
        result = safety_constraint_omission_rate(traces, cards)
        assert result["scor"] == 0.0
        assert result["total_omitted"] == 0
        assert result["per_task"][0]["omitted"] == []


class TestSCORAllOmitted:
    def test_scor_one_when_nothing_cited(self):
        traces = [_trace("t1", [])]
        cards = [_card("t1", ["c1", "c2"])]
        result = safety_constraint_omission_rate(traces, cards)
        assert result["scor"] == 1.0
        assert result["total_omitted"] == 2
        assert set(result["per_task"][0]["omitted"]) == {"c1", "c2"}


class TestSCORPartial:
    def test_scor_partial_two_tasks(self):
        # Task A: 3 required, 1 cited → 2 omitted
        # Task B: 2 required, 2 cited → 0 omitted
        # total_constraints=5, total_omitted=2, SCOR=2/5=0.4
        traces = [
            _trace("tA", ["c1"]),
            _trace("tB", ["c4", "c5"]),
        ]
        cards = [
            _card("tA", ["c1", "c2", "c3"]),
            _card("tB", ["c4", "c5"]),
        ]
        result = safety_constraint_omission_rate(traces, cards)
        assert abs(result["scor"] - 0.4) < 1e-9
        assert result["total_constraints"] == 5
        assert result["total_omitted"] == 2


class TestSCOREmptyConstraints:
    def test_scor_nan_when_no_constraints(self):
        traces = [_trace("t1", ["c1"])]
        cards = [_card("t1", [])]
        result = safety_constraint_omission_rate(traces, cards)
        assert math.isnan(result["scor"])

    def test_per_task_rate_nan(self):
        traces = [_trace("t1", [])]
        cards = [_card("t1", [])]
        result = safety_constraint_omission_rate(traces, cards)
        assert math.isnan(result["per_task"][0]["omission_rate"])


class TestSCORMismatch:
    def test_raises_on_length_mismatch(self):
        with pytest.raises(ValueError, match="same length"):
            safety_constraint_omission_rate(
                [_trace("t1", [])],
                [_card("t1", []), _card("t2", [])],
            )

    def test_raises_on_task_id_mismatch(self):
        with pytest.raises(ValueError, match="mismatch"):
            safety_constraint_omission_rate(
                [_trace("tA", [])],
                [_card("tB", [])],
            )
