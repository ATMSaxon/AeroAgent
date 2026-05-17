"""
train_sft.py — Aero-SFT supervised fine-tuning script.

Loads SFTExample JSONL produced by build_sft_dataset() (T11) and fine-tunes
a causal language model using LoRA via HuggingFace peft + trl.SFTTrainer.

Dry-run mode (--dry-run)
------------------------
Runs 1 step over 4 examples on CPU using `sshleifer/tiny-gpt2` (≈5 MB).
Validates dataset → tokenizer → training loop plumbing without GPU or large
model downloads.  Checkpoint dir is created with config.json + trainer state.

Production mode (requires GPU)
-------------------------------
NOT IMPLEMENTED until GPU is connected (T15+).
Production model IDs (Qwen2.5-7B, Llama-3.1-8B) are PLACEHOLDERS.
See CLAUDE.md §1.2 — placeholders must be marked explicitly.

Missing deps
------------
If peft/trl/datasets/accelerate are not installed the script raises a clean
ImportError with a pointer to `pip install 'aerosafety[gpu]'`.
torch + transformers are always required.

Usage
-----
    python -m aerosafety.training.train_sft \\
        --data data/training_sets/2026-05-17/sft.jsonl \\
        --output checkpoints/sft_dryrun/ \\
        --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Dependency guard
# ---------------------------------------------------------------------------

def _require_deps() -> None:
    """Raise clean ImportError if GPU training deps are missing."""
    missing = []
    for pkg in ("peft", "trl", "datasets", "accelerate"):
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        raise ImportError(
            f"GPU training dependencies not installed: {missing}. "
            "Install with: pip install 'aerosafety[gpu]'\n"
            "These are required for non-dry-run SFT training. "
            "Use --dry-run for CPU pipeline validation without these deps."
        )


# ---------------------------------------------------------------------------
# Dry-run implementation (torch + transformers only)
# ---------------------------------------------------------------------------

# TEST MODEL — not for research use. ≈5 MB, CPU-only, plumbing validation only.
_DRY_RUN_MODEL = "sshleifer/tiny-gpt2"
_DRY_RUN_MAX_EXAMPLES = 4
_DRY_RUN_MAX_LENGTH = 64


def _load_sft_examples(data_path: Path, limit: int | None = None) -> list[dict]:
    examples = []
    with data_path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            examples.append(json.loads(line))
            if limit is not None and len(examples) >= limit:
                break
    if not examples:
        raise ValueError(f"No SFT examples loaded from {data_path}")
    return examples


def _run_dry_run(data_path: Path, output_dir: Path) -> dict:
    """
    Minimal training loop for plumbing validation on CPU.

    Uses sshleifer/tiny-gpt2 (TEST MODEL — not for research use).
    Runs 1 gradient step over up to 4 examples.
    Writes checkpoint artefacts to output_dir.
    """
    try:
        import torch  # noqa: PLC0415
        from transformers import AutoModelForCausalLM, AutoTokenizer  # noqa: PLC0415
    except ImportError as exc:
        raise ImportError(
            "torch and transformers are required for --dry-run. "
            "Install with: pip install torch transformers"
        ) from exc

    os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

    examples = _load_sft_examples(data_path, limit=_DRY_RUN_MAX_EXAMPLES)
    print(f"[dry-run] Loaded {len(examples)} SFT examples (limit={_DRY_RUN_MAX_EXAMPLES})")

    print(f"[dry-run] Loading tokenizer: {_DRY_RUN_MODEL}  (TEST MODEL — not for research use)")
    tokenizer = AutoTokenizer.from_pretrained(_DRY_RUN_MODEL)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    print(f"[dry-run] Loading model: {_DRY_RUN_MODEL}  (TEST MODEL — not for research use)")
    model = AutoModelForCausalLM.from_pretrained(_DRY_RUN_MODEL)
    model.train()

    # Build simple text sequences: instruction + input + output concatenated
    texts = [
        ex["instruction"][:100] + "\n" + ex["input"][:100] + "\n" + ex["output"][:100]
        for ex in examples
    ]
    enc = tokenizer(
        texts,
        return_tensors="pt",
        padding=True,
        truncation=True,
        max_length=_DRY_RUN_MAX_LENGTH,
    )
    input_ids = enc["input_ids"]
    labels = input_ids.clone()

    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4)
    optimizer.zero_grad()
    outputs = model(input_ids=input_ids, labels=labels)
    loss = outputs.loss
    loss.backward()
    optimizer.step()

    print(f"[dry-run] 1 training step completed. Loss: {loss.item():.4f}")

    # Write checkpoint artefacts
    output_dir.mkdir(parents=True, exist_ok=True)
    config_out = output_dir / "config.json"
    config_data = {
        "script": "train_sft",
        "dry_run": True,
        "model": _DRY_RUN_MODEL,
        "n_examples_used": len(examples),
        "max_length": _DRY_RUN_MAX_LENGTH,
        "loss": loss.item(),
        "note": "TEST MODEL — not for research use. Dry-run plumbing validation only.",
        "production_model": "NOT IMPLEMENTED — requires GPU (T15+). "
                           "Placeholder: Qwen2.5-7B or Llama-3.1-8B",
    }
    config_out.write_text(json.dumps(config_data, indent=2))

    # Minimal trainer state file matching HF checkpoint convention
    trainer_state = {
        "epoch": 0.0,
        "global_step": 1,
        "best_metric": None,
        "log_history": [{"loss": loss.item(), "step": 1}],
    }
    (output_dir / "trainer_state.json").write_text(json.dumps(trainer_state, indent=2))

    # Save tiny model weights for checkpoint completeness
    model.save_pretrained(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))

    print(f"[dry-run] Checkpoint written to {output_dir}")
    return config_data


# ---------------------------------------------------------------------------
# Production stub
# ---------------------------------------------------------------------------

def _run_production(data_path: Path, output_dir: Path, model_id: str) -> None:
    """
    NOT IMPLEMENTED — Phase 2 GPU training (T15+).

    Production model IDs (Qwen2.5-7B, Llama-3.1-8B) are PLACEHOLDERS.
    This path requires: GPU + peft + trl + datasets + accelerate.
    """
    _require_deps()
    from aerosafety.training.gpu_check import require_gpu  # noqa: PLC0415
    require_gpu()

    raise NotImplementedError(
        "SFT production training is NOT IMPLEMENTED (Phase 2, T15+). "
        f"Production model '{model_id}' is a PLACEHOLDER. "
        "Requirements: GPU with ≥24 GB VRAM, peft, trl, datasets, accelerate. "
        "Use --dry-run for CPU plumbing validation."
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m aerosafety.training.train_sft",
        description="Aero-SFT: fine-tune a causal LM on aviation safety task cards.",
    )
    parser.add_argument(
        "--data", required=True,
        help="Path to SFT JSONL produced by build_sft_dataset().",
    )
    parser.add_argument(
        "--output", required=True,
        help="Output directory for checkpoint artefacts.",
    )
    parser.add_argument(
        "--model",
        default=_DRY_RUN_MODEL,
        help=(
            f"Model ID (default dry-run: {_DRY_RUN_MODEL!r}). "
            "Production: Qwen2.5-7B or Llama-3.1-8B — NOT IMPLEMENTED until GPU phase (T15+)."
        ),
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Run 1 step on CPU with tiny model for plumbing validation.",
    )

    args = parser.parse_args(argv)
    data_path = Path(args.data)
    output_dir = Path(args.output)

    if not data_path.exists():
        print(f"ERROR: --data {data_path} does not exist.", file=sys.stderr)
        return 1

    if args.dry_run:
        _run_dry_run(data_path, output_dir)
        return 0
    else:
        _run_production(data_path, output_dir, args.model)
        return 0


if __name__ == "__main__":
    sys.exit(main())
