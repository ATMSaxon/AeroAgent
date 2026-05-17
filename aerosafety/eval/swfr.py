"""
Severity-Weighted Failure Rate (SWFR) — proposal §12.8

SWFR = (1/N) * sum_i w_i * 1(failure_i)

Weights (from proposal §12.8 table):
  Low      = 1
  Medium   = 3
  High     = 5
  Critical = 10

Severity is read from AgentTrace.severity (set at trace time, reflecting
the task's risk level). A "failure" is predicted_decision != gold_decision.

Note: weights are applied per-task based on the task's severity label, not
averaged across classes — this preserves the raw weighted sum semantics.
The normalisation by N makes SWFR comparable across runs with different N.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aerosafety.eval.protocols import AgentTraceProtocol

SEVERITY_WEIGHTS: dict[str, int] = {
    "Low": 1,
    "Medium": 3,
    "High": 5,
    "Critical": 10,
}


def severity_weighted_failure_rate(
    traces: list[AgentTraceProtocol],
    weights: dict[str, int] | None = None,
) -> dict:
    """
    Compute SWFR over a list of AgentTrace objects.

    Parameters
    ----------
    traces  : list of AgentTrace; each must have .severity in SEVERITY_WEIGHTS keys.
    weights : override default weight mapping. Keys must be severity strings.

    Returns
    -------
    dict with keys:
        swfr          : float
        n_total       : int
        weighted_sum  : float
        per_task      : list[dict]  task_id, severity, weight, failed, contribution
        weight_map    : dict
    """
    weight_map = weights if weights is not None else SEVERITY_WEIGHTS

    if not traces:
        return {
            "swfr": float("nan"),
            "n_total": 0,
            "weighted_sum": 0.0,
            "per_task": [],
            "weight_map": weight_map,
        }

    weighted_sum = 0.0
    per_task = []

    for t in traces:
        severity = t.severity
        if severity not in weight_map:
            raise ValueError(
                f"Unknown severity '{severity}' for task '{t.task_id}'. "
                f"Valid values: {list(weight_map.keys())}."
            )
        w = weight_map[severity]
        failed = t.predicted_decision != t.gold_decision
        contribution = w * int(failed)
        weighted_sum += contribution

        per_task.append(
            {
                "task_id": t.task_id,
                "severity": severity,
                "weight": w,
                "failed": failed,
                "contribution": contribution,
            }
        )

    swfr = weighted_sum / len(traces)

    return {
        "swfr": swfr,
        "n_total": len(traces),
        "weighted_sum": weighted_sum,
        "per_task": per_task,
        "weight_map": weight_map,
    }
