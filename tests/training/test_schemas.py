"""
Unit tests for aerosafety/training/schemas.py — Pydantic schema round-trips.

No LLM calls, no file I/O beyond what Pydantic does internally.
"""

from __future__ import annotations

import json

import pytest

from aerosafety.training.schemas import (
    DatasetManifest,
    DPOPair,
    SFTExample,
    VerifierExample,
)


class TestSFTExample:
    def test_round_trip(self) -> None:
        ex = SFTExample(
            instruction="Analyse this NOTAM.",
            input="NOTAM Q) KZNY/QMRLC/IV/NBO/A",
            output="Decision: NO-GO\n\nRationale: Runway closed.",
            source_task_id="NC-A-001",
            source_family="notam_compliance",
            source_split="dev",
        )
        data = json.loads(ex.model_dump_json())
        restored = SFTExample.model_validate(data)
        assert restored.source_task_id == "NC-A-001"
        assert restored.output == ex.output

    def test_license_tag(self) -> None:
        ex = SFTExample(
            instruction="I", input="X", output="O",
            source_task_id="T1", source_family="f", source_split="dev",
        )
        assert ex.license == "PILOT — NOT EXPERT-REVIEWED"

    def test_generation_method_fixed(self) -> None:
        ex = SFTExample(
            instruction="I", input="X", output="O",
            source_task_id="T1", source_family="f", source_split="dev",
        )
        assert ex.generation_method == "gold_card_expansion"

    def test_generation_timestamp_present(self) -> None:
        ex = SFTExample(
            instruction="I", input="X", output="O",
            source_task_id="T1", source_family="f", source_split="dev",
        )
        assert ex.generation_timestamp  # non-empty string


class TestDPOPair:
    def _valid_pair(self, **kwargs) -> DPOPair:
        defaults = dict(
            prompt="Scenario X.",
            chosen="Decision: NO-GO\nSafety: runway closed.",
            rejected="Decision: PROCEED\n(no constraints cited)",
            source_task_id="NC-A-001",
            source_family="notam_compliance",
            source_split="dev",
            generation_method="synthetic_gold_vs_worst_case",
            synthetic_generation_rule="Gold = NO-GO; rejected = worst-case PROCEED with no constraints.",
            partial_implementation=True,
        )
        defaults.update(kwargs)
        return DPOPair(**defaults)

    def test_round_trip(self) -> None:
        pair = self._valid_pair()
        data = json.loads(pair.model_dump_json())
        restored = DPOPair.model_validate(data)
        assert restored.source_task_id == "NC-A-001"
        assert restored.partial_implementation is True

    def test_synthetic_rule_required_for_synthetic_method(self) -> None:
        with pytest.raises(Exception, match="synthetic_generation_rule"):
            DPOPair(
                prompt="P", chosen="C", rejected="R",
                source_task_id="T1", source_family="f", source_split="dev",
                generation_method="synthetic_gold_vs_worst_case",
                synthetic_generation_rule=None,   # missing — must raise
            )

    def test_license_tag(self) -> None:
        pair = self._valid_pair()
        assert pair.license == "PILOT — NOT EXPERT-REVIEWED"

    def test_partial_implementation_flag(self) -> None:
        pair = self._valid_pair()
        assert pair.partial_implementation is True

    def test_agent_trace_method_no_rule_required(self) -> None:
        # agent_trace_pair method does not require synthetic_generation_rule
        pair = DPOPair(
            prompt="P", chosen="C", rejected="R",
            source_task_id="T1", source_family="f", source_split="dev",
            generation_method="agent_trace_pair",
            synthetic_generation_rule=None,
        )
        assert pair.generation_method == "agent_trace_pair"


class TestVerifierExample:
    def _valid_example(self, label="pass", **kwargs) -> VerifierExample:
        defaults = dict(
            trace_features={"predicted_decision": "NO-GO", "synthetic": True},
            label=label,
            violated_constraint=None if label == "pass" else "runway_closure",
            severity="High",
            missing_evidence_type=None if label == "pass" else "safety_constraint_omission",
            source_task_id="NC-A-001",
            source_family="notam_compliance",
            source_split="dev",
            generation_method="synthetic_gold_derivation",
            synthetic_generation_rule="Gold pass/fail from card fields.",
            partial_implementation=True,
        )
        defaults.update(kwargs)
        return VerifierExample(**defaults)

    def test_round_trip_pass(self) -> None:
        ex = self._valid_example("pass")
        data = json.loads(ex.model_dump_json())
        restored = VerifierExample.model_validate(data)
        assert restored.label == "pass"
        assert restored.violated_constraint is None

    def test_round_trip_fail(self) -> None:
        ex = self._valid_example("fail")
        data = json.loads(ex.model_dump_json())
        restored = VerifierExample.model_validate(data)
        assert restored.label == "fail"
        assert restored.violated_constraint == "runway_closure"

    def test_round_trip_needs_escalation(self) -> None:
        ex = self._valid_example("needs_escalation", violated_constraint="escalation_required",
                                 missing_evidence_type="missed_escalation")
        data = json.loads(ex.model_dump_json())
        restored = VerifierExample.model_validate(data)
        assert restored.label == "needs_escalation"

    def test_synthetic_rule_required(self) -> None:
        with pytest.raises(Exception, match="synthetic_generation_rule"):
            VerifierExample(
                trace_features={}, label="pass", violated_constraint=None,
                severity="High", missing_evidence_type=None,
                source_task_id="T1", source_family="f", source_split="dev",
                generation_method="synthetic_gold_derivation",
                synthetic_generation_rule=None,  # missing — must raise
            )

    def test_license_tag(self) -> None:
        ex = self._valid_example()
        assert ex.license == "PILOT — NOT EXPERT-REVIEWED"


class TestDatasetManifest:
    def test_round_trip(self) -> None:
        m = DatasetManifest(
            kind="sft",
            output_path="/tmp/sft.jsonl",
            n_examples=42,
            source_task_families=["notam_compliance"],
            source_splits_included=["dev"],
            generation_method="gold_card_expansion",
            partial_implementation=False,
            partial_implementation_notes="Deterministic gold expansion.",
        )
        data = json.loads(m.model_dump_json())
        restored = DatasetManifest.model_validate(data)
        assert restored.n_examples == 42
        assert restored.kind == "sft"
