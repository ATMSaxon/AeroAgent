"""
runner.py — CLI entry point for AeroSafetyEval smoke test runs.

Usage:
    AEROSAFETY_EVAL_MODE=1 python -m aerosafety.smoke_test.runner \\
        --system all \\
        --family all \\
        --limit 10 \\
        --api mock \\
        --output-dir /tmp/smoke_outputs

Arguments:
    --system   1|2|3|4|7|all   Agent systems to run (default: all = 1,2,3,4)
    --family   notam|weather|all  Task families (default: all)
    --limit    N                Max tasks per system (default: 10)
    --api      mock|anthropic|openai  LLM backend (default: mock)
                                WARNING: only mock is implemented in T8a.
                                anthropic/openai require T8b with API key.
    --model    MODEL_ID         Model ID for real API runs (ignored for mock)
    --output-dir PATH           Output directory (default: smoke_test_outputs/)
    --dry-run                   Alias for --api mock (convenience flag)
    --n-bootstrap N             Bootstrap resamples (default: 100 for smoke, 1000 for full)

Per CLAUDE.md §5.1: assert_eval_mode() is called at entry.
Per CLAUDE.md §8.1: --api anthropic/openai will raise NotImplementedError until T8b.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from aerosafety.determinism import assert_eval_mode, lock_seeds


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="AeroSafetyEval smoke test runner (T8a: mock-only)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--system",
        default="all",
        help="Agent system(s): 1, 2, 3, 4, 7, or 'all' (default: all = 1,2,3,4)",
    )
    parser.add_argument(
        "--family",
        default="all",
        choices=["notam", "weather", "all"],
        help="Task family (default: all)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Max tasks per system (default: 10)",
    )
    parser.add_argument(
        "--api",
        default="mock",
        choices=["mock", "anthropic", "openai"],
        help="LLM backend (default: mock). anthropic/openai require T8b.",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Model ID for real API runs (ignored for mock)",
    )
    parser.add_argument(
        "--output-dir",
        default="smoke_test_outputs",
        help="Output directory (default: smoke_test_outputs/)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Alias for --api mock",
    )
    parser.add_argument(
        "--n-bootstrap",
        type=int,
        default=100,
        help="Bootstrap resamples (default: 100 for smoke)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed (default: 42)",
    )
    return parser.parse_args(argv)


def _parse_systems(system_arg: str) -> list[int]:
    if system_arg == "all":
        return [1, 2, 3, 4]
    parts = system_arg.split(",")
    result: list[int] = []
    for p in parts:
        p = p.strip()
        try:
            sid = int(p)
        except ValueError:
            raise ValueError(f"Invalid system id: {p!r}. Use integers 1-4 or 7, or 'all'.")
        if sid not in (1, 2, 3, 4, 7):
            raise ValueError(f"System {sid} is not available. Valid: 1, 2, 3, 4, 7.")
        result.append(sid)
    return result


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    # assert_eval_mode must be called before any evaluation work
    assert_eval_mode()
    lock_seeds(args.seed)

    # Resolve dry-run alias
    api = "mock" if args.dry_run else args.api

    # T8b guard — real API not implemented in T8a
    if api in ("anthropic", "openai"):
        print(
            f"ERROR: --api {api} is NOT IMPLEMENTED in T8a.\n"
            "Real API execution requires T8b with a user-provided API key and budget approval.\n"
            "Use --api mock (or --dry-run) for pipeline validation.",
            file=sys.stderr,
        )
        return 1

    try:
        systems = _parse_systems(args.system)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    families = None if args.family == "all" else [args.family]
    output_dir = Path(args.output_dir)

    print(f"AeroSafetyEval smoke test runner (T8a — MockLLM only)")
    print(f"  Systems  : {systems}")
    print(f"  Families : {args.family}")
    print(f"  Limit    : {args.limit} tasks per system")
    print(f"  API      : {api} (MOCK — no real LLM calls)")
    print(f"  Output   : {output_dir}")
    print()

    from aerosafety.smoke_test.mock_run import run_mock_pipeline  # noqa: PLC0415
    from aerosafety.smoke_test.report import generate_comparison_report  # noqa: PLC0415

    pipeline_result = run_mock_pipeline(
        systems=systems,
        families=families,
        limit=args.limit,
        output_dir=output_dir,
        n_bootstrap=args.n_bootstrap,
        seed=args.seed,
    )

    # Generate comparison report
    import datetime  # noqa: PLC0415
    run_metadata = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "api": api,
        "model": args.model or "mock/test-model",
        "systems": str(systems),
        "families": args.family,
        "limit_per_system": args.limit,
        "n_bootstrap": args.n_bootstrap,
        "seed": args.seed,
        "mock": True,
        "note": "MOCK RUN — no research value. Pipeline plumbing validation only.",
    }

    report_path = generate_comparison_report(
        system_results=pipeline_result["system_results"],
        output_path=output_dir / "comparison_report.md",
        run_label=f"Pilot ({args.family})",
        mock=True,
        run_metadata=run_metadata,
    )

    if pipeline_result["all_valid"]:
        print(f"Pipeline validation: PASS")
    else:
        print(f"Pipeline validation: FAIL")
        for err in pipeline_result["errors"]:
            print(f"  ERROR: {err}", file=sys.stderr)

    print(f"Comparison report  : {report_path}")
    print(f"Per-system outputs : {output_dir}/system*/")

    # Print a brief aggregate summary per system
    print()
    print("Aggregate metrics (MOCK — no research value):")
    for sys_name, res in pipeline_result["system_results"].items():
        agg = res.get("aggregate", {})
        tsr = agg.get("tsr", float("nan"))
        svr = agg.get("svr", float("nan"))
        n = agg.get("n_total", 0)
        print(f"  {sys_name}: TSR={tsr:.3f}  SVR={svr:.3f}  N={n}")

    return 0 if pipeline_result["all_valid"] else 2


if __name__ == "__main__":
    sys.exit(main())
