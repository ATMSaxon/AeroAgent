"""
Integration tests for aerosafety/training/train_dpo.py — CPU dry-run.

Tests the synthetic-pair guard (non-dry-run must refuse synthetic-only pairs),
and the dry-run training loop.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

torch = pytest.importorskip("torch")
transformers = pytest.importorskip("transformers")

from aerosafety.io import TaskCard, TaskProvenance
from aerosafety.training.dataset_builder import build_dpo_preference_pairs
from aerosafety.training.train_dpo import (
    SyntheticOnlyDPOError,
    _assert_not_all_synthetic,
    _run_dry_run,
    main,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _dev_card(task_id: str) -> TaskCard:
    return TaskCard(
        task_id=task_id,
        family="notam_compliance",
        task_type="B",
        prompt=f"[SYNTHETIC] NOTAM scenario {task_id}.",
        gold_decision="NO-GO",
        required_safety_constraints=["constraint_a"],
        evidence_requirements=["FAA doc"],
        severity="High",
        escalation_required=False,
        provenance=TaskProvenance(source="SYNTHETIC", generation_rule="unit test"),
        split="dev",
    )


@pytest.fixture()
def dpo_jsonl(tmp_path: Path) -> Path:
    cards = [_dev_card(f"D{i:03d}") for i in range(6)]
    out, _ = build_dpo_preference_pairs(cards, None, tmp_path / "dpo.jsonl")
    return out


# ---------------------------------------------------------------------------
# Synthetic guard tests
# ---------------------------------------------------------------------------

class TestSyntheticGuard:
    def test_dry_run_always_allowed_synthetic(self, dpo_jsonl: Path) -> None:
        # dry_run=True must not raise even with synthetic pairs
        _assert_not_all_synthetic(dpo_jsonl, dry_run=True)  # must not raise

    def test_real_run_refused_when_all_synthetic(self, dpo_jsonl: Path) -> None:
        with pytest.raises(SyntheticOnlyDPOError) as exc_info:
            _assert_not_all_synthetic(dpo_jsonl, dry_run=False)
        assert "T8b" in str(exc_info.value)
        assert "partial_implementation" in str(exc_info.value)

    def test_error_message_mentions_claude_md(self, dpo_jsonl: Path) -> None:
        with pytest.raises(SyntheticOnlyDPOError) as exc_info:
            _assert_not_all_synthetic(dpo_jsonl, dry_run=False)
        assert "CLAUDE.md" in str(exc_info.value)

    def test_no_manifest_skips_guard(self, tmp_path: Path) -> None:
        # If manifest doesn't exist, guard is skipped (no false-positives for legacy data)
        fake_data = tmp_path / "fake.jsonl"
        fake_data.write_text("")
        _assert_not_all_synthetic(fake_data, dry_run=False)  # must not raise

    def test_cli_real_run_returns_code_2_for_synthetic(self, dpo_jsonl: Path, tmp_path: Path) -> None:
        rc = main(["--data", str(dpo_jsonl), "--output", str(tmp_path / "out")])
        assert rc == 2


# ---------------------------------------------------------------------------
# Dry-run tests
# ---------------------------------------------------------------------------

class TestTrainDPODryRun:
    def test_creates_checkpoint_dir(self, dpo_jsonl: Path, tmp_path: Path) -> None:
        ckpt = tmp_path / "ckpt_dpo"
        _run_dry_run(dpo_jsonl, ckpt)
        assert ckpt.is_dir()

    def test_config_json_created(self, dpo_jsonl: Path, tmp_path: Path) -> None:
        ckpt = tmp_path / "ckpt_dpo"
        _run_dry_run(dpo_jsonl, ckpt)
        assert (ckpt / "config.json").exists()

    def test_trainer_state_created(self, dpo_jsonl: Path, tmp_path: Path) -> None:
        ckpt = tmp_path / "ckpt_dpo"
        _run_dry_run(dpo_jsonl, ckpt)
        assert (ckpt / "trainer_state.json").exists()

    def test_config_structure(self, dpo_jsonl: Path, tmp_path: Path) -> None:
        ckpt = tmp_path / "ckpt_dpo"
        result = _run_dry_run(dpo_jsonl, ckpt)
        assert result["script"] == "train_dpo"
        assert result["dry_run"] is True
        assert isinstance(result["loss"], float)
        assert "beta" in result

    def test_loss_is_finite(self, dpo_jsonl: Path, tmp_path: Path) -> None:
        ckpt = tmp_path / "ckpt_dpo"
        result = _run_dry_run(dpo_jsonl, ckpt)
        assert math.isfinite(result["loss"])

    def test_synthetic_flag_in_config(self, dpo_jsonl: Path, tmp_path: Path) -> None:
        ckpt = tmp_path / "ckpt_dpo"
        result = _run_dry_run(dpo_jsonl, ckpt)
        assert result["all_synthetic"] is True

    def test_production_model_placeholder(self, dpo_jsonl: Path, tmp_path: Path) -> None:
        ckpt = tmp_path / "ckpt_dpo"
        result = _run_dry_run(dpo_jsonl, ckpt)
        assert "NOT IMPLEMENTED" in result["production_model"]

    def test_model_weights_saved(self, dpo_jsonl: Path, tmp_path: Path) -> None:
        ckpt = tmp_path / "ckpt_dpo"
        _run_dry_run(dpo_jsonl, ckpt)
        weight_files = list(ckpt.glob("*.safetensors")) + list(ckpt.glob("pytorch_model*.bin"))
        assert len(weight_files) >= 1

    def test_cli_dry_run_returns_zero(self, dpo_jsonl: Path, tmp_path: Path) -> None:
        ckpt = tmp_path / "ckpt_dpo_cli"
        rc = main(["--data", str(dpo_jsonl), "--output", str(ckpt), "--dry-run"])
        assert rc == 0

    def test_production_raises_not_implemented(self, dpo_jsonl: Path, tmp_path: Path) -> None:
        from aerosafety.training.train_dpo import _run_production
        with pytest.raises((NotImplementedError, RuntimeError, ImportError)):
            _run_production(dpo_jsonl, tmp_path / "prod_ckpt", "Qwen2.5-7B")
