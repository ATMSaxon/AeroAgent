"""
Output-Length-Controlled Safety Recall — proposal §12.10

Evaluates hazard identification tasks under four output-length settings:
  top_3         : agent is constrained to list exactly 3 hazards
  top_5         : agent is constrained to list exactly 5 hazards
  top_10        : agent is constrained to list exactly 10 hazards
  unconstrained : agent lists as many hazards as it identifies

For each setting, compute recall:
  recall = #hazards_correctly_identified / #ground_truth_hazards

This prevents verbosity-driven score inflation (a verbose agent that lists
everything will score well unconstrained but is penalised when k is small).

AgentTrace.predicted_decision is expected to be a newline-separated or
list-based representation of hazards. For this module, it is treated as
a list stored in AgentTrace using a specialised HazardTrace structure.

HazardTrace is a thin wrapper that adds:
  hazard_predictions: list[str]   # ordered list of predicted hazards
  ground_truth_hazards: list[str] # from the TaskCard

Since AgentTrace may not yet carry hazard_predictions natively, this module
accepts either a bare AgentTrace (reads predicted_decision as a
newline-split list) or an explicit hazard_predictions argument.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aerosafety.eval.protocols import AgentTraceProtocol, TaskCardProtocol

LENGTH_SETTINGS = [3, 5, 10, None]  # None = unconstrained


@dataclass
class HazardEvalEntry:
    task_id: str
    hazard_predictions: list[str]
    ground_truth_hazards: list[str]


def _compute_recall_at_k(
    predictions: list[str],
    ground_truth: list[str],
    k: int | None,
) -> float:
    if not ground_truth:
        return float("nan")
    top_k = predictions[:k] if k is not None else predictions
    covered = sum(1 for gt in ground_truth if gt in top_k)
    return covered / len(ground_truth)


def length_controlled_safety_recall(
    entries: list[HazardEvalEntry],
) -> dict:
    """
    Evaluate hazard identification under top-3, top-5, top-10, and unconstrained settings.

    Parameters
    ----------
    entries : list of HazardEvalEntry, each providing ordered hazard predictions
              and ground-truth hazards for one task.

    Returns
    -------
    dict with keys:
        recall_top_3          : float  (NaN if no tasks)
        recall_top_5          : float
        recall_top_10         : float
        recall_unconstrained  : float
        n_total               : int
        per_task              : list[dict]
    """
    if not entries:
        return {
            "recall_top_3": float("nan"),
            "recall_top_5": float("nan"),
            "recall_top_10": float("nan"),
            "recall_unconstrained": float("nan"),
            "n_total": 0,
            "per_task": [],
        }

    per_task = []
    sums: dict[str, float] = {"top_3": 0.0, "top_5": 0.0, "top_10": 0.0, "unconstrained": 0.0}
    counts: dict[str, int] = {"top_3": 0, "top_5": 0, "top_10": 0, "unconstrained": 0}

    key_map = {3: "top_3", 5: "top_5", 10: "top_10", None: "unconstrained"}

    for entry in entries:
        task_result: dict = {"task_id": entry.task_id}
        for k in LENGTH_SETTINGS:
            key = key_map[k]
            r = _compute_recall_at_k(entry.hazard_predictions, entry.ground_truth_hazards, k)
            task_result[f"recall_{key}"] = r
            if not (r != r):  # not NaN
                sums[key] += r
                counts[key] += 1

        per_task.append(task_result)

    def _mean(key: str) -> float:
        return sums[key] / counts[key] if counts[key] > 0 else float("nan")

    return {
        "recall_top_3": _mean("top_3"),
        "recall_top_5": _mean("top_5"),
        "recall_top_10": _mean("top_10"),
        "recall_unconstrained": _mean("unconstrained"),
        "n_total": len(entries),
        "per_task": per_task,
    }


def build_hazard_entries_from_traces(
    traces: list[AgentTraceProtocol],
    task_cards: list[TaskCardProtocol],
) -> list[HazardEvalEntry]:
    """
    Convenience builder: construct HazardEvalEntry list from generic AgentTrace
    by treating predicted_decision as a newline-delimited list of hazards.
    Ground-truth hazards come from TaskCard.ground_truth_consequence_points.
    """
    if len(traces) != len(task_cards):
        raise ValueError("traces and task_cards must have the same length.")
    entries = []
    for trace, card in zip(traces, task_cards):
        preds = [h.strip() for h in trace.predicted_decision.splitlines() if h.strip()]
        entries.append(
            HazardEvalEntry(
                task_id=trace.task_id,
                hazard_predictions=preds,
                ground_truth_hazards=card.ground_truth_consequence_points,
            )
        )
    return entries
