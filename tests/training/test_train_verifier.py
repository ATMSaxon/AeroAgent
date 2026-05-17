"""
Integration tests for aerosafety/training/train_verifier.py — CPU dry-run.

Builds a real VerifierExample JSONL from pilot cards, runs --dry-run, asserts
checkpoint artefacts.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

torch = pytest.importorskip("torch")
transformers = pytest.importorskip("transformers")

from aerosafety.io import TaskCard, TaskProvenance
from aerosafety.training.dataset_builder import build_verifier_dataset
from aerosafety.training.train_verifier import _run_dry_run, main


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _dev_card(task_id: str, escalation: bool = False) -> TaskCard:
    return TaskCard(
        task_id=task_id,
        family="weather_dispatch",
        task_type="C",
        prompt=f"[SYNTHETIC] Weather scenario {task_id}.",
        gold_decision="NO-GO",
        required_safety_constraints=["wx_minima_constraint"],
        evidence_requirements=["FAA AC 00-6B"],
        severity="High",
        escalation_required=escalation,
        provenance=TaskProvenance(source="SYNTHETIC", generation_rule="unit test"),
        split="dev",
    )


@pytest.fixture()
def verifier_jsonl(tmp_path: Path) -> Path:
    cards = [_dev_card(f"V{i:03d}") for i in range(5)]
    out, _ = build_verifier_dataset(cards, None, tmp_path / "verifier.jsonl")
    return out


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestTrainVerifierDryRun:
    def test_creates_checkpoint_dir(self, verifier_jsonl: Path, tmp_path: Path) -> None:
        ckpt = tmp_path / "ckpt_verifier"
        _run_dry_run(verifier_jsonl, ckpt)
        assert ckpt.is_dir()

    def test_config_json_created(self, verifier_jsonl: Path, tmp_path: Path) -> None:
        ckpt = tmp_path / "ckpt_verifier"
        _run_dry_run(verifier_jsonl, ckpt)
        assert (ckpt / "config.json").exists()

    def test_trainer_state_created(self, verifier_jsonl: Path, tmp_path: Path) -> None:
        ckpt = tmp_path / "ckpt_verifier"
        _run_dry_run(verifier_jsonl, ckpt)
        assert (ckpt / "trainer_state.json").exists()

    def test_classifier_heads_saved(self, verifier_jsonl: Path, tmp_path: Path) -> None:
        ckpt = tmp_path / "ckpt_verifier"
        _run_dry_run(verifier_jsonl, ckpt)
        assert (ckpt / "classifier_heads.pt").exists()

    def test_config_structure(self, verifier_jsonl: Path, tmp_path: Path) -> None:
        ckpt = tmp_path / "ckpt_verifier"
        result = _run_dry_run(verifier_jsonl, ckpt)
        assert result["script"] == "train_verifier"
        assert result["dry_run"] is True
        assert isinstance(result["loss"], float)
        assert "loss_label" in result
        assert "loss_severity" in result
        assert "loss_violation" in result

    def test_all_losses_finite(self, verifier_jsonl: Path, tmp_path: Path) -> None:
        ckpt = tmp_path / "ckpt_verifier"
        result = _run_dry_run(verifier_jsonl, ckpt)
        for key in ("loss", "loss_label", "loss_severity", "loss_violation"):
            assert math.isfinite(result[key]), f"{key} is not finite"

    def test_n_label_classes_correct(self, verifier_jsonl: Path, tmp_path: Path) -> None:
        ckpt = tmp_path / "ckpt_verifier"
        result = _run_dry_run(verifier_jsonl, ckpt)
        assert result["n_label_classes"] == 3   # pass | fail | needs_escalation

    def test_synthetic_flag_in_config(self, verifier_jsonl: Path, tmp_path: Path) -> None:
        ckpt = tmp_path / "ckpt_verifier"
        result = _run_dry_run(verifier_jsonl, ckpt)
        assert result["all_synthetic"] is True

    def test_production_model_placeholder(self, verifier_jsonl: Path, tmp_path: Path) -> None:
        ckpt = tmp_path / "ckpt_verifier"
        result = _run_dry_run(verifier_jsonl, ckpt)
        assert "NOT IMPLEMENTED" in result["production_model"]

    def test_cli_dry_run_returns_zero(self, verifier_jsonl: Path, tmp_path: Path) -> None:
        ckpt = tmp_path / "ckpt_verifier_cli"
        rc = main(["--data", str(verifier_jsonl), "--output", str(ckpt), "--dry-run"])
        assert rc == 0

    def test_cli_missing_data_returns_nonzero(self, tmp_path: Path) -> None:
        rc = main([
            "--data", str(tmp_path / "nonexistent.jsonl"),
            "--output", str(tmp_path / "out"),
            "--dry-run",
        ])
        assert rc != 0

    def test_production_raises_not_implemented(self, verifier_jsonl: Path, tmp_path: Path) -> None:
        from aerosafety.training.train_verifier import _run_production
        with pytest.raises((NotImplementedError, RuntimeError, ImportError)):
            _run_production(verifier_jsonl, tmp_path / "prod_ckpt", "aviation-bert")
