"""
Consequence Coverage Score (CCS) — proposal §12.6

CCS = #covered_consequence_points / #ground_truth_consequence_points

For active consequence prediction tasks (Type C in proposal §8).

Each ground-truth consequence point is assessed by a Judge whether the agent
response covers it. Phase 1 uses a MockJudge for deterministic testing.
Real LLM judge is PARTIAL IMPLEMENTATION — plug in API later.

PARTIAL IMPLEMENTATION: Real LLM judge is not implemented.
Use MockJudge for all current evaluation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from aerosafety.eval.protocols import AgentTraceProtocol, TaskCardProtocol


@runtime_checkable
class Judge(Protocol):
    """
    Protocol for consequence-point coverage judges.

    A Judge decides whether a predicted agent response covers a given
    ground-truth consequence point.
    """

    def covers(
        self,
        predicted_response: str,
        consequence_point: str,
    ) -> bool:
        """Return True if predicted_response covers consequence_point."""
        ...


class MockJudge:
    """
    Deterministic mock judge for unit tests.

    Checks if consequence_point appears as a substring of predicted_response
    (case-insensitive). This is deterministic and suitable for tests with
    hand-crafted data.
    """

    def covers(self, predicted_response: str, consequence_point: str) -> bool:
        return consequence_point.lower() in predicted_response.lower()


# PARTIAL IMPLEMENTATION: Real LLM judge is not implemented.
# When aerosafety LLM infrastructure is ready, implement:
#
# class LLMJudge:
#     def __init__(self, llm_client, model_id: str, prompt_template: str) -> None: ...
#     def covers(self, predicted_response: str, consequence_point: str) -> bool: ...
#
# The judge should use structured output / chain-of-thought to decide coverage.


def consequence_coverage_score(
    traces: list[AgentTraceProtocol],
    task_cards: list[TaskCardProtocol],
    judge: Judge | None = None,
) -> dict:
    """
    Compute CCS over consequence-prediction traces.

    Parameters
    ----------
    traces     : list of AgentTrace (predicted_decision holds agent's consequence list)
    task_cards : list of TaskCard aligned with traces
    judge      : Judge instance. Defaults to MockJudge.
                 PARTIAL IMPLEMENTATION: pass a real LLMJudge when available.

    Returns
    -------
    dict with keys:
        ccs                      : float  (NaN if no consequence points)
        total_consequence_points : int
        total_covered            : int
        per_task                 : list[dict]
        judge_type               : str
    """
    if judge is None:
        judge = MockJudge()

    judge_type = type(judge).__name__

    if len(traces) != len(task_cards):
        raise ValueError(
            f"traces ({len(traces)}) and task_cards ({len(task_cards)}) must have the same length."
        )

    if not traces:
        return {
            "ccs": float("nan"),
            "total_consequence_points": 0,
            "total_covered": 0,
            "per_task": [],
            "judge_type": judge_type,
        }

    total_points = 0
    total_covered = 0
    per_task = []

    for trace, card in zip(traces, task_cards):
        if trace.task_id != card.task_id:
            raise ValueError(
                f"task_id mismatch: trace '{trace.task_id}' vs card '{card.task_id}'."
            )

        points = card.ground_truth_consequence_points
        covered = [
            cp for cp in points if judge.covers(trace.predicted_decision, cp)
        ]

        total_points += len(points)
        total_covered += len(covered)

        task_ccs = len(covered) / len(points) if points else float("nan")
        per_task.append(
            {
                "task_id": trace.task_id,
                "n_points": len(points),
                "n_covered": len(covered),
                "covered_points": covered,
                "uncovered_points": [p for p in points if p not in covered],
                "ccs": task_ccs,
            }
        )

    ccs = total_covered / total_points if total_points > 0 else float("nan")

    return {
        "ccs": ccs,
        "total_consequence_points": total_points,
        "total_covered": total_covered,
        "per_task": per_task,
        "judge_type": judge_type,
    }
