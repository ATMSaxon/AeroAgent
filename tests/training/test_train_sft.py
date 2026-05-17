"""
Integration tests for aerosafety/training/train_sft.py — CPU dry-run.

Builds a real SFT JSONL from pilot cards, runs --dry-run, asserts checkpoint
artefacts are produced with expected structure.

These tests require torch + transformers (both installed).
They do NOT require peft/trl/datasets/accelerate.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

torch = pytest.importorskip("torch")
transformers = pytest.importorskip("transformers")

from aerosafety.io import TaskCard, TaskProvenance
from aerosafety.training.dataset_builder import build_sft_dataset
from aerosafety.training.train_sft import _run_dry_run, main


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _dev_card(task_id: str, gold: str = "NO-GO") -> TaskCard:
    return TaskCard(
        task_id=task_id,
        family="notam_compliance",
        task_type="A",
        prompt=f"[SYNTHETIC] Is operation {task_id} permitted?",
        gold_decision=gold,
        required_safety_constraints=["runway_closure_notam"],
        evidence_requirements=["FAA JO 7930.2S"],
        severity="High",
        escalation_required=False,
        provenance=TaskProvenance(source="SYNTHETIC", generation_rule="unit test"),
        split="dev",
    )


@pytest.fixture()
def sft_jsonl(tmp_path: Path) -> Path:
    cards = [_dev_card(f"T{i:03d}") for i in range(6)]
    out, _ = build_sft_dataset(cards, tmp_path / "sft.jsonl")
    return out


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestTrainSFTDryRun:
    def test_dry_run_creates_checkpoint_dir(self, sft_jsonl: Path, tmp_path: Path) -> None:
        ckpt = tmp_path / "ckpt_sft"
        _run_dry_run(sft_jsonl, ckpt)
        assert ckpt.is_dir()

    def test_config_json_created(self, sft_jsonl: Path, tmp_path: Path) -> None:
        ckpt = tmp_path / "ckpt_sft"
        _run_dry_run(sft_jsonl, ckpt)
        assert (ckpt / "config.json").exists()

    def test_trainer_state_created(self, sft_jsonl: Path, tmp_path: Path) -> None:
        ckpt = tmp_path / "ckpt_sft"
        _run_dry_run(sft_jsonl, ckpt)
        assert (ckpt / "trainer_state.json").exists()

    def test_config_json_structure(self, sft_jsonl: Path, tmp_path: Path) -> None:
        ckpt = tmp_path / "ckpt_sft"
        result = _run_dry_run(sft_jsonl, ckpt)
        assert result["dry_run"] is True
        assert result["script"] == "train_sft"
        assert isinstance(result["loss"], float)
        assert "NOT IMPLEMENTED" in result["production_model"]

    def test_trainer_state_has_global_step(self, sft_jsonl: Path, tmp_path: Path) -> None:
        ckpt = tmp_path / "ckpt_sft"
        _run_dry_run(sft_jsonl, ckpt)
        state = json.loads((ckpt / "trainer_state.json").read_text())
        assert state["global_step"] == 1

    def test_loss_is_finite(self, sft_jsonl: Path, tmp_path: Path) -> None:
        ckpt = tmp_path / "ckpt_sft"
        result = _run_dry_run(sft_jsonl, ckpt)
        import math
        assert math.isfinite(result["loss"])
        assert result["loss"] > 0

    def test_model_weights_saved(self, sft_jsonl: Path, tmp_path: Path) -> None:
        ckpt = tmp_path / "ckpt_sft"
        _run_dry_run(sft_jsonl, ckpt)
        # HF save_pretrained writes model.safetensors or pytorch_model.bin
        weight_files = list(ckpt.glob("*.safetensors")) + list(ckpt.glob("pytorch_model*.bin"))
        assert len(weight_files) >= 1, f"No model weights found in {ckpt}"

    def test_note_says_test_model(self, sft_jsonl: Path, tmp_path: Path) -> None:
        ckpt = tmp_path / "ckpt_sft"
        result = _run_dry_run(sft_jsonl, ckpt)
        assert "TEST MODEL" in result["note"]

    def test_cli_dry_run_returns_zero(self, sft_jsonl: Path, tmp_path: Path) -> None:
        ckpt = tmp_path / "ckpt_sft_cli"
        rc = main(["--data", str(sft_jsonl), "--output", str(ckpt), "--dry-run"])
        assert rc == 0

    def test_cli_missing_data_returns_nonzero(self, tmp_path: Path) -> None:
        rc = main([
            "--data", str(tmp_path / "nonexistent.jsonl"),
            "--output", str(tmp_path / "out"),
            "--dry-run",
        ])
        assert rc != 0

    def test_production_raises_not_implemented(self, sft_jsonl: Path, tmp_path: Path) -> None:
        from aerosafety.training.train_sft import _run_production
        with pytest.raises((NotImplementedError, RuntimeError, ImportError)):
            _run_production(sft_jsonl, tmp_path / "prod_ckpt", "Qwen2.5-7B")
