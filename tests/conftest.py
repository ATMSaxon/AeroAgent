"""
Shared pytest fixtures for AeroSafetyEval test suite.

Conventions:
- All fixtures that touch the filesystem use tmp_path (pytest built-in).
- No fixture silently swallows errors — let them propagate.
- No fixture creates fake aviation data that could be mistaken for real data.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from aerosafety.io import (
    AgentTrace,
    Recommendation,
    RetrievedDoc,
    TaskCard,
    TaskProvenance,
    ToolCall,
)


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clear_eval_mode_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Ensure AEROSAFETY_EVAL_MODE is not set by accident during unit tests.

    Integration / eval tests that need deterministic mode should set it
    explicitly with monkeypatch.setenv("AEROSAFETY_EVAL_MODE", "1").
    """
    monkeypatch.delenv("AEROSAFETY_EVAL_MODE", raising=False)


# ---------------------------------------------------------------------------
# Minimal synthetic TaskCard (SYNTHETIC, clearly labelled)
# ---------------------------------------------------------------------------

@pytest.fixture()
def synthetic_task_card() -> TaskCard:
    """
    A minimal SYNTHETIC TaskCard for unit-testing schema validation.

    NOT a real aviation scenario — do not use as ground truth.
    """
    return TaskCard(
        task_id="SYNTHETIC-TEST-001",
        family="notam_compliance",
        task_type="A",
        prompt=(
            "[SYNTHETIC] Runway 09/27 is closed via NOTAM effective "
            "2024-01-15T10:00Z to 2024-01-15T18:00Z. "
            "A flight plans to depart at 2024-01-15T14:00Z on runway 09. "
            "Is this operation compliant?"
        ),
        gold_decision="No — the runway is closed during the planned departure time.",
        required_safety_constraints=[
            "NOTAM effective window must be checked against planned operation time.",
            "Closed runway must not be used for departure or landing.",
        ],
        acceptable_variants=["Non-compliant", "Not compliant"],
        evidence_requirements=["NOTAM effective time", "planned departure time"],
        severity="High",
        escalation_required=False,
        failure_mode_labels=["misread_notam_time", "utc_local_confusion"],
        provenance=TaskProvenance(
            source="SYNTHETIC",
            generation_rule=(
                "Constructed to test UTC time-window parsing in NOTAM compliance tasks. "
                "Not derived from any real operational event."
            ),
        ),
        split="dev",
    )


# ---------------------------------------------------------------------------
# Minimal AgentTrace
# ---------------------------------------------------------------------------

@pytest.fixture()
def minimal_agent_trace(synthetic_task_card: TaskCard) -> AgentTrace:
    """
    A minimal AgentTrace for unit-testing schema validation and logging.

    NOT a real model output.
    """
    return AgentTrace(
        task_id=synthetic_task_card.task_id,
        run_id="test-run-001",
        model_version="gpt-4o-2024-08-06",
        model_provider="openai",
        prompt_hash="a" * 64,  # placeholder hash — real runs compute via determinism.prompt_hash
        system_prompt="[TEST] You are an aviation safety evaluation assistant.",
        messages=[
            {"role": "user", "content": synthetic_task_card.prompt},
            {"role": "assistant", "content": "No — the runway is closed."},
        ],
        tool_calls=[
            ToolCall(
                name="notam_time_checker",
                args={"notam_start": "2024-01-15T10:00Z", "operation_time": "2024-01-15T14:00Z"},
                result={"within_window": True},
                error=None,
                runtime_ms=12.4,
            )
        ],
        retrieved_docs=[
            RetrievedDoc(
                doc_id="notam-example-001",
                source="SYNTHETIC",
                chunk_text="Runway 09/27 closed 1000Z to 1800Z 15 JAN 2024",
                score=0.97,
            )
        ],
        final_recommendation=Recommendation(
            decision="Non-compliant",
            rationale="Planned departure at 1400Z falls within the NOTAM closure window.",
            safety_constraints_cited=["NOTAM effective window"],
            evidence_cited=["NOTAM closing runway 09/27 1000Z–1800Z"],
            escalation_recommended=False,
            uncertainty_flags=[],
        ),
        raw_output="No — the runway is closed.",
        confidence=0.95,
        requested_escalation=False,
        total_runtime_ms=543.2,
        token_usage={"prompt": 210, "completion": 48, "total": 258},
        hardware={"hostname": "test-host", "platform": "test"},
        started_at="2024-01-15T09:00:00Z",
        finished_at="2024-01-15T09:00:00.543Z",
        had_tool_error=False,
        had_retrieval_error=False,
        had_parse_error=False,
    )


# ---------------------------------------------------------------------------
# Log directory fixture
# ---------------------------------------------------------------------------

@pytest.fixture()
def log_dir(tmp_path: Path) -> Path:
    """A temporary directory for ExperimentLogger output."""
    d = tmp_path / "logs"
    d.mkdir()
    return d
