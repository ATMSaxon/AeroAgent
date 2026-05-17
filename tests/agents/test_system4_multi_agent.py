"""
Unit tests for System 4: MultiAgentSystem.

All LLM calls use MockLLM. No real API calls.
"""

from __future__ import annotations

import json

import pytest

from aerosafety.agents.mock_llm import MockLLM
from aerosafety.agents.system4_multi_agent import MultiAgentSystem
from aerosafety.io import AgentTrace, TaskCard


def _ops_analyst_response() -> str:
    return json.dumps({
        "role": "operations_analyst",
        "operational_facts": ["runway 09/27 closed per NOTAM", "departure at 14:00Z"],
        "missing_information": [],
        "operational_risks": ["departure runway unavailable"],
        "notes": "Runway closure directly affects planned departure.",
    })


def _safety_officer_response(escalate: bool = False) -> str:
    return json.dumps({
        "role": "safety_officer",
        "applicable_safety_constraints": ["NOTAM must be complied with"],
        "potential_violations": ["departing on closed runway"],
        "severity_assessment": "Critical",
        "escalation_warranted": escalate,
        "notes": "Operation must not proceed.",
    })


def _regulation_specialist_response() -> str:
    return json.dumps({
        "role": "regulation_specialist",
        "applicable_regulations": ["FAR 91.137"],
        "compliance_assessment": "NON-COMPLIANT",
        "ambiguities": [],
        "notes": "Departure prohibited.",
    })


def _tool_use_agent_response() -> str:
    return json.dumps({
        "role": "tool_use_agent",
        "tools_invoked": [],
        "computed_values": {},
        "tool_errors": [],
        "notes": "No tools needed for this determination.",
    })


def _final_decision_response(decision: str = "NO-GO", escalate: bool = False) -> str:
    return json.dumps({
        "role": "final_decision_agent",
        "decision": decision,
        "rationale": "Runway is closed per NOTAM; departure must not proceed.",
        "safety_constraints_cited": ["NOTAM closure"],
        "evidence_cited": ["NOTAM 2024-001"],
        "escalation_recommended": escalate,
        "uncertainty_flags": [],
    })


def _make_five_role_responses(**kwargs) -> list[str]:
    return [
        _ops_analyst_response(),
        _safety_officer_response(escalate=kwargs.get("escalate", False)),
        _regulation_specialist_response(),
        _tool_use_agent_response(),
        _final_decision_response(
            decision=kwargs.get("decision", "NO-GO"),
            escalate=kwargs.get("escalate", False),
        ),
    ]


class TestMultiAgentSystemTrace:
    def test_returns_agent_trace(self, synthetic_task_card: TaskCard) -> None:
        llm = MockLLM(responses=_make_five_role_responses())
        trace = MultiAgentSystem().run(synthetic_task_card, llm)
        assert isinstance(trace, AgentTrace)

    def test_system_name(self) -> None:
        assert MultiAgentSystem.system_name == "system4_multi_agent"

    def test_five_llm_calls(self, synthetic_task_card: TaskCard) -> None:
        llm = MockLLM(responses=_make_five_role_responses())
        MultiAgentSystem().run(synthetic_task_card, llm)
        assert llm.call_count == 5

    def test_decision_extracted(self, synthetic_task_card: TaskCard) -> None:
        llm = MockLLM(responses=_make_five_role_responses(decision="NO-GO"))
        trace = MultiAgentSystem().run(synthetic_task_card, llm)
        assert trace.final_recommendation.decision == "NO-GO"

    def test_no_retrieved_docs(self, synthetic_task_card: TaskCard) -> None:
        llm = MockLLM(responses=_make_five_role_responses())
        trace = MultiAgentSystem().run(synthetic_task_card, llm)
        assert trace.retrieved_docs == []

    def test_token_usage_accumulates_all_roles(self, synthetic_task_card: TaskCard) -> None:
        llm = MockLLM(
            responses=_make_five_role_responses(),
            prompt_tokens_per_call=20,
            completion_tokens_per_call=10,
        )
        trace = MultiAgentSystem().run(synthetic_task_card, llm)
        # 5 LLM calls = 100 prompt + 50 completion
        assert trace.token_usage["prompt"] == 100
        assert trace.token_usage["completion"] == 50

    def test_role_tagged_messages_in_trace(self, synthetic_task_card: TaskCard) -> None:
        llm = MockLLM(responses=_make_five_role_responses())
        trace = MultiAgentSystem().run(synthetic_task_card, llm)
        role_tags = [m.get("role_tag") for m in trace.messages if m.get("role_tag")]
        assert "operations_analyst" in role_tags
        assert "safety_officer" in role_tags
        assert "regulation_specialist" in role_tags
        assert "tool_use_agent" in role_tags
        assert "final_decision_agent" in role_tags


class TestMultiAgentSystemEscalation:
    def test_intermediate_escalation_propagates_to_final(self, synthetic_task_card: TaskCard) -> None:
        # Safety officer flags escalation; final agent does not — but should inherit
        responses = [
            _ops_analyst_response(),
            _safety_officer_response(escalate=True),
            _regulation_specialist_response(),
            _tool_use_agent_response(),
            _final_decision_response(decision="NO-GO", escalate=False),
        ]
        llm = MockLLM(responses=responses)
        trace = MultiAgentSystem().run(synthetic_task_card, llm)
        # escalation_warranted from safety_officer OR escalation_recommended from final
        assert trace.requested_escalation is True

    def test_llm_error_propagates(self, synthetic_task_card: TaskCard) -> None:
        llm = MockLLM(responses=[RuntimeError("LLM down")])
        with pytest.raises(RuntimeError, match="LLM down"):
            MultiAgentSystem().run(synthetic_task_card, llm)


class TestMultiAgentSystemParseFailure:
    def test_final_parse_error_escalates(self, synthetic_task_card: TaskCard) -> None:
        responses = [
            _ops_analyst_response(),
            _safety_officer_response(),
            _regulation_specialist_response(),
            _tool_use_agent_response(),
            "this is not json",
        ]
        llm = MockLLM(responses=responses)
        trace = MultiAgentSystem().run(synthetic_task_card, llm)
        assert trace.had_parse_error is True
        assert trace.requested_escalation is True

    def test_intermediate_parse_error_flagged_but_continues(self, synthetic_task_card: TaskCard) -> None:
        responses = [
            "not json",  # ops_analyst fails
            _safety_officer_response(),
            _regulation_specialist_response(),
            _tool_use_agent_response(),
            _final_decision_response(),
        ]
        llm = MockLLM(responses=responses)
        trace = MultiAgentSystem().run(synthetic_task_card, llm)
        assert trace.had_parse_error is True
        # System should still produce a trace, not crash
        assert isinstance(trace, AgentTrace)
