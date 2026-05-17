"""
Unit tests for Tool-Use Reliability — aerosafety/eval/tool_use_reliability.py

Hand-computed expected values:

Case 1 (all required tools called, all correct):
  required_tool_call_rate = 1.0
  correct_selection/input/interpretation_rate = 1.0
  misuse_rate = 0.0

Case 2 (required tool not called):
  required_tool_call_rate = 0.0

Case 3 (tool called with wrong input, N=1):
  1 tool call: correct_sel=True, correct_input=False, correct_interp=True → misuse_rate=1.0
  correct_input_rate = 0.0

Case 4 (mixed N=2 tasks, 3 total tool calls):
  Task A: 2 calls — both fully correct
  Task B: 1 call — wrong selection
  required_tool_call_rate: both tasks have all required called → 2/2=1.0
  total_tool_calls = 3
  n_correct_sel = 2 (t_B wrong) → correct_selection_rate = 2/3
  n_correct_inp = 3 → 1.0
  n_correct_interp = 3 → 1.0
  n_misuse = 1 (t_B: wrong selection) → misuse_rate = 1/3

Case 5 (empty):
  All NaN
"""

from __future__ import annotations

import math

import pytest

from aerosafety.eval.protocols import AgentTraceStub, TaskCardStub, ToolCallStub
from aerosafety.eval.tool_use_reliability import tool_use_reliability


def _trace(task_id: str, tools: list[ToolCallStub]) -> AgentTraceStub:
    return AgentTraceStub(
        task_id=task_id, predicted_decision="x", gold_decision="x", tool_calls=tools
    )


def _card(task_id: str, required_tools: list[str]) -> TaskCardStub:
    return TaskCardStub(task_id=task_id, required_tool_names=required_tools)


class TestToolUseAllCorrect:
    def test_all_rates_perfect(self):
        tc = ToolCallStub("metar_parser", correct_selection=True, correct_input=True, correct_interpretation=True)
        traces = [_trace("t1", [tc])]
        cards = [_card("t1", ["metar_parser"])]
        result = tool_use_reliability(traces, cards)
        assert result["required_tool_call_rate"] == 1.0
        assert result["correct_selection_rate"] == 1.0
        assert result["correct_input_rate"] == 1.0
        assert result["correct_interpretation_rate"] == 1.0
        assert result["misuse_rate"] == 0.0


class TestToolUseRequiredNotCalled:
    def test_required_tool_missing(self):
        # Required: "wind_calc", but agent used "metar_parser" instead
        tc = ToolCallStub("metar_parser")
        traces = [_trace("t1", [tc])]
        cards = [_card("t1", ["wind_calc"])]
        result = tool_use_reliability(traces, cards)
        assert result["required_tool_call_rate"] == 0.0


class TestToolUseWrongInput:
    def test_wrong_input_reflected(self):
        tc = ToolCallStub("wind_calc", correct_selection=True, correct_input=False, correct_interpretation=True)
        traces = [_trace("t1", [tc])]
        cards = [_card("t1", ["wind_calc"])]
        result = tool_use_reliability(traces, cards)
        assert result["correct_input_rate"] == 0.0
        assert result["misuse_rate"] == 1.0


class TestToolUseMixed:
    def test_mixed_two_tasks(self):
        # Task A: 2 correct calls; required = ["t_a1", "t_a2"]
        tc_a1 = ToolCallStub("t_a1", correct_selection=True, correct_input=True, correct_interpretation=True)
        tc_a2 = ToolCallStub("t_a2", correct_selection=True, correct_input=True, correct_interpretation=True)
        # Task B: 1 call, wrong selection; required = ["t_b1"]
        tc_b1 = ToolCallStub("t_b1", correct_selection=False, correct_input=True, correct_interpretation=True)

        traces = [_trace("tA", [tc_a1, tc_a2]), _trace("tB", [tc_b1])]
        cards = [_card("tA", ["t_a1", "t_a2"]), _card("tB", ["t_b1"])]
        result = tool_use_reliability(traces, cards)

        # required_tool_call_rate: tA all present, tB "t_b1" present (name matches even if wrong sel)
        assert result["required_tool_call_rate"] == 1.0
        # total tool calls = 3; correct_sel: 2 → 2/3
        assert abs(result["correct_selection_rate"] - 2.0 / 3.0) < 1e-9
        # correct_input: 3/3 = 1.0
        assert result["correct_input_rate"] == 1.0
        # misuse: tB has wrong sel → 1/3
        assert abs(result["misuse_rate"] - 1.0 / 3.0) < 1e-9


class TestToolUseNoToolCalls:
    def test_nan_when_no_tool_calls(self):
        # Task has no tool calls → denominators all 0 → NaN
        traces = [_trace("t1", [])]
        cards = [_card("t1", [])]
        result = tool_use_reliability(traces, cards)
        assert math.isnan(result["correct_selection_rate"])
        assert math.isnan(result["misuse_rate"])


class TestToolUseEmpty:
    def test_empty_all_nan(self):
        result = tool_use_reliability([], [])
        assert math.isnan(result["required_tool_call_rate"])
        assert result["n_total"] == 0


class TestToolUseMismatch:
    def test_raises_on_length_mismatch(self):
        with pytest.raises(ValueError, match="same length"):
            tool_use_reliability([_trace("t1", [])], [_card("t1", []), _card("t2", [])])

    def test_raises_on_task_id_mismatch(self):
        with pytest.raises(ValueError, match="mismatch"):
            tool_use_reliability([_trace("tA", [])], [_card("tB", [])])
