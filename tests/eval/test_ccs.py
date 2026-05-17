"""
Unit tests for CCS (Consequence Coverage Score) — aerosafety/eval/ccs.py

Uses MockJudge (substring match) for deterministic, hand-computed results.

Hand-computed expected values:

Case 1 (all covered, N=1):
  ground_truth = ["runway incursion", "wake turbulence"]
  predicted = "risk of runway incursion and wake turbulence encounter"
  MockJudge: both substrings present → covered=2, CCS=1.0

Case 2 (none covered, N=1):
  ground_truth = ["fuel exhaustion", "gear failure"]
  predicted = "weather delay expected"
  MockJudge: neither substring present → covered=0, CCS=0.0

Case 3 (partial, N=1):
  ground_truth = ["ice accretion", "loss of separation", "go around required"]
  predicted = "ice accretion on airframe may require go around required"
  MockJudge: "ice accretion"=yes, "loss of separation"=no, "go around required"=yes
  CCS = 2/3

Case 4 (two tasks, mixed):
  Task A: 2/2 covered → CCS_A=1.0
  Task B: 0/2 covered → CCS_B=0.0
  Overall: 2/4=0.5

Case 5 (empty consequence points):
  ground_truth = [] → CCS = NaN

Case 6 (empty tasks):
  CCS = NaN
"""

from __future__ import annotations

import math

import pytest

from aerosafety.eval.ccs import MockJudge, consequence_coverage_score
from aerosafety.eval.protocols import AgentTraceStub, TaskCardStub


def _trace(task_id: str, pred: str) -> AgentTraceStub:
    return AgentTraceStub(task_id=task_id, predicted_decision=pred, gold_decision="x")


def _card(task_id: str, consequences: list[str]) -> TaskCardStub:
    return TaskCardStub(task_id=task_id, ground_truth_consequence_points=consequences)


class TestCCSAllCovered:
    def test_ccs_one(self):
        traces = [_trace("t1", "risk of runway incursion and wake turbulence encounter")]
        cards = [_card("t1", ["runway incursion", "wake turbulence"])]
        result = consequence_coverage_score(traces, cards, judge=MockJudge())
        assert result["ccs"] == 1.0
        assert result["total_covered"] == 2
        assert result["total_consequence_points"] == 2


class TestCCSNoneCovered:
    def test_ccs_zero(self):
        traces = [_trace("t1", "weather delay expected")]
        cards = [_card("t1", ["fuel exhaustion", "gear failure"])]
        result = consequence_coverage_score(traces, cards, judge=MockJudge())
        assert result["ccs"] == 0.0
        assert result["total_covered"] == 0


class TestCCSPartial:
    def test_ccs_two_thirds(self):
        traces = [_trace("t1", "ice accretion on airframe may require go around required")]
        cards = [_card("t1", ["ice accretion", "loss of separation", "go around required"])]
        result = consequence_coverage_score(traces, cards, judge=MockJudge())
        assert abs(result["ccs"] - 2.0 / 3.0) < 1e-9
        assert result["total_covered"] == 2

    def test_uncovered_points_recorded(self):
        traces = [_trace("t1", "ice accretion only")]
        cards = [_card("t1", ["ice accretion", "loss of separation"])]
        result = consequence_coverage_score(traces, cards, judge=MockJudge())
        pt = result["per_task"][0]
        assert "loss of separation" in pt["uncovered_points"]
        assert "ice accretion" in pt["covered_points"]


class TestCCSTwoTasks:
    def test_mixed_two_tasks(self):
        traces = [
            _trace("tA", "runway collision and wake turbulence encounter"),
            _trace("tB", "weather delay"),
        ]
        cards = [
            _card("tA", ["runway collision", "wake turbulence"]),
            _card("tB", ["fuel leak", "engine failure"]),
        ]
        result = consequence_coverage_score(traces, cards, judge=MockJudge())
        assert result["ccs"] == 0.5  # 2/4
        assert result["total_covered"] == 2


class TestCCSEmptyConsequences:
    def test_nan_on_empty_ground_truth(self):
        traces = [_trace("t1", "something")]
        cards = [_card("t1", [])]
        result = consequence_coverage_score(traces, cards, judge=MockJudge())
        assert math.isnan(result["ccs"])
        assert math.isnan(result["per_task"][0]["ccs"])


class TestCCSEmpty:
    def test_empty_tasks_nan(self):
        result = consequence_coverage_score([], [], judge=MockJudge())
        assert math.isnan(result["ccs"])
        assert result["total_consequence_points"] == 0
        assert result["per_task"] == []

    def test_judge_type_reported(self):
        result = consequence_coverage_score([], [], judge=MockJudge())
        assert result["judge_type"] == "MockJudge"


class TestCCSMismatch:
    def test_raises_on_length_mismatch(self):
        with pytest.raises(ValueError, match="same length"):
            consequence_coverage_score(
                [_trace("t1", "x")],
                [_card("t1", []), _card("t2", [])],
            )
