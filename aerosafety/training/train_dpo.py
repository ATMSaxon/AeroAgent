"""
train_dpo.py — AeroSafety-DPO preference optimisation training script.

Loads DPOPair JSONL produced by build_dpo_preference_pairs() (T11) and
runs DPO preference optimisation.

Dry-run mode (--dry-run)
------------------------
Runs 1 gradient step on CPU using `sshleifer/tiny-gpt2` (TEST MODEL).
Validates dataset → tokenizer → DPO loss plumbing without GPU or trl.DPOTrainer.

Synthetic-pair guard
--------------------
If all DPO pairs in the manifest have `partial_implementation: True` (i.e., all
synthetic Phase 1 pairs), the script refuses to start a non-dry-run.  This
prevents claiming DPO alignment efficacy from synthetic data.  Points users to
T8b (real AgentTrace execution) for real pairs.

Production mode (requires GPU)
-------------------------------
NOT IMPLEMENTED until GPU is connected (T15+).
Production model IDs are PLACEHOLDERS per CLAUDE.md §1.2.

Missing deps
------------
Non-dry-run requires peft/trl/datasets/accelerate.
Clean ImportError with pointer to `pip install 'aerosafety[gpu]'`.
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
            "These are required for non-dry-run DPO training. "
            "Use --dry-run for CPU pipeline validation without these deps."
        )


# ---------------------------------------------------------------------------
# Synthetic-pair guard
# ---------------------------------------------------------------------------

class SyntheticOnlyDPOError(Exception):
    """
    Raised when a non-dry-run DPO training is attempted with all-synthetic pairs.

    Per CLAUDE.md §6.2, DPO training requires traceable preference pairs.
    All-synthetic pairs (partial_implementation=True) are PARTIAL IMPLEMENTATION
    and must not be used for real training runs until T8b provides real AgentTraces.
    """


def _check_synthetic_guard(manifest_path: Path) -> bool:
    """
    Return True if all pairs in the manifest are synthetic (partial_implementation=True).
    Returns False if manifest doesn't exist or has real pairs.
    """
    if not manifest_path.exists():
        return False
    data = json.loads(manifest_path.read_text())
    return bool(data.get("partial_implementation", False))


def _assert_not_all_synthetic(data_path: Path, dry_run: bool) -> None:
    """
    Raise SyntheticOnlyDPOError if attempting real training on synthetic-only pairs.
    """
    if dry_run:
        return  # dry-run always allowed regardless of pair quality

    manifest_path = data_path.with_suffix(".manifest.json")
    if _check_synthetic_guard(manifest_path):
        raise SyntheticOnlyDPOError(
            "REFUSED: All DPO pairs are synthetic (partial_implementation=True). "
            "Running a real DPO training on synthetic pairs would produce a model "
            "whose alignment cannot be attributed to real agent behaviour. "
            "Per CLAUDE.md §6.2, DPO requires traceable preference pairs. "
            "To proceed: run T8b (real AgentTrace execution with an API key) to "
            "generate real chosen/rejected pairs via build_dpo_preference_pairs() "
            "with agent_traces != None."
        )


# ---------------------------------------------------------------------------
# DPO loss (manual implementation for dry-run without trl)
# ---------------------------------------------------------------------------

def _dpo_loss(
    policy_logps_chosen: "torch.Tensor",
    policy_logps_rejected: "torch.Tensor",
    ref_logps_chosen: "torch.Tensor",
    ref_logps_rejected: "torch.Tensor",
    beta: float = 0.1,
) -> "torch.Tensor":
    """
    Bradley-Terry DPO loss (Rafailov et al. 2023).

    loss = -log(sigmoid(beta * ((log pi_chosen - log ref_chosen)
                               - (log pi_rejected - log ref_rejected))))
    """
    import torch  # noqa: PLC0415
    pi_logratios = policy_logps_chosen - policy_logps_rejected
    ref_logratios = ref_logps_chosen - ref_logps_rejected
    return -torch.nn.functional.logsigmoid(beta * (pi_logratios - ref_logratios)).mean()


def _sequence_logprobs(model, input_ids: "torch.Tensor") -> "torch.Tensor":
    """Compute mean log-probability over sequence tokens."""
    import torch  # noqa: PLC0415
    with torch.no_grad() if not model.training else torch.enable_grad():
        outputs = model(input_ids=input_ids, labels=input_ids)
    return -outputs.loss  # loss = mean NLL; logp = -loss


# ---------------------------------------------------------------------------
# Dry-run implementation
# ---------------------------------------------------------------------------

# TEST MODEL — not for research use.
_DRY_RUN_MODEL = "sshleifer/tiny-gpt2"
_DRY_RUN_MAX_PAIRS = 4
_DRY_RUN_MAX_LENGTH = 64


def _load_dpo_pairs(data_path: Path, limit: int | None = None) -> list[dict]:
    pairs = []
    with data_path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            pairs.append(json.loads(line))
            if limit is not None and len(pairs) >= limit:
                break
    if not pairs:
        raise ValueError(f"No DPO pairs loaded from {data_path}")
    return pairs


def _run_dry_run(data_path: Path, output_dir: Path) -> dict:
    """
    Manual DPO training step for plumbing validation on CPU.

    Uses sshleifer/tiny-gpt2 (TEST MODEL — not for research use).
    Does NOT use trl.DPOTrainer — validates loss computation only.
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

    pairs = _load_dpo_pairs(data_path, limit=_DRY_RUN_MAX_PAIRS)
    print(f"[dry-run] Loaded {len(pairs)} DPO pairs (limit={_DRY_RUN_MAX_PAIRS})")
    if pairs and pairs[0].get("partial_implementation"):
        print("[dry-run] NOTE: pairs are synthetic (partial_implementation=True) — dry-run only")

    print(f"[dry-run] Loading model: {_DRY_RUN_MODEL}  (TEST MODEL — not for research use)")
    tokenizer = AutoTokenizer.from_pretrained(_DRY_RUN_MODEL)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # Policy model (trainable) + frozen reference copy
    policy = AutoModelForCausalLM.from_pretrained(_DRY_RUN_MODEL)
    ref = AutoModelForCausalLM.from_pretrained(_DRY_RUN_MODEL)
    for p in ref.parameters():
        p.requires_grad_(False)

    policy.train()
    ref.eval()

    def encode(texts: list[str]) -> "torch.Tensor":
        return tokenizer(
            texts,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=_DRY_RUN_MAX_LENGTH,
        )["input_ids"]

    chosen_texts = [p["chosen"][:200] for p in pairs]
    rejected_texts = [p["rejected"][:200] for p in pairs]

    chosen_ids = encode(chosen_texts)
    rejected_ids = encode(rejected_texts)

    optimizer = torch.optim.AdamW(policy.parameters(), lr=1e-4)
    optimizer.zero_grad()

    # Compute log-probs under policy and reference
    policy_logp_chosen = _sequence_logprobs(policy, chosen_ids)
    policy_logp_rejected = _sequence_logprobs(policy, rejected_ids)
    with torch.no_grad():
        ref_logp_chosen = _sequence_logprobs(ref, chosen_ids)
        ref_logp_rejected = _sequence_logprobs(ref, rejected_ids)

    loss = _dpo_loss(
        policy_logp_chosen, policy_logp_rejected,
        ref_logp_chosen, ref_logp_rejected,
    )
    loss.backward()
    optimizer.step()

    print(f"[dry-run] 1 DPO step completed. Loss: {loss.item():.4f}")

    output_dir.mkdir(parents=True, exist_ok=True)
    config_data = {
        "script": "train_dpo",
        "dry_run": True,
        "model": _DRY_RUN_MODEL,
        "n_pairs_used": len(pairs),
        "max_length": _DRY_RUN_MAX_LENGTH,
        "beta": 0.1,
        "loss": loss.item(),
        "all_synthetic": bool(pairs[0].get("partial_implementation")) if pairs else False,
        "note": "TEST MODEL — not for research use. Dry-run plumbing validation only.",
        "production_model": "NOT IMPLEMENTED — requires GPU (T15+). "
                           "Placeholder: Qwen2.5-7B or Llama-3.1-8B",
    }
    (output_dir / "config.json").write_text(json.dumps(config_data, indent=2))
    trainer_state = {
        "epoch": 0.0,
        "global_step": 1,
        "log_history": [{"dpo_loss": loss.item(), "step": 1}],
    }
    (output_dir / "trainer_state.json").write_text(json.dumps(trainer_state, indent=2))
    policy.save_pretrained(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))

    print(f"[dry-run] Checkpoint written to {output_dir}")
    return config_data


