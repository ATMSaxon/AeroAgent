"""
Tool-Use Reliability — proposal §12.5

Five sub-metrics:
1. required_tool_call_rate      = #tasks_where_all_required_tools_called / N
2. correct_selection_rate       = #tool_calls_with_correct_selection / #tool_calls
3. correct_input_rate           = #tool_calls_with_correct_input / #tool_calls
4. correct_interpretation_rate  = #tool_calls_with_correct_interpretation / #tool_calls
5. misuse_rate                  = #tool_calls_with_any_error / #tool_calls
   (error = wrong selection OR wrong input OR wrong interpretation)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aerosafety.eval.protocols import AgentTraceProtocol, TaskCardProtocol


def tool_use_reliability(
    traces: list[AgentTraceProtocol],
    task_cards: list[TaskCardProtocol],
) -> dict:
    """
    Compute all five Tool-Use Reliability sub-metrics.

    Parameters
    ----------
    traces     : list of AgentTrace
    task_cards : list of TaskCard aligned with traces

    Returns
    -------
    dict with keys:
        required_tool_call_rate     : float
        correct_selection_rate      : float
        correct_input_rate          : float
        correct_interpretation_rate : float
        misuse_rate                 : float
        n_total                     : int
        n_tool_calls                : int
        per_task                    : list[dict]
    """
    if len(traces) != len(task_cards):
        raise ValueError(
            f"traces ({len(traces)}) and task_cards ({len(task_cards)}) must have the same length."
        )

    if not traces:
        return {
            "required_tool_call_rate": float("nan"),
            "correct_selection_rate": float("nan"),
            "correct_input_rate": float("nan"),
            "correct_interpretation_rate": float("nan"),
            "misuse_rate": float("nan"),
            "n_total": 0,
            "n_tool_calls": 0,
            "per_task": [],
        }

    n_all_required_called = 0
    total_tool_calls = 0
    n_correct_sel = 0
    n_correct_inp = 0
    n_correct_interp = 0
    n_misuse = 0
    per_task = []

    for trace, card in zip(traces, task_cards):
        if trace.task_id != card.task_id:
            raise ValueError(
                f"task_id mismatch: trace '{trace.task_id}' vs card '{card.task_id}'."
            )

        called_names = {tc.name for tc in trace.tool_calls}
        all_required_called = all(
            req in called_names for req in card.required_tool_names
        )
        if all_required_called:
            n_all_required_called += 1

        task_tool_calls = len(trace.tool_calls)
        task_correct_sel = sum(1 for tc in trace.tool_calls if tc.correct_selection)
        task_correct_inp = sum(1 for tc in trace.tool_calls if tc.correct_input)
        task_correct_interp = sum(1 for tc in trace.tool_calls if tc.correct_interpretation)
        task_misuse = sum(
            1
            for tc in trace.tool_calls
            if not (tc.correct_selection and tc.correct_input and tc.correct_interpretation)
        )

        total_tool_calls += task_tool_calls
        n_correct_sel += task_correct_sel
        n_correct_inp += task_correct_inp
        n_correct_interp += task_correct_interp
        n_misuse += task_misuse

        per_task.append(
            {
                "task_id": trace.task_id,
                "required_tools": card.required_tool_names,
                "called_tools": list(called_names),
                "all_required_called": all_required_called,
                "n_tool_calls": task_tool_calls,
                "n_misuse": task_misuse,
            }
        )

    n = len(traces)
    required_tool_call_rate = n_all_required_called / n

    def _rate(numerator: int, denominator: int) -> float:
        return numerator / denominator if denominator > 0 else float("nan")

    return {
        "required_tool_call_rate": required_tool_call_rate,
        "correct_selection_rate": _rate(n_correct_sel, total_tool_calls),
        "correct_input_rate": _rate(n_correct_inp, total_tool_calls),
        "correct_interpretation_rate": _rate(n_correct_interp, total_tool_calls),
        "misuse_rate": _rate(n_misuse, total_tool_calls),
        "n_total": n,
        "n_tool_calls": total_tool_calls,
        "per_task": per_task,
    }
