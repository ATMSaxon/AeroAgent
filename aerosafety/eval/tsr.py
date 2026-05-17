"""
Task Success Rate (TSR) — proposal §12.1

TSR = (1/N) * sum_i 1(predicted_i == gold_i)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aerosafety.eval.protocols import AgentTraceProtocol


def task_success_rate(
    traces: list[AgentTraceProtocol],
) -> dict:
    """
    Compute TSR over a list of AgentTrace objects.

    Returns
    -------
    dict with keys:
        tsr          : float   overall rate in [0, 1]
        n_total      : int
        n_correct    : int
        per_task     : list[dict]  one entry per trace with task_id + correct flag
    """
    if not traces:
        return {
            "tsr": float("nan"),
            "n_total": 0,
            "n_correct": 0,
            "per_task": [],
        }

    per_task = []
    n_correct = 0
    for t in traces:
        correct = t.predicted_decision == t.gold_decision
        if correct:
            n_correct += 1
        per_task.append({"task_id": t.task_id, "correct": correct})

    return {
        "tsr": n_correct / len(traces),
        "n_total": len(traces),
        "n_correct": n_correct,
        "per_task": per_task,
    }
