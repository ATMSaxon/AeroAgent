"""
CLI for Phase 2 training dataset construction.

Usage
-----
    python -m aerosafety.training.cli build --kind sft --input aerosafety/tasks --output data/training_sets/2026-05-17/ --no-test-leak

Options
-------
    --kind         sft | dpo | verifier
    --input        Root of aerosafety/tasks/ (default: aerosafety/tasks)
    --output       Output directory (default: data/training_sets/<today>/)
    --families     notam | weather | all  (default: all)
    --limit        Max TaskCards to include (default: all)
    --no-test-leak Fail immediately if any test card is detected (always enforced; flag is declarative)
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path


# ---------------------------------------------------------------------------
# TaskCard loader (re-used from smoke_test for DRY)
# ---------------------------------------------------------------------------

def _load_cards(
    input_root: Path,
    families: list[str] | None,
    limit: int | None,
) -> list:
    from aerosafety.io import TaskCard

    task_dirs: list[Path] = []
    if families is None or "all" in families:
        task_dirs = [
            input_root / "notam_compliance" / "taskcards",
            input_root / "weather_dispatch" / "taskcards",
        ]
    else:
        for fam in families:
            if fam == "notam":
                task_dirs.append(input_root / "notam_compliance" / "taskcards")
            elif fam == "weather":
                task_dirs.append(input_root / "weather_dispatch" / "taskcards")
            else:
                print(f"ERROR: Unknown family {fam!r}. Valid: notam, weather, all.", file=sys.stderr)
                sys.exit(1)

    cards: list[TaskCard] = []
    for d in task_dirs:
        if not d.is_dir():
            continue
        for jsonl_file in sorted(d.glob("*.jsonl")):
            with jsonl_file.open(encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    cards.append(TaskCard.model_validate(json.loads(line)))
            if limit and len(cards) >= limit:
                return cards[:limit]

    if limit:
        cards = cards[:limit]
    return cards


# ---------------------------------------------------------------------------
# Build command
# ---------------------------------------------------------------------------

def cmd_build(args: argparse.Namespace) -> int:
    from aerosafety.training.dataset_builder import (
        build_dpo_preference_pairs,
        build_sft_dataset,
        build_verifier_dataset,
    )
    from aerosafety.training.splits import SplitLeakageError

    input_root = Path(args.input)
    if not input_root.is_dir():
        print(f"ERROR: --input {input_root} is not a directory.", file=sys.stderr)
        return 1

    families = args.families if args.families else None
    limit = args.limit if args.limit else None

    cards = _load_cards(input_root, families, limit)
    print(f"Loaded {len(cards)} TaskCards ({sum(1 for c in cards if c.split=='dev')} dev, "
          f"{sum(1 for c in cards if c.split=='test')} test).")

    today = date.today().isoformat()
    output_dir = Path(args.output) if args.output else Path("data/training_sets") / today
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        if args.kind == "sft":
            out, manifest = build_sft_dataset(
                task_cards=cards,
                output_path=output_dir / "sft.jsonl",
            )
        elif args.kind == "dpo":
            out, manifest = build_dpo_preference_pairs(
                task_cards=cards,
                agent_traces=None,   # Phase 1: synthetic path
                output_path=output_dir / "dpo.jsonl",
            )
        elif args.kind == "verifier":
            out, manifest = build_verifier_dataset(
                task_cards=cards,
                agent_traces=None,  # Phase 1: synthetic path
                output_path=output_dir / "verifier.jsonl",
            )
        else:
            print(f"ERROR: Unknown --kind {args.kind!r}. Valid: sft, dpo, verifier.", file=sys.stderr)
            return 1

    except SplitLeakageError as exc:
        print(f"HARD ERROR — TEST SPLIT LEAKAGE DETECTED:\n{exc}", file=sys.stderr)
        return 2

    print(f"Written {manifest.n_examples} examples to {out}")
    print(f"Manifest: {out.with_suffix('.manifest.json')}")
    if manifest.partial_implementation:
        print(f"WARNING: PARTIAL IMPLEMENTATION — {manifest.partial_implementation_notes}")
    return 0


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m aerosafety.training.cli",
        description="Build Phase 2 training datasets from pilot TaskCards.",
    )
    sub = parser.add_subparsers(dest="command")

    build_cmd = sub.add_parser("build", help="Build a training dataset.")
    build_cmd.add_argument(
        "--kind", required=True, choices=["sft", "dpo", "verifier"],
        help="Training dataset type.",
    )
    build_cmd.add_argument(
        "--input", default="aerosafety/tasks",
        help="Root of aerosafety/tasks/ directory (default: aerosafety/tasks).",
    )
    build_cmd.add_argument(
        "--output", default=None,
        help="Output directory (default: data/training_sets/<today>/).",
    )
    build_cmd.add_argument(
        "--families", nargs="+", choices=["notam", "weather", "all"], default=["all"],
        help="Task families to include (default: all).",
    )
    build_cmd.add_argument(
        "--limit", type=int, default=None,
        help="Max number of TaskCards (default: all).",
    )
    build_cmd.add_argument(
        "--no-test-leak", action="store_true", default=True,
        help="Enforce test-split leakage prevention (always active; flag is declarative).",
    )

    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0

    return cmd_build(args)


if __name__ == "__main__":
    sys.exit(main())
