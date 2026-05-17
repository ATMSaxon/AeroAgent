"""
Reporting utilities — proposal §3.3, CLAUDE.md §3.3.

Responsibilities:
1. write_jsonl_log: emit per-task result JSONL (failures MUST be preserved)
2. write_summary_markdown: emit aggregate metric table as markdown

NO plotting. No fabricated numbers. Failures are NEVER aggregated away.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any


def write_jsonl_log(
    per_task_results: list[dict],
    output_path: str | Path,
) -> Path:
    """
    Write per-task evaluation results to a JSONL file.

    Each line is a JSON object. Failure cases are preserved with full detail
    (CLAUDE.md §3.3 — suppressing failures is prohibited).

    Parameters
    ----------
    per_task_results : list of dicts, one per task. Must include at minimum:
                       task_id, correct (bool), and any metric breakdown.
    output_path      : file path (created or overwritten)

    Returns
    -------
    Path of the written file.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as fh:
        for record in per_task_results:
            fh.write(json.dumps(record, ensure_ascii=False, default=_json_default) + "\n")

    return output_path


def write_summary_markdown(
    aggregate_metrics: dict[str, Any],
    output_path: str | Path,
    run_metadata: dict[str, Any] | None = None,
) -> Path:
    """
    Write aggregate metrics as a markdown table.

    Parameters
    ----------
    aggregate_metrics : dict mapping metric_name → value (or nested dict with CI)
    output_path       : file path (created or overwritten)
    run_metadata      : optional run-level metadata (model, date, seed, etc.)

    Returns
    -------
    Path of the written file.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = ["# AeroSafetyEval — Aggregate Metrics\n"]

    if run_metadata:
        lines.append("## Run Metadata\n")
        lines.append("| Key | Value |")
        lines.append("|-----|-------|")
        for k, v in run_metadata.items():
            lines.append(f"| {k} | {v} |")
        lines.append("")

    lines.append("## Metrics\n")
    lines.append("| Metric | Value | CI Lower | CI Upper | N |")
    lines.append("|--------|-------|----------|----------|---|")

    for metric_name, value in aggregate_metrics.items():
        if isinstance(value, dict) and "point_estimate" in value:
            pe = _fmt(value.get("point_estimate"))
            cil = _fmt(value.get("ci_lower"))
            ciu = _fmt(value.get("ci_upper"))
            n = value.get("n_samples", "—")
            lines.append(f"| {metric_name} | {pe} | {cil} | {ciu} | {n} |")
        elif isinstance(value, float):
            lines.append(f"| {metric_name} | {_fmt(value)} | — | — | — |")
        else:
            lines.append(f"| {metric_name} | {value} | — | — | — |")

    lines.append("")
    lines.append(
        "> **Note:** All metrics are computed from executed evaluation runs. "
        "Failure cases are preserved in the accompanying JSONL log. "
        "No fabricated numbers."
    )

    with output_path.open("w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")

    return output_path


def _fmt(v: Any) -> str:
    if v is None:
        return "—"
    if isinstance(v, float):
        if math.isnan(v):
            return "NaN"
        return f"{v:.4f}"
    return str(v)


def _json_default(obj: Any) -> Any:
    if isinstance(obj, float) and math.isnan(obj):
        return "NaN"
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")
