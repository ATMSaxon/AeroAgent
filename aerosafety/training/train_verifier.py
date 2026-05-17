"""
train_verifier.py — AeroVerifier classifier training script.

Loads VerifierExample JSONL produced by build_verifier_dataset() (T11) and
trains a multi-label classifier with head on top of a sentence encoder.

Dry-run mode (--dry-run)
------------------------
Runs 1 gradient step on CPU using sentence_transformers pooled embeddings
with a tiny linear classification head. Validates dataset → embedding →
classifier plumbing without GPU. Requires only torch + sentence_transformers.

Label schema
------------
Multi-label output (each example can trigger multiple heads):
  - binary label head: pass vs (fail | needs_escalation)
  - severity head: Low | Medium | High | Critical
  - violation type head: safety_constraint_omission | missed_escalation | None

Production mode (requires GPU)
-------------------------------
NOT IMPLEMENTED until GPU is connected (T15+).
Production encoder (e.g., aviation-finetuned BERT) is a PLACEHOLDER.

Missing deps
------------
sentence_transformers is required for dry-run (already in main deps).
peft/trl/datasets/accelerate are required for non-dry-run.
Clean ImportError with pointer to `pip install 'aerosafety[gpu]'`.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Label maps
# ---------------------------------------------------------------------------

_LABEL_TO_IDX = {"pass": 0, "fail": 1, "needs_escalation": 2}
_SEVERITY_TO_IDX = {"Low": 0, "Medium": 1, "High": 2, "Critical": 3}
_VIOLATION_TO_IDX: dict[str | None, int] = {
    None: 0,
    "safety_constraint_omission": 1,
    "missed_escalation": 2,
    "hallucinated_evidence": 3,
    "escalation_required": 2,  # alias
}


# ---------------------------------------------------------------------------
# Dependency guard
# ---------------------------------------------------------------------------

def _require_gpu_deps() -> None:
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
            "These are required for non-dry-run verifier training. "
            "Use --dry-run for CPU pipeline validation."
        )


# ---------------------------------------------------------------------------
# Dry-run implementation
# ---------------------------------------------------------------------------

# TEST MODEL — not for research use. sentence_transformers tiny model.
_DRY_RUN_ENCODER = "sentence-transformers/all-MiniLM-L6-v2"
_DRY_RUN_MAX_EXAMPLES = 8
_EMBEDDING_DIM = 384   # all-MiniLM-L6-v2 output dim
_N_LABELS = 3          # pass | fail | needs_escalation
_N_SEVERITY = 4        # Low | Medium | High | Critical
_N_VIOLATION = 4       # None | omission | escalation | hallucination


def _load_verifier_examples(data_path: Path, limit: int | None = None) -> list[dict]:
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
        raise ValueError(f"No VerifierExample objects loaded from {data_path}")
    return examples


def _run_dry_run(data_path: Path, output_dir: Path) -> dict:
    """
    Train a tiny classifier head on sentence embeddings for plumbing validation.

    Uses all-MiniLM-L6-v2 embeddings (TEST MODEL — not for research use).
    1 gradient step over up to 8 examples.
    """
    try:
        import torch  # noqa: PLC0415
        import torch.nn as nn  # noqa: PLC0415
        from sentence_transformers import SentenceTransformer  # noqa: PLC0415
    except ImportError as exc:
        raise ImportError(
            "torch and sentence_transformers are required for --dry-run. "
            "Install with: pip install torch sentence-transformers"
        ) from exc

    os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

    examples = _load_verifier_examples(data_path, limit=_DRY_RUN_MAX_EXAMPLES)
    print(f"[dry-run] Loaded {len(examples)} VerifierExamples (limit={_DRY_RUN_MAX_EXAMPLES})")
    if examples and examples[0].get("partial_implementation"):
        print("[dry-run] NOTE: examples are synthetic (partial_implementation=True) — dry-run only")

    print(f"[dry-run] Loading encoder: {_DRY_RUN_ENCODER}  (TEST MODEL — not for research use)")
    encoder = SentenceTransformer(_DRY_RUN_ENCODER)
    encoder.eval()
    for p in encoder.parameters():
        p.requires_grad_(False)

    # Encode trace feature text (use predicted_decision as representative feature)
    feature_texts = [
        str(ex["trace_features"].get("predicted_decision", "UNKNOWN"))[:200]
        for ex in examples
    ]
    # .cpu().clone() moves from MPS/GPU to CPU and exits inference_mode so autograd works
    embeddings = encoder.encode(feature_texts, convert_to_tensor=True).cpu().clone()

    # Build labels
    label_ids = torch.tensor([_LABEL_TO_IDX.get(ex["label"], 0) for ex in examples], dtype=torch.long)
    severity_ids = torch.tensor(
        [_SEVERITY_TO_IDX.get(ex.get("severity", "Low"), 0) for ex in examples], dtype=torch.long
    )
    violation_ids = torch.tensor(
        [_VIOLATION_TO_IDX.get(ex.get("missing_evidence_type"), 0) for ex in examples],
        dtype=torch.long,
    )

    # Classification heads
    head_label = nn.Linear(_EMBEDDING_DIM, _N_LABELS)
    head_severity = nn.Linear(_EMBEDDING_DIM, _N_SEVERITY)
    head_violation = nn.Linear(_EMBEDDING_DIM, _N_VIOLATION)

    ce = nn.CrossEntropyLoss()
    optimizer = torch.optim.AdamW(
        list(head_label.parameters()) +
        list(head_severity.parameters()) +
        list(head_violation.parameters()),
        lr=1e-3,
    )

    optimizer.zero_grad()
    loss_label = ce(head_label(embeddings), label_ids)
    loss_severity = ce(head_severity(embeddings), severity_ids)
    loss_violation = ce(head_violation(embeddings), violation_ids)
    loss = loss_label + loss_severity + loss_violation
    loss.backward()
    optimizer.step()

    print(
        f"[dry-run] 1 classifier step completed. "
        f"Total loss: {loss.item():.4f} "
        f"(label={loss_label.item():.4f}, "
        f"severity={loss_severity.item():.4f}, "
        f"violation={loss_violation.item():.4f})"
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    config_data = {
        "script": "train_verifier",
        "dry_run": True,
        "encoder": _DRY_RUN_ENCODER,
        "n_examples_used": len(examples),
        "embedding_dim": _EMBEDDING_DIM,
        "n_label_classes": _N_LABELS,
        "n_severity_classes": _N_SEVERITY,
        "n_violation_classes": _N_VIOLATION,
        "loss": loss.item(),
        "loss_label": loss_label.item(),
        "loss_severity": loss_severity.item(),
        "loss_violation": loss_violation.item(),
        "all_synthetic": bool(examples[0].get("partial_implementation")) if examples else False,
        "note": "TEST MODEL — not for research use. Dry-run plumbing validation only.",
        "production_model": "NOT IMPLEMENTED — requires GPU (T15+). "
                           "Placeholder: aviation-finetuned BERT or DeBERTa",
    }
    (output_dir / "config.json").write_text(json.dumps(config_data, indent=2))
    trainer_state = {
        "epoch": 0.0,
        "global_step": 1,
        "log_history": [{"loss": loss.item(), "step": 1}],
    }
    (output_dir / "trainer_state.json").write_text(json.dumps(trainer_state, indent=2))

    # Save head weights
    torch.save({
        "head_label": head_label.state_dict(),
        "head_severity": head_severity.state_dict(),
        "head_violation": head_violation.state_dict(),
    }, str(output_dir / "classifier_heads.pt"))

    print(f"[dry-run] Checkpoint written to {output_dir}")
    return config_data


# ---------------------------------------------------------------------------
# Production stub
# ---------------------------------------------------------------------------

def _run_production(data_path: Path, output_dir: Path, encoder_id: str) -> None:
    """NOT IMPLEMENTED — Phase 2 GPU training (T15+)."""
    _require_gpu_deps()
    from aerosafety.training.gpu_check import require_gpu  # noqa: PLC0415
    require_gpu()
    raise NotImplementedError(
        "Verifier production training is NOT IMPLEMENTED (Phase 2, T15+). "
        f"Production encoder '{encoder_id}' is a PLACEHOLDER. "
        "Requirements: GPU + peft + accelerate. "
        "Use --dry-run for CPU plumbing validation."
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m aerosafety.training.train_verifier",
        description="AeroVerifier: train multi-label safety classifier.",
    )
    parser.add_argument("--data", required=True, help="Path to VerifierExample JSONL.")
    parser.add_argument("--output", required=True, help="Output checkpoint directory.")
    parser.add_argument("--encoder", default=_DRY_RUN_ENCODER,
                        help="Encoder model ID. Production models NOT IMPLEMENTED (T15+).")
    parser.add_argument("--dry-run", action="store_true",
                        help="CPU plumbing validation with tiny encoder.")

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
        _run_production(data_path, output_dir, args.encoder)
        return 0


if __name__ == "__main__":
    sys.exit(main())
