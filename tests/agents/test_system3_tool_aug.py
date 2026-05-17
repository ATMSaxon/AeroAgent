"""
Unit tests for System 3: ToolAugmentedAgent.

All LLM calls use MockLLM. No real API calls.
Tool registry uses the built-in stub registry unless overridden.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from aerosafety.agents.mock_llm import MockLLM
from aerosafety.agents.system3_tool_aug import ToolAugmentedAgent
from aerosafety.io import AgentTrace, TaskCard


def _tool_call_response(tool: str, args: dict[str, Any]) -> str:
    return json.dumps({"action": "tool_call", "tool": tool, "args": args})


def _final_response(decision: str = "PROCEED", escalate: bool = False) -> str:
    return json.dumps({
        "action": "final",
        "decision": decision,
        "rationale": "Tool outputs verified; operation is safe.",
        "safety_constraints_cited": ["wind_limit"],
        "evidence_cited": ["echo_tool output"],
        "escalation_recommended": escalate,
        "uncertainty_flags": [],
    })


class TestToolAugmentedAgentTrace:
    def test_returns_agent_trace(self, synthetic_task_card: TaskCard) -> None:
        llm = MockLLM(responses=[_final_response()])
        trace = ToolAugmentedAgent().run(synthetic_task_card, llm)
        assert isinstance(trace, AgentTrace)

    def test_system_name(self) -> None:
        assert ToolAugmentedAgent.system_name == "system3_tool_aug"

    def test_no_retrieved_docs(self, synthetic_task_card: TaskCard) -> None:
        llm = MockLLM(responses=[_final_response()])
        trace = ToolAugmentedAgent().run(synthetic_task_card, llm)
        assert trace.retrieved_docs == []

    def test_decision_extracted(self, synthetic_task_card: TaskCard) -> None:
        llm = MockLLM(responses=[_final_response("NO-GO")])
        trace = ToolAugmentedAgent().run(synthetic_task_card, llm)
        assert trace.final_recommendation.decision == "NO-GO"


class TestToolAugmentedAgentToolCalls:
    def test_tool_call_logged(self, synthetic_task_card: TaskCard) -> None:
        # Turn 1: call echo_tool; Turn 2: produce final recommendation
        llm = MockLLM(responses=[
            _tool_call_response("echo_tool", {"message": "hello"}),
            _final_response("PROCEED"),
        ])
        trace = ToolAugmentedAgent().run(synthetic_task_card, llm)
        assert len(trace.tool_calls) == 1
        assert trace.tool_calls[0].name == "echo_tool"
        assert trace.tool_calls[0].args == {"message": "hello"}
        assert trace.tool_calls[0].result == "hello"
        assert trace.tool_calls[0].error is None

    def test_unknown_tool_error_logged(self, synthetic_task_card: TaskCard) -> None:
        llm = MockLLM(responses=[
            _tool_call_response("nonexistent_tool", {}),
            _final_response("ESCALATE"),
        ])
        trace = ToolAugmentedAgent().run(synthetic_task_card, llm)
        assert trace.had_tool_error is True
        assert trace.tool_calls[0].error is not None

    def test_multiple_tool_calls(self, synthetic_task_card: TaskCard) -> None:
        llm = MockLLM(responses=[
            _tool_call_response("echo_tool", {"message": "check1"}),
            _tool_call_response("echo_tool", {"message": "check2"}),
            _final_response("DELAY"),
        ])
        trace = ToolAugmentedAgent().run(synthetic_task_card, llm)
        assert len(trace.tool_calls) == 2

    def test_token_usage_accumulates_across_turns(self, synthetic_task_card: TaskCard) -> None:
        llm = MockLLM(
            responses=[_tool_call_response("echo_tool", {"message": "x"}), _final_response()],
            prompt_tokens_per_call=10,
            completion_tokens_per_call=5,
        )
        trace = ToolAugmentedAgent().run(synthetic_task_card, llm)
        # 2 LLM calls = 20 prompt + 10 completion
        assert trace.token_usage["prompt"] == 20
        assert trace.token_usage["completion"] == 10


class TestToolAugmentedAgentMaxTurns:
    def test_max_turns_exceeded_escalates(self, synthetic_task_card: TaskCard) -> None:
        # All responses are tool calls — never finalise
        llm = MockLLM(responses=[_tool_call_response("echo_tool", {"message": "x"})])
        agent = ToolAugmentedAgent(max_turns=3)
        trace = agent.run(synthetic_task_card, llm)
        assert trace.requested_escalation is True
        assert "MAX TURNS" in trace.final_recommendation.rationale

    def test_parse_error_escalates(self, synthetic_task_card: TaskCard) -> None:
        llm = MockLLM(responses=["this is not json"])
        trace = ToolAugmentedAgent().run(synthetic_task_card, llm)
        assert trace.had_parse_error is True
        assert trace.requested_escalation is True

    def test_llm_error_propagates(self, synthetic_task_card: TaskCard) -> None:
        llm = MockLLM(responses=[RuntimeError("timeout")])
        with pytest.raises(RuntimeError, match="timeout"):
            ToolAugmentedAgent().run(synthetic_task_card, llm)


class TestToolAugmentedAgentEscalation:
    def test_escalation_flag_propagated(self, synthetic_task_card: TaskCard) -> None:
        llm = MockLLM(responses=[_final_response(escalate=True)])
        trace = ToolAugmentedAgent().run(synthetic_task_card, llm)
        assert trace.requested_escalation is True
