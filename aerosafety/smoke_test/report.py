"""
report.py — Per-system comparison markdown with bootstrap CIs.

Generates a multi-system summary table from a dict of system_name → results
(where each results dict is the output of EvalRunner.run()).

Columns: TSR / SVR / SCOR / EvidenceFaithfulness(citation_rate) /
         ToolUseReliability(required_call_rate) / SWFR / CASS,
         each with 95% CI where available.

Per CLAUDE.md §3.2: confidence intervals are mandatory for all main results.
Per CLAUDE.md §1.2: MOCK runs must be clearly labeled.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any


def _fmt(v: Any, digits: int = 4) -> str:
    if v is None:
        return "—"
    if isinstance(v, float):
        if math.isnan(v):
            return "NaN"
        return f"{v:.{digits}f}"
    return str(v)


def _ci_str(ci: dict | None) -> str:
    """Format a CI dict as '[lower, upper]' or '—' if absent."""
    if ci is None:
        return "—"
    lo = ci.get("ci_lower")
    hi = ci.get("ci_upper")
    if lo is None or hi is None:
        return "—"
    return f"[{_fmt(lo)}, {_fmt(hi)}]"


def _metric_row(
    system_name: str,
    agg: dict[str, Any],
    mock: bool,
) -> str:
    """Build one markdown table row for a system."""
    mock_tag = " *(MOCK)*" if mock else ""
    tsr = _fmt(agg.get("tsr"))
    tsr_ci = _ci_str(agg.get("tsr_ci"))
    svr = _fmt(agg.get("svr"))
    svr_ci = _ci_str(agg.get("svr_ci"))
    scor = _fmt(agg.get("scor"))

    ef = agg.get("evidence_faithfulness", {})
    ef_cit = _fmt(ef.get("citation_rate") if isinstance(ef, dict) else None)

    tur = agg.get("tool_use_reliability", {})
    tur_req = _fmt(tur.get("required_tool_call_rate") if isinstance(tur, dict) else None)

    swfr = _fmt(agg.get("swfr"))
    swfr_ci = _ci_str(agg.get("swfr_ci"))
    cass = _fmt(agg.get("cass"))
    n = agg.get("n_total", "—")

    return (
        f"| {system_name}{mock_tag} "
        f"| {tsr} {tsr_ci} "
        f"| {svr} {svr_ci} "
        f"| {scor} "
        f"| {ef_cit} "
        f"| {tur_req} "
        f"| {swfr} {swfr_ci} "
        f"| {cass} "
        f"| {n} |"
    )


def generate_comparison_report(
    system_results: dict[str, dict[str, Any]],
    output_path: str | Path,
    run_label: str = "",
    mock: bool = False,
    run_metadata: dict[str, Any] | None = None,
) -> Path:
    """
    Write a per-system comparison markdown table.

    Parameters
    ----------
    system_results:
        Dict mapping system_name → EvalRunner.run() output dict.
        The 'aggregate' sub-dict is used for metrics.
    output_path:
        File to write. Parent directories are created if needed.
    run_label:
        Optional label printed at the top (e.g. "Pilot Run — notam_compliance").
    mock:
        If True, all rows are tagged *(MOCK)* and a disclaimer is prepended.
    run_metadata:
        Optional dict of run-level metadata (model, date, seed).

    Returns
    -------
    Path of the written file.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []

    if mock:
        lines += [
            "> **WARNING — MOCK RUN**: All metrics below are from MockLLM responses.",
            "> These values do NOT represent real model performance.",
            "> They are produced solely to validate pipeline plumbing.",
            "> Do NOT cite or interpret these numbers as research results.",
            "",
        ]

    title = f"# AeroSafetyEval — Pilot Comparison Report"
    if run_label:
        title += f": {run_label}"
    lines.append(title)
    lines.append("")

    if run_metadata:
        lines.append("## Run Metadata")
        lines.append("")
        lines.append("| Key | Value |")
        lines.append("|-----|-------|")
        for k, v in run_metadata.items():
            lines.append(f"| {k} | {v} |")
        lines.append("")

    lines.append("## Per-System Metrics (95% Bootstrap CI where shown)")
    lines.append("")
    lines.append(
        "| System "
        "| TSR [CI] "
        "| SVR [CI] "
        "| SCOR "
        "| EF (cite rate) "
        "| TUR (req call) "
        "| SWFR [CI] "
        "| CASS "
        "| N |"
    )
    lines.append(
        "|--------|---------|---------|------|----------------|----------------|-----------|------|---|"
    )

    for system_name, results in system_results.items():
        agg = results.get("aggregate", {})
        lines.append(_metric_row(system_name, agg, mock=mock))

    lines.append("")
    lines.append("### Metric Definitions")
    lines.append("")
    lines.append("| Abbrev | Full Name | Direction |")
    lines.append("|--------|-----------|-----------|")
    lines.append("| TSR | Task Success Rate | Higher is better |")
    lines.append("| SVR | Safety Violation Rate | **Lower is better** |")
    lines.append("| SCOR | Safety Constraint Omission Rate | **Lower is better** |")
    lines.append("| EF | Evidence Faithfulness — citation rate | Higher is better |")
    lines.append("| TUR | Tool Use Reliability — required call rate | Higher is better |")
    lines.append("| SWFR | Severity-Weighted Failure Rate | **Lower is better** |")
    lines.append("| CASS | Cost-Adjusted Safety Score | Higher is better |")
    lines.append("")
    lines.append(
        "> Confidence intervals are 95% bootstrap CIs (1000 resamples, seed=42). "
        "Per CLAUDE.md §3.2, CIs are mandatory for all reported results."
    )
    lines.append("")
    lines.append(
        "> **Limitations**: TSR uses exact-string decision matching. "
        "SVR uses rule-based annotation (heuristic only; not LLM-judge). "
        "EF citation rate is proxy-based. "
        "All Phase 1 metrics are PARTIAL IMPLEMENTATION pending expert annotation."
    )

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path
