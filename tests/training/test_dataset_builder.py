"""
Integration tests for aerosafety/training/dataset_builder.py.

Uses synthetic TaskCards — no real TaskCard files required.
Verifies output shape, lineage, PARTIAL IMPLEMENTATION flags, and leakage guards.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aerosafety.io import TaskCard, TaskProvenance
from aerosafety.training.dataset_builder import (
    build_dpo_preference_pairs,
    build_sft_dataset,
    build_verifier_dataset,
)
from aerosafety.training.schemas import DPOPair, SFTExample, VerifierExample
from aerosafety.training.splits import SplitLeakageError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _card(
    task_id: str = "NC-A-001",
    split: str = "dev",
    escalation_required: bool = False,
    gold_decision: str = "NO-GO",
    family: str = "notam_compliance",
) -> TaskCard:
    return TaskCard(
        task_id=task_id,
        family=family,
        task_type="A",
        prompt=f"[SYNTHETIC] Task {task_id}.",
        gold_decision=gold_decision,
        required_safety_constraints=["runway_closure_notam", "far_91_137"],
        evidence_requirements=["FAA JO 7930.2S Appendix A"],
        severity="High",
        escalation_required=escalation_required,
        provenance=TaskProvenance(source="SYNTHETIC", generation_rule="unit test"),
        split=split,
    )


@pytest.fixture()
def dev_cards() -> list[TaskCard]:
    return [
        _card("NC-A-001", "dev"),
        _card("NC-A-002", "dev", gold_decision="PROCEED"),
        _card("WD-B-001", "dev", family="weather_dispatch"),
    ]


@pytest.fixture()
def mixed_cards() -> list[TaskCard]:
    """Mix of dev and test cards — test cards must be filtered out."""
    return [
        _card("NC-A-001", "dev"),
        _card("NC-TEST-001", "test"),
        _card("WD-B-001", "dev"),
    ]


# ---------------------------------------------------------------------------
# SFT
# ---------------------------------------------------------------------------

class TestBuildSFTDataset:
    def test_output_file_created(self, dev_cards, tmp_path) -> None:
        out, _ = build_sft_dataset(dev_cards, tmp_path / "sft.jsonl")
        assert out.exists()

    def test_one_example_per_dev_card(self, dev_cards, tmp_path) -> None:
        out, manifest = build_sft_dataset(dev_cards, tmp_path / "sft.jsonl")
        lines = [l for l in out.read_text().splitlines() if l.strip()]
        assert len(lines) == len(dev_cards)
        assert manifest.n_examples == len(dev_cards)

    def test_output_schema_valid(self, dev_cards, tmp_path) -> None:
        out, _ = build_sft_dataset(dev_cards, tmp_path / "sft.jsonl")
        for line in out.read_text().splitlines():
            if not line.strip():
                continue
            ex = SFTExample.model_validate(json.loads(line))
            assert ex.instruction
            assert ex.input
            assert ex.output

    def test_lineage_recorded(self, dev_cards, tmp_path) -> None:
        out, _ = build_sft_dataset(dev_cards, tmp_path / "sft.jsonl")
        for line in out.read_text().splitlines():
            if not line.strip():
                continue
            ex = SFTExample.model_validate(json.loads(line))
            assert ex.source_task_id
            assert ex.source_family
            assert ex.source_split == "dev"

    def test_license_tag_present(self, dev_cards, tmp_path) -> None:
        out, _ = build_sft_dataset(dev_cards, tmp_path / "sft.jsonl")
        lines = [l for l in out.read_text().splitlines() if l.strip()]
        ex = SFTExample.model_validate(json.loads(lines[0]))
        assert "PILOT" in ex.license

    def test_manifest_written(self, dev_cards, tmp_path) -> None:
        out, manifest = build_sft_dataset(dev_cards, tmp_path / "sft.jsonl")
        manifest_path = out.with_suffix(".manifest.json")
        assert manifest_path.exists()
        data = json.loads(manifest_path.read_text())
        assert data["kind"] == "sft"
        assert data["n_examples"] == len(dev_cards)

    def test_manifest_lineage(self, dev_cards, tmp_path) -> None:
        _, manifest = build_sft_dataset(dev_cards, tmp_path / "sft.jsonl")
        assert "notam_compliance" in manifest.source_task_families
        assert "test" not in manifest.source_splits_included

    def test_test_cards_in_input_raises_leakage_error(self, mixed_cards, tmp_path) -> None:
        # Passing a mix with any test card must raise — callers must pre-filter.
        with pytest.raises(SplitLeakageError):
            build_sft_dataset(mixed_cards, tmp_path / "sft.jsonl")

    def test_gold_decision_in_output(self, dev_cards, tmp_path) -> None:
        out, _ = build_sft_dataset(dev_cards, tmp_path / "sft.jsonl")
        lines = [l for l in out.read_text().splitlines() if l.strip()]
        ex = SFTExample.model_validate(json.loads(lines[0]))
        assert "NO-GO" in ex.output

    def test_creates_parent_dirs(self, dev_cards, tmp_path) -> None:
        nested = tmp_path / "a" / "b" / "sft.jsonl"
        build_sft_dataset(dev_cards, nested)
        assert nested.exists()

    def test_raises_on_test_only_input(self, tmp_path) -> None:
        test_only = [_card("T-001", "test")]
        with pytest.raises(SplitLeakageError):
            build_sft_dataset(test_only, tmp_path / "sft.jsonl")


# ---------------------------------------------------------------------------
# DPO
# ---------------------------------------------------------------------------

class TestBuildDPOPreferencePairs:
    def test_output_file_created(self, dev_cards, tmp_path) -> None:
        out, _ = build_dpo_preference_pairs(dev_cards, None, tmp_path / "dpo.jsonl")
        assert out.exists()

    def test_one_pair_per_dev_card(self, dev_cards, tmp_path) -> None:
        out, manifest = build_dpo_preference_pairs(dev_cards, None, tmp_path / "dpo.jsonl")
        lines = [l for l in out.read_text().splitlines() if l.strip()]
        assert len(lines) == len(dev_cards)
        assert manifest.n_examples == len(dev_cards)

    def test_output_schema_valid(self, dev_cards, tmp_path) -> None:
        out, _ = build_dpo_preference_pairs(dev_cards, None, tmp_path / "dpo.jsonl")
        for line in out.read_text().splitlines():
            if not line.strip():
                continue
            pair = DPOPair.model_validate(json.loads(line))
            assert pair.prompt
            assert pair.chosen
            assert pair.rejected

    def test_partial_implementation_flag(self, dev_cards, tmp_path) -> None:
        out, manifest = build_dpo_preference_pairs(dev_cards, None, tmp_path / "dpo.jsonl")
        assert manifest.partial_implementation is True
        for line in out.read_text().splitlines():
            if not line.strip():
                continue
            pair = DPOPair.model_validate(json.loads(line))
            assert pair.partial_implementation is True

    def test_synthetic_generation_rule_documented(self, dev_cards, tmp_path) -> None:
        out, _ = build_dpo_preference_pairs(dev_cards, None, tmp_path / "dpo.jsonl")
        for line in out.read_text().splitlines():
            if not line.strip():
                continue
            pair = DPOPair.model_validate(json.loads(line))
            assert pair.synthetic_generation_rule
            assert "PARTIAL IMPLEMENTATION" in pair.synthetic_generation_rule

    def test_chosen_contains_gold_decision(self, dev_cards, tmp_path) -> None:
        out, _ = build_dpo_preference_pairs(dev_cards, None, tmp_path / "dpo.jsonl")
        lines = [l for l in out.read_text().splitlines() if l.strip()]
        pair = DPOPair.model_validate(json.loads(lines[0]))
        assert "NO-GO" in pair.chosen

    def test_rejected_omits_constraints(self, dev_cards, tmp_path) -> None:
        out, _ = build_dpo_preference_pairs(dev_cards, None, tmp_path / "dpo.jsonl")
        lines = [l for l in out.read_text().splitlines() if l.strip()]
        pair = DPOPair.model_validate(json.loads(lines[0]))
        assert "none" in pair.rejected.lower() or "PROCEED" in pair.rejected

    def test_test_cards_in_input_raises_leakage_error(self, mixed_cards, tmp_path) -> None:
        with pytest.raises(SplitLeakageError):
            build_dpo_preference_pairs(mixed_cards, None, tmp_path / "dpo.jsonl")

    def test_raises_if_agent_traces_passed(self, dev_cards, tmp_path) -> None:
        from aerosafety.io import AgentTrace, Recommendation
        import hashlib
        fake_trace = AgentTrace(
            task_id="T1", run_id="R1", model_version="mock", model_provider="mock",
            prompt_hash=hashlib.sha256(b"x").hexdigest(), system_prompt="sp",
            messages=[], final_recommendation=Recommendation(
                decision="NO-GO", rationale="[MOCK]",
            ),
        )
        with pytest.raises(NotImplementedError, match="PARTIAL IMPLEMENTATION"):
            build_dpo_preference_pairs(dev_cards, [fake_trace], tmp_path / "dpo.jsonl")

    def test_manifest_partial_notes_mention_t8b(self, dev_cards, tmp_path) -> None:
        _, manifest = build_dpo_preference_pairs(dev_cards, None, tmp_path / "dpo.jsonl")
        assert "T8b" in manifest.partial_implementation_notes


# ---------------------------------------------------------------------------
# Verifier
# ---------------------------------------------------------------------------

class TestBuildVerifierDataset:
    def test_output_file_created(self, dev_cards, tmp_path) -> None:
        out, _ = build_verifier_dataset(dev_cards, None, tmp_path / "verifier.jsonl")
        assert out.exists()

    def test_two_examples_per_non_escalation_card(self, tmp_path) -> None:
        # Card without escalation_required produces pass + fail = 2 examples
        cards = [_card("NC-A-001", "dev", escalation_required=False)]
        out, manifest = build_verifier_dataset(cards, None, tmp_path / "verifier.jsonl")
        assert manifest.n_examples == 2

    def test_three_examples_per_escalation_card(self, tmp_path) -> None:
        # Card with escalation_required produces pass + fail + needs_escalation = 3
        cards = [_card("NC-A-001", "dev", escalation_required=True)]
        out, manifest = build_verifier_dataset(cards, None, tmp_path / "verifier.jsonl")
        assert manifest.n_examples == 3

    def test_output_schema_valid(self, dev_cards, tmp_path) -> None:
        out, _ = build_verifier_dataset(dev_cards, None, tmp_path / "verifier.jsonl")
        for line in out.read_text().splitlines():
            if not line.strip():
                continue
            ex = VerifierExample.model_validate(json.loads(line))
            assert ex.label in ("pass", "fail", "needs_escalation")
            assert ex.severity in ("Low", "Medium", "High", "Critical")

    def test_pass_has_no_violated_constraint(self, tmp_path) -> None:
        cards = [_card("NC-A-001", "dev")]
        out, _ = build_verifier_dataset(cards, None, tmp_path / "verifier.jsonl")
        lines = [l for l in out.read_text().splitlines() if l.strip()]
        pass_ex = VerifierExample.model_validate(json.loads(lines[0]))
        assert pass_ex.label == "pass"
        assert pass_ex.violated_constraint is None

    def test_fail_has_violated_constraint(self, tmp_path) -> None:
        cards = [_card("NC-A-001", "dev")]
        out, _ = build_verifier_dataset(cards, None, tmp_path / "verifier.jsonl")
        lines = [l for l in out.read_text().splitlines() if l.strip()]
        fail_ex = VerifierExample.model_validate(json.loads(lines[1]))
        assert fail_ex.label == "fail"
        assert fail_ex.violated_constraint is not None

    def test_partial_implementation_flag(self, dev_cards, tmp_path) -> None:
        out, manifest = build_verifier_dataset(dev_cards, None, tmp_path / "verifier.jsonl")
        assert manifest.partial_implementation is True

    def test_synthetic_rule_documented(self, dev_cards, tmp_path) -> None:
        out, _ = build_verifier_dataset(dev_cards, None, tmp_path / "verifier.jsonl")
        for line in out.read_text().splitlines():
            if not line.strip():
                continue
            ex = VerifierExample.model_validate(json.loads(line))
            assert ex.synthetic_generation_rule
            assert "PARTIAL IMPLEMENTATION" in ex.synthetic_generation_rule

    def test_test_cards_in_input_raises_leakage_error(self, mixed_cards, tmp_path) -> None:
        with pytest.raises(SplitLeakageError):
            build_verifier_dataset(mixed_cards, None, tmp_path / "verifier.jsonl")

    def test_raises_if_agent_traces_passed(self, dev_cards, tmp_path) -> None:
        with pytest.raises(NotImplementedError, match="PARTIAL IMPLEMENTATION"):
            build_verifier_dataset(dev_cards, [], tmp_path / "verifier.jsonl")

    def test_manifest_extra_counts(self, dev_cards, tmp_path) -> None:
        _, manifest = build_verifier_dataset(dev_cards, None, tmp_path / "verifier.jsonl")
        assert "n_pass" in manifest.extra
        assert "n_fail" in manifest.extra
        assert "n_needs_escalation" in manifest.extra


# ---------------------------------------------------------------------------
# Manifest lineage
# ---------------------------------------------------------------------------

class TestManifestRecordsLineage:
    def test_sft_manifest_records_source_families(self, dev_cards, tmp_path) -> None:
        _, manifest = build_sft_dataset(dev_cards, tmp_path / "sft.jsonl")
        assert "notam_compliance" in manifest.source_task_families
        assert "weather_dispatch" in manifest.source_task_families

    def test_sft_manifest_no_test_in_splits(self, dev_cards, tmp_path) -> None:
        _, manifest = build_sft_dataset(dev_cards, tmp_path / "sft.jsonl")
        assert "test" not in manifest.source_splits_included

    def test_dpo_manifest_partial_implementation_true(self, dev_cards, tmp_path) -> None:
        _, manifest = build_dpo_preference_pairs(dev_cards, None, tmp_path / "dpo.jsonl")
        assert manifest.partial_implementation is True

    def test_verifier_manifest_generation_method(self, dev_cards, tmp_path) -> None:
        _, manifest = build_verifier_dataset(dev_cards, None, tmp_path / "verifier.jsonl")
        assert manifest.generation_method == "synthetic_gold_derivation"
