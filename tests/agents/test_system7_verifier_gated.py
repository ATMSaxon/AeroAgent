"""
Unit tests for System 7: VerifierGatedAgent.

All LLM calls use MockLLM. No real API calls.
Verifier independence enforced: verifiers receive only AgentTrace + TaskCard.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from aerosafety.agents.mock_llm import MockLLM
from aerosafety.agents.system7_verifier_gated import (
    EscalationVerifier,
    EvidenceVerifier,
    NumericalVerifier,
    RuleVerifier,
    SafetyConstraintVerifier,
    ToolUseVerifier,
    VerifierBase,
    VerifierGatedAgent,
    VerifierResult,
)
from aerosafety.io import AgentTrace, TaskCard

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _primary_agent_final_response(decision: str = "PROCEED") -> str:
    return json.dumps({
        "action": "final",
        "decision": decision,
        "rationale": "All checks passed.",
        "safety_constraints_cited": ["wind_limit"],
        "evidence_cited": ["METAR"],
        "escalation_recommended": False,
        "uncertainty_flags": [],
    })


def _verifier_pass_response() -> str:
    return json.dumps({
        "passed": True,
        "violated_constraints": [],
        "severity": "Low",
        "notes": "All checks passed.",
    })


def _verifier_fail_response(severity: str = "Critical") -> str:
    return json.dumps({
        "passed": False,
        "violated_constraints": ["missing_constraint"],
        "severity": severity,
        "notes": "Constraint was omitted.",
    })


class _PassVerifier(VerifierBase):
    name = "always_pass"

    def verify(self, trace: AgentTrace, task: TaskCard, llm: Any) -> VerifierResult:
        return VerifierResult(
            verifier_name=self.name,
            passed=True,
            violated_constraints=[],
            severity="Low",
            notes="Stub always-pass verifier.",
        )


class _FailVerifier(VerifierBase):
    def __init__(self, severity: str = "Critical") -> None:
        self._severity = severity

    name = "always_fail"

    def verify(self, trace: AgentTrace, task: TaskCard, llm: Any) -> VerifierResult:
        return VerifierResult(
            verifier_name=self.name,
            passed=False,
            violated_constraints=["test_violation"],
            severity=self._severity,
            notes="Stub always-fail verifier.",
        )


# ---------------------------------------------------------------------------
# VerifierResult tests
# ---------------------------------------------------------------------------

class TestVerifierResult:
    def test_to_dict(self) -> None:
        vr = VerifierResult(
            verifier_name="test_v",
            passed=True,
            violated_constraints=[],
            severity="Low",
            notes="ok",
        )
        d = vr.to_dict()
        assert d["verifier_name"] == "test_v"
        assert d["passed"] is True
        assert d["severity"] == "Low"


# ---------------------------------------------------------------------------
# VerifierGatedAgent basic trace tests
# ---------------------------------------------------------------------------

class TestVerifierGatedAgentTrace:
    def test_returns_agent_trace(self, synthetic_task_card: TaskCard) -> None:
        primary_resp = _primary_agent_final_response("NO-GO")
        llm = MockLLM(responses=[primary_resp])
        agent = VerifierGatedAgent(verifiers=[_PassVerifier()])
        trace = agent.run(synthetic_task_card, llm)
        assert isinstance(trace, AgentTrace)

    def test_system_name(self) -> None:
        assert VerifierGatedAgent.system_name == "system7_verifier_gated"

    def test_verifier_messages_appended(self, synthetic_task_card: TaskCard) -> None:
        primary_resp = _primary_agent_final_response("PROCEED")
        llm = MockLLM(responses=[primary_resp])
        agent = VerifierGatedAgent(verifiers=[_PassVerifier()])
        trace = agent.run(synthetic_task_card, llm)
        verifier_msgs = [m for m in trace.messages if m.get("role") == "verifier"]
        assert len(verifier_msgs) == 1
        assert verifier_msgs[0]["verifier_name"] == "always_pass"

    def test_pass_verifier_preserves_decision(self, synthetic_task_card: TaskCard) -> None:
        primary_resp = _primary_agent_final_response("NO-GO")
        llm = MockLLM(responses=[primary_resp])
        agent = VerifierGatedAgent(verifiers=[_PassVerifier()])
        trace = agent.run(synthetic_task_card, llm)
        assert trace.final_recommendation.decision == "NO-GO"

    def test_task_id_propagated(self, synthetic_task_card: TaskCard) -> None:
        llm = MockLLM(responses=[_primary_agent_final_response()])
        agent = VerifierGatedAgent(verifiers=[_PassVerifier()])
        trace = agent.run(synthetic_task_card, llm)
        assert trace.task_id == synthetic_task_card.task_id


# ---------------------------------------------------------------------------
# Verifier override tests
# ---------------------------------------------------------------------------

class TestVerifierGatedOverride:
    def test_critical_fail_overrides_to_escalate(self, synthetic_task_card: TaskCard) -> None:
        primary_resp = _primary_agent_final_response("PROCEED")
        llm = MockLLM(responses=[primary_resp])
        agent = VerifierGatedAgent(verifiers=[_FailVerifier(severity="Critical")])
        trace = agent.run(synthetic_task_card, llm)
        assert trace.final_recommendation.decision == "ESCALATE"
        assert trace.requested_escalation is True

    def test_high_fail_overrides_to_escalate(self, synthetic_task_card: TaskCard) -> None:
        primary_resp = _primary_agent_final_response("PROCEED")
        llm = MockLLM(responses=[primary_resp])
        agent = VerifierGatedAgent(verifiers=[_FailVerifier(severity="High")])
        trace = agent.run(synthetic_task_card, llm)
        assert trace.final_recommendation.decision == "ESCALATE"

    def test_low_fail_does_not_override(self, synthetic_task_card: TaskCard) -> None:
        primary_resp = _primary_agent_final_response("NO-GO")
        llm = MockLLM(responses=[primary_resp])
        agent = VerifierGatedAgent(
            verifiers=[_FailVerifier(severity="Low")],
            escalate_on_severities=("Critical", "High"),
        )
        trace = agent.run(synthetic_task_card, llm)
        assert trace.final_recommendation.decision == "NO-GO"

    def test_override_rationale_mentions_verifier(self, synthetic_task_card: TaskCard) -> None:
        primary_resp = _primary_agent_final_response("PROCEED")
        llm = MockLLM(responses=[primary_resp])
        agent = VerifierGatedAgent(verifiers=[_FailVerifier(severity="Critical")])
        trace = agent.run(synthetic_task_card, llm)
        assert "VERIFIER OVERRIDE" in trace.final_recommendation.rationale

    def test_confidence_zero_on_override(self, synthetic_task_card: TaskCard) -> None:
        primary_resp = _primary_agent_final_response("PROCEED")
        llm = MockLLM(responses=[primary_resp])
        agent = VerifierGatedAgent(verifiers=[_FailVerifier(severity="Critical")])
        trace = agent.run(synthetic_task_card, llm)
        assert trace.confidence == 0.0

    def test_multiple_verifiers_all_run(self, synthetic_task_card: TaskCard) -> None:
        primary_resp = _primary_agent_final_response("PROCEED")
        llm = MockLLM(responses=[primary_resp])
        agent = VerifierGatedAgent(verifiers=[_PassVerifier(), _PassVerifier()])
        trace = agent.run(synthetic_task_card, llm)
        verifier_msgs = [m for m in trace.messages if m.get("role") == "verifier"]
        assert len(verifier_msgs) == 2


# ---------------------------------------------------------------------------
# LLM-judge verifier tests (using MockLLM for judge calls)
# ---------------------------------------------------------------------------

class TestLLMJudgeVerifiers:
    """Test the LLM-judge verifiers using MockLLM for their LLM calls."""

    def test_evidence_verifier_pass(self, minimal_agent_trace: AgentTrace, synthetic_task_card: TaskCard) -> None:
        llm = MockLLM(responses=[_verifier_pass_response()])
        verifier = EvidenceVerifier()
        result = verifier.verify(minimal_agent_trace, synthetic_task_card, llm)
        assert result.passed is True
        assert result.verifier_name == "evidence_verifier"

    def test_evidence_verifier_fail(self, minimal_agent_trace: AgentTrace, synthetic_task_card: TaskCard) -> None:
        llm = MockLLM(responses=[_verifier_fail_response()])
        verifier = EvidenceVerifier()
        result = verifier.verify(minimal_agent_trace, synthetic_task_card, llm)
        assert result.passed is False
        assert "missing_constraint" in result.violated_constraints

    def test_rule_verifier_pass(self, minimal_agent_trace: AgentTrace, synthetic_task_card: TaskCard) -> None:
        llm = MockLLM(responses=[_verifier_pass_response()])
        result = RuleVerifier().verify(minimal_agent_trace, synthetic_task_card, llm)
        assert result.passed is True
        assert result.verifier_name == "rule_verifier"

    def test_numerical_verifier_pass(self, minimal_agent_trace: AgentTrace, synthetic_task_card: TaskCard) -> None:
        llm = MockLLM(responses=[_verifier_pass_response()])
        result = NumericalVerifier().verify(minimal_agent_trace, synthetic_task_card, llm)
        assert result.passed is True
        assert result.verifier_name == "numerical_verifier"

    def test_tool_use_verifier_pass(self, minimal_agent_trace: AgentTrace, synthetic_task_card: TaskCard) -> None:
        llm = MockLLM(responses=[_verifier_pass_response()])
        result = ToolUseVerifier().verify(minimal_agent_trace, synthetic_task_card, llm)
        assert result.passed is True
        assert result.verifier_name == "tool_use_verifier"

    def test_safety_constraint_verifier_pass(self, minimal_agent_trace: AgentTrace, synthetic_task_card: TaskCard) -> None:
        llm = MockLLM(responses=[_verifier_pass_response()])
        result = SafetyConstraintVerifier().verify(minimal_agent_trace, synthetic_task_card, llm)
        assert result.passed is True
        assert result.verifier_name == "safety_constraint_verifier"

    def test_escalation_verifier_pass(self, minimal_agent_trace: AgentTrace, synthetic_task_card: TaskCard) -> None:
        llm = MockLLM(responses=[_verifier_pass_response()])
        result = EscalationVerifier().verify(minimal_agent_trace, synthetic_task_card, llm)
        assert result.passed is True
        assert result.verifier_name == "escalation_verifier"

    def test_verifier_parse_error_returns_fail(self, minimal_agent_trace: AgentTrace, synthetic_task_card: TaskCard) -> None:
        llm = MockLLM(responses=["this is not json"])
        result = EvidenceVerifier().verify(minimal_agent_trace, synthetic_task_card, llm)
        # Parse error should result in a fail, not crash
        assert result.passed is False
        assert "verifier_parse_error" in result.violated_constraints

    def test_verifier_llm_error_propagates(self, minimal_agent_trace: AgentTrace, synthetic_task_card: TaskCard) -> None:
        llm = MockLLM(responses=[RuntimeError("verifier LLM down")])
        with pytest.raises(RuntimeError, match="verifier LLM down"):
            EvidenceVerifier().verify(minimal_agent_trace, synthetic_task_card, llm)


# ---------------------------------------------------------------------------
# Phase 2 stubs
# ---------------------------------------------------------------------------

class TestPhase2Stubs:
    def test_system5_raises_not_implemented(self, synthetic_task_card: TaskCard) -> None:
        from aerosafety.agents.system5_aero_sft import AeroSFTAgent
        llm = MockLLM(responses=["unused"])
        with pytest.raises(NotImplementedError, match="Phase 2"):
            AeroSFTAgent().run(synthetic_task_card, llm)

    def test_system6_raises_not_implemented(self, synthetic_task_card: TaskCard) -> None:
        from aerosafety.agents.system6_aero_dpo import AeroDPOAgent
        llm = MockLLM(responses=["unused"])
        with pytest.raises(NotImplementedError, match="Phase 2"):
            AeroDPOAgent().run(synthetic_task_card, llm)
