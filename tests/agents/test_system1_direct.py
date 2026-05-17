"""
Unit tests for System 1: DirectLLMAgent.

All LLM calls use MockLLM. No real API calls.
"""

from __future__ import annotations

import json

import pytest

from aerosafety.agents.mock_llm import MockLLM
from aerosafety.agents.system1_direct import DirectLLMAgent
from aerosafety.io import AgentTrace, TaskCard


def _make_valid_response(decision: str = "NO-GO", escalate: bool = False) -> str:
    return json.dumps({
        "decision": decision,
        "rationale": "Test rationale.",
        "safety_constraints_cited": ["constraint_A"],
        "evidence_cited": ["evidence_B"],
        "escalation_recommended": escalate,
        "uncertainty_flags": [],
    })


class TestDirectLLMAgentTrace:
    def test_returns_agent_trace(self, synthetic_task_card: TaskCard) -> None:
        llm = MockLLM(responses=[_make_valid_response()])
        agent = DirectLLMAgent()
        trace = agent.run(synthetic_task_card, llm)
        assert isinstance(trace, AgentTrace)

    def test_system_name(self) -> None:
        assert DirectLLMAgent.system_name == "system1_direct"

    def test_task_id_propagated(self, synthetic_task_card: TaskCard) -> None:
        llm = MockLLM(responses=[_make_valid_response()])
        trace = DirectLLMAgent().run(synthetic_task_card, llm)
        assert trace.task_id == synthetic_task_card.task_id

    def test_no_retrieved_docs(self, synthetic_task_card: TaskCard) -> None:
        llm = MockLLM(responses=[_make_valid_response()])
        trace = DirectLLMAgent().run(synthetic_task_card, llm)
        assert trace.retrieved_docs == []

    def test_no_tool_calls(self, synthetic_task_card: TaskCard) -> None:
        llm = MockLLM(responses=[_make_valid_response()])
        trace = DirectLLMAgent().run(synthetic_task_card, llm)
        assert trace.tool_calls == []

    def test_decision_extracted(self, synthetic_task_card: TaskCard) -> None:
        llm = MockLLM(responses=[_make_valid_response(decision="NO-GO")])
        trace = DirectLLMAgent().run(synthetic_task_card, llm)
        assert trace.final_recommendation is not None
        assert trace.final_recommendation.decision == "NO-GO"

    def test_escalation_flag_false_when_not_set(self, synthetic_task_card: TaskCard) -> None:
        llm = MockLLM(responses=[_make_valid_response(escalate=False)])
        trace = DirectLLMAgent().run(synthetic_task_card, llm)
        assert trace.requested_escalation is False

    def test_escalation_flag_true_when_set(self, synthetic_task_card: TaskCard) -> None:
        llm = MockLLM(responses=[_make_valid_response(escalate=True)])
        trace = DirectLLMAgent().run(synthetic_task_card, llm)
        assert trace.requested_escalation is True

    def test_token_usage_recorded(self, synthetic_task_card: TaskCard) -> None:
        llm = MockLLM(responses=[_make_valid_response()], prompt_tokens_per_call=80, completion_tokens_per_call=30)
        trace = DirectLLMAgent().run(synthetic_task_card, llm)
        assert trace.token_usage is not None
        assert trace.token_usage["prompt"] == 80
        assert trace.token_usage["completion"] == 30
        assert trace.token_usage["total"] == 110

    def test_prompt_hash_is_hex_string(self, synthetic_task_card: TaskCard) -> None:
        llm = MockLLM(responses=[_make_valid_response()])
        trace = DirectLLMAgent().run(synthetic_task_card, llm)
        assert len(trace.prompt_hash) == 64
        assert all(c in "0123456789abcdef" for c in trace.prompt_hash)

    def test_runtime_ms_positive(self, synthetic_task_card: TaskCard) -> None:
        llm = MockLLM(responses=[_make_valid_response()])
        trace = DirectLLMAgent().run(synthetic_task_card, llm)
        assert trace.total_runtime_ms is not None
        assert trace.total_runtime_ms >= 0

    def test_started_at_and_finished_at_set(self, synthetic_task_card: TaskCard) -> None:
        llm = MockLLM(responses=[_make_valid_response()])
        trace = DirectLLMAgent().run(synthetic_task_card, llm)
        assert trace.started_at is not None
        assert trace.finished_at is not None

    def test_raw_output_preserved(self, synthetic_task_card: TaskCard) -> None:
        raw = _make_valid_response()
        llm = MockLLM(responses=[raw])
        trace = DirectLLMAgent().run(synthetic_task_card, llm)
        assert trace.raw_output == raw


class TestDirectLLMAgentParseFailure:
    def test_parse_error_flagged(self, synthetic_task_card: TaskCard) -> None:
        llm = MockLLM(responses=["this is not json at all"])
        trace = DirectLLMAgent().run(synthetic_task_card, llm)
        assert trace.had_parse_error is True

    def test_parse_error_escalates(self, synthetic_task_card: TaskCard) -> None:
        llm = MockLLM(responses=["this is not json at all"])
        trace = DirectLLMAgent().run(synthetic_task_card, llm)
        assert trace.requested_escalation is True
        assert trace.final_recommendation is not None
        assert trace.final_recommendation.decision == "UNCERTAIN"

    def test_parse_error_confidence_zero(self, synthetic_task_card: TaskCard) -> None:
        llm = MockLLM(responses=["not json"])
        trace = DirectLLMAgent().run(synthetic_task_card, llm)
        assert trace.confidence == 0.0

    def test_llm_error_propagates(self, synthetic_task_card: TaskCard) -> None:
        llm = MockLLM(responses=[RuntimeError("API failure")])
        agent = DirectLLMAgent()
        with pytest.raises(RuntimeError, match="API failure"):
            agent.run(synthetic_task_card, llm)


class TestDirectLLMAgentUncertain:
    def test_uncertain_decision_confidence_zero(self, synthetic_task_card: TaskCard) -> None:
        llm = MockLLM(responses=[_make_valid_response(decision="UNCERTAIN")])
        trace = DirectLLMAgent().run(synthetic_task_card, llm)
        assert trace.confidence == 0.0

    def test_non_uncertain_decision_confidence_nonzero(self, synthetic_task_card: TaskCard) -> None:
        llm = MockLLM(responses=[_make_valid_response(decision="PROCEED")])
        trace = DirectLLMAgent().run(synthetic_task_card, llm)
        assert trace.confidence is not None
        assert trace.confidence > 0