# ---------------------------------------------------------------------------
# Production stub
# ---------------------------------------------------------------------------

def _run_production(data_path: Path, output_dir: Path, model_id: str) -> None:
    """NOT IMPLEMENTED — Phase 2 GPU training (T15+)."""
    _require_deps()
    from aerosafety.training.gpu_check import require_gpu  # noqa: PLC0415
    require_gpu()
    raise NotImplementedError(
        "DPO production training is NOT IMPLEMENTED (Phase 2, T15+). "
        f"Production model '{model_id}' is a PLACEHOLDER. "
        "Requirements: GPU with ≥40 GB VRAM (for reference model), peft, trl. "
        "Use --dry-run for CPU plumbing validation."
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m aerosafety.training.train_dpo",
        description="AeroSafety-DPO: preference optimisation on aviation safety pairs.",
    )
    parser.add_argument("--data", required=True, help="Path to DPO JSONL.")
    parser.add_argument("--output", required=True, help="Output checkpoint directory.")
    parser.add_argument("--model", default=_DRY_RUN_MODEL,
                        help="Model ID. Production models NOT IMPLEMENTED (T15+).")
    parser.add_argument("--dry-run", action="store_true",
                        help="CPU plumbing validation with tiny model.")

    args = parser.parse_args(argv)
    data_path = Path(args.data)
    output_dir = Path(args.output)

    if not data_path.exists():
        print(f"ERROR: --data {data_path} does not exist.", file=sys.stderr)
        return 1

    try:
        _assert_not_all_synthetic(data_path, dry_run=args.dry_run)
    except SyntheticOnlyDPOError as exc:
        print(f"HARD ERROR — SYNTHETIC GUARD:\n{exc}", file=sys.stderr)
        return 2

    if args.dry_run:
        _run_dry_run(data_path, output_dir)
        return 0
    else:
        _run_production(data_path, output_dir, args.model)
        return 0


if __name__ == "__main__":
    sys.exit(main())
