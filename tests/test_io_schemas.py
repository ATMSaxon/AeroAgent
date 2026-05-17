"""Smoke tests for aerosafety.io Pydantic schemas."""

import pytest
from pydantic import ValidationError

from aerosafety.io import AgentTrace, TaskCard, ToolCall


def test_task_card_round_trip(synthetic_task_card: TaskCard) -> None:
    data = synthetic_task_card.model_dump()
    rebuilt = TaskCard.model_validate(data)
    assert rebuilt.task_id == synthetic_task_card.task_id
    assert rebuilt.severity == synthetic_task_card.severity


def test_task_card_requires_provenance() -> None:
    with pytest.raises((ValidationError, TypeError)):
        TaskCard(
            task_id="X",
            family="x",
            task_type="A",
            prompt="p",
            gold_decision="g",
            required_safety_constraints=[],
            severity="Low",
            escalation_required=False,
        )


def test_agent_trace_confidence_bounds(minimal_agent_trace: AgentTrace) -> None:
    assert minimal_agent_trace.confidence is not None
    assert 0.0 <= minimal_agent_trace.confidence <= 1.0


def test_agent_trace_confidence_out_of_range(minimal_agent_trace: AgentTrace) -> None:
    data = minimal_agent_trace.model_dump()
    data["confidence"] = 1.5
    with pytest.raises(ValidationError):
        AgentTrace.model_validate(data)


def test_tool_call_error_field() -> None:
    tc = ToolCall(name="test_tool", args={}, result=None, error="timeout", runtime_ms=5000.0)
    assert tc.error == "timeout"
