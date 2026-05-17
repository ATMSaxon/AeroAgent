"""
Unit tests for aerosafety/eval/adapters.py

Tests the bridge between io.AgentTrace/TaskCard and EvalView.
"""

from __future__ import annotations

import pytest

from aerosafety.io import AgentTrace, Recommendation, TaskCard, TaskProvenance, ToolCall
from aerosafety.eval.adapters import (
    AnnotatedToolCall,
    EvalAnnotation,
    EvalTaskCard,
    EvalView,
    ToolCallAnnotation,
    make_eval_view,
)


def _make_task_card(task_id: str = "T001", severity: str = "High") -> TaskCard:
    return TaskCard(
        task_id=task_id,
        family="notam_compliance",
        task_type="D",
        prompt="[SYNTHETIC] Test prompt",
        gold_decision="no-go",
        required_safety_constraints=["constraint_a", "constraint_b"],
        severity=severity,
        escalation_required=False,
        provenance=TaskProvenance(source="SYNTHETIC", generation_rule="unit test"),
    )


def _make_trace(
    task_id: str = "T001",
    decision: str = "no-go",
    confidence: float | None = 0.9,
    token_total: int = 100,
    runtime_ms: float = 500.0,
    tools: list[ToolCall] | None = None,
) -> AgentTrace:
    return AgentTrace(
        task_id=task_id,
        run_id="run-001",
        model_version="test-model",
        model_provider="test",
        prompt_hash="a" * 64,
        system_prompt="[TEST]",
        messages=[],
        tool_calls=tools or [],
        final_recommendation=Recommendation(
            decision=decision,
            rationale="[TEST] rationale",
            safety_constraints_cited=["constraint_a"],
            evidence_cited=["evidence_x"],
        ),
        confidence=confidence,
        total_runtime_ms=runtime_ms,
        token_usage={"prompt": 50, "completion": 50, "total": token_total},
    )


class TestMakeEvalView:
    def test_basic_fields_mapped(self):
        trace = _make_trace()
        card = _make_task_card()
        eval_card = EvalTaskCard(task_card=card, required_tool_names=["metar_parser"])
        annotation = EvalAnnotation(unsafe_recommendation=False)

        view = make_eval_view(trace, annotation, eval_card)

        assert view.task_id == "T001"
        assert view.predicted_decision == "no-go"
        assert view.gold_decision == "no-go"
        assert view.confidence == 0.9
        assert view.unsafe_recommendation is False
        assert view.severity == "High"
        assert view.token_count == 100
        assert view.latency_seconds == 0.5

    def test_citations_combined_from_recommendation(self):
        trace = _make_trace()
        card = _make_task_card()
        eval_card = EvalTaskCard(task_card=card)
        annotation = EvalAnnotation(unsafe_recommendation=False)

        view = make_eval_view(trace, annotation, eval_card)
        assert "constraint_a" in view.citations
        assert "evidence_x" in view.citations

    def test_annotation_fields_propagated(self):
        trace = _make_trace()
        card = _make_task_card()
        eval_card = EvalTaskCard(task_card=card)
        annotation = EvalAnnotation(
            unsafe_recommendation=True,
            unsupported_claims=["claim_x"],
            hallucinated_evidence=["hal_1"],
            contradictions=["con_1"],
        )
        view = make_eval_view(trace, annotation, eval_card)
        assert view.unsafe_recommendation is True
        assert view.unsupported_claims == ["claim_x"]
        assert view.hallucinated_evidence == ["hal_1"]
        assert view.contradictions == ["con_1"]

    def test_raises_on_missing_unsafe_recommendation(self):
        trace = _make_trace()
        card = _make_task_card()
        eval_card = EvalTaskCard(task_card=card)
        annotation = EvalAnnotation(unsafe_recommendation=None)

        with pytest.raises(ValueError, match="unsafe_recommendation"):
            make_eval_view(trace, annotation, eval_card)

    def test_raises_on_task_id_mismatch(self):
        trace = _make_trace(task_id="T001")
        card = _make_task_card(task_id="T002")
        eval_card = EvalTaskCard(task_card=card)
        annotation = EvalAnnotation(unsafe_recommendation=False)

        with pytest.raises(ValueError, match="mismatch"):
            make_eval_view(trace, annotation, eval_card)

    def test_confidence_defaults_to_one_when_none(self):
        trace = _make_trace(confidence=None)
        card = _make_task_card()
        eval_card = EvalTaskCard(task_card=card)
        annotation = EvalAnnotation(unsafe_recommendation=False)
        view = make_eval_view(trace, annotation, eval_card)
        assert view.confidence == 1.0

    def test_tool_annotations_applied(self):
        tc = ToolCall(name="wind_calc", args={"bearing": 270, "speed": 15}, result=12.5)
        trace = _make_trace(tools=[tc])
        card = _make_task_card()
        eval_card = EvalTaskCard(task_card=card, required_tool_names=["wind_calc"])
        annotation = EvalAnnotation(
            unsafe_recommendation=False,
            tool_annotations=[
                ToolCallAnnotation(
                    tool_call_index=0,
                    correct_selection=True,
                    correct_input=False,
                    correct_interpretation=True,
                )
            ],
        )
        view = make_eval_view(trace, annotation, eval_card)
        assert len(view.tool_calls) == 1
        assert view.tool_calls[0].correct_input is False
        assert view.tool_calls[0].correct_selection is True

    def test_raw_output_used_when_no_recommendation(self):
        trace = AgentTrace(
            task_id="T001",
            run_id="r1",
            model_version="v1",
            model_provider="p",
            prompt_hash="a" * 64,
            system_prompt="s",
            messages=[],
            final_recommendation=None,
            raw_output="raw answer here",
        )
        card = _make_task_card()
        eval_card = EvalTaskCard(task_card=card)
        annotation = EvalAnnotation(unsafe_recommendation=False)
        view = make_eval_view(trace, annotation, eval_card)
        assert view.predicted_decision == "raw answer here"
