"""
EvalRunner — orchestrates evaluation of an agent over a task set.

Interface:
    runner = EvalRunner(agent, task_set, llm=None)
    results = runner.run()

Outputs:
- per-task JSONL log (written via reporting.write_jsonl_log)
- aggregate metrics dict with 95% bootstrap CIs
- summary markdown table

The runner does NOT fabricate results. It calls the agent, collects traces,
and computes metrics from real outputs.

PARTIAL IMPLEMENTATION:
- agent and llm are Protocols; concrete implementations come from agents-builder.
- LLM judge for CCS is MockJudge until plug-in.
"""

from __future__ import annotations

import datetime
import math
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from aerosafety.eval.protocols import AgentTraceProtocol, TaskCardProtocol

from aerosafety.determinism import assert_eval_mode
from aerosafety.eval.cass import cost_adjusted_safety_score
from aerosafety.eval.ccs import MockJudge, consequence_coverage_score
from aerosafety.eval.evidence_faithfulness import evidence_faithfulness
from aerosafety.eval.length_controlled import (
    HazardEvalEntry,
    build_hazard_entries_from_traces,
    length_controlled_safety_recall,
)
from aerosafety.eval.ofr import overconfident_failure_rate
from aerosafety.eval.reporting import write_jsonl_log, write_summary_markdown
from aerosafety.eval.scor import safety_constraint_omission_rate
from aerosafety.eval.statistics import bootstrap_ci
from aerosafety.eval.svr import safety_violation_rate
from aerosafety.eval.swfr import severity_weighted_failure_rate
from aerosafety.eval.tool_use_reliability import tool_use_reliability
from aerosafety.eval.tsr import task_success_rate


@runtime_checkable
class AgentProtocol(Protocol):
    """
    Minimal protocol for an agent that can process a TaskCard and return a trace.
    Concrete implementation provided by agents-builder.
    """

    def run(self, task_card: "TaskCardProtocol") -> "AgentTraceProtocol":
        ...


class EvalRunner:
    """
    Runs an agent over a task set and computes all 10 evaluation metrics.

    Parameters
    ----------
    agent         : an object satisfying AgentProtocol
    task_set      : list of TaskCard
    llm           : optional LLM client for CCS judge (PARTIAL IMPLEMENTATION)
    output_dir    : directory for JSONL + markdown outputs (default: "eval_outputs/")
    n_bootstrap   : bootstrap resamples for CIs (default 1000)
    bootstrap_seed: random seed for reproducibility
    cass_kwargs   : extra kwargs forwarded to cost_adjusted_safety_score
    """

    def __init__(
        self,
        agent: AgentProtocol,
        task_set: list["TaskCardProtocol"],
        llm=None,
        output_dir: str | Path = "eval_outputs",
        n_bootstrap: int = 1000,
        bootstrap_seed: int = 42,
        cass_kwargs: dict | None = None,
    ) -> None:
        self.agent = agent
        self.task_set = task_set
        self.llm = llm
        self.output_dir = Path(output_dir)
        self.n_bootstrap = n_bootstrap
        self.bootstrap_seed = bootstrap_seed
        self.cass_kwargs = cass_kwargs or {}

    def run(self) -> dict:
        """
        Execute evaluation and return full results dict.

        Returns
        -------
        dict with keys:
            traces          : list[AgentTrace]  raw per-task traces (failures preserved)
            per_task        : list[dict]         per-task metric breakdown
            aggregate       : dict               all 10 metrics + CIs
            jsonl_path      : Path
            summary_path    : Path
            run_metadata    : dict
        """
        assert_eval_mode()

        traces: list["AgentTraceProtocol"] = []
        for card in self.task_set:
            trace = self.agent.run(card)
            traces.append(trace)

        judge = MockJudge()  # PARTIAL IMPLEMENTATION: swap for LLMJudge when ready

        tsr_result = task_success_rate(traces)
        svr_result = safety_violation_rate(traces)
        scor_result = safety_constraint_omission_rate(traces, self.task_set)
        ef_result = evidence_faithfulness(traces)
        tur_result = tool_use_reliability(traces, self.task_set)
        ccs_result = consequence_coverage_score(traces, self.task_set, judge=judge)
        ofr_result = overconfident_failure_rate(traces)
        swfr_result = severity_weighted_failure_rate(traces)
        cass_result = cost_adjusted_safety_score(traces, **self.cass_kwargs)
        lc_entries = build_hazard_entries_from_traces(traces, self.task_set)
        lc_result = length_controlled_safety_recall(lc_entries)

        correct_flags = [
            float(t.predicted_decision == t.gold_decision) for t in traces
        ]
        unsafe_flags = [float(t.unsafe_recommendation) for t in traces]
        swfr_values = [
            entry["contribution"] for entry in swfr_result["per_task"]
        ]

        def _ci(values: list[float], name: str) -> dict:
            return bootstrap_ci(
                values,
                n_resamples=self.n_bootstrap,
                seed=self.bootstrap_seed,
            )

        aggregate = {
            "tsr": tsr_result["tsr"],
            "tsr_ci": _ci(correct_flags, "tsr"),
            "svr": svr_result["svr"],
            "svr_ci": _ci(unsafe_flags, "svr"),
            "scor": scor_result["scor"],
            "evidence_faithfulness": {
                "citation_rate": ef_result["citation_rate"],
                "unsupported_claim_rate": ef_result["unsupported_claim_rate"],
                "hallucinated_evidence_rate": ef_result["hallucinated_evidence_rate"],
                "contradiction_rate": ef_result["contradiction_rate"],
            },
            "tool_use_reliability": {
                "required_tool_call_rate": tur_result["required_tool_call_rate"],
                "correct_selection_rate": tur_result["correct_selection_rate"],
                "correct_input_rate": tur_result["correct_input_rate"],
                "correct_interpretation_rate": tur_result["correct_interpretation_rate"],
                "misuse_rate": tur_result["misuse_rate"],
            },
            "ccs": ccs_result["ccs"],
            "ccs_judge": ccs_result["judge_type"],
            "ofr": ofr_result["ofr"],
            "swfr": swfr_result["swfr"],
            "swfr_ci": _ci(swfr_values, "swfr"),
            "cass": cass_result["cass"],
            "length_controlled": {
                "recall_top_3": lc_result["recall_top_3"],
                "recall_top_5": lc_result["recall_top_5"],
                "recall_top_10": lc_result["recall_top_10"],
                "recall_unconstrained": lc_result["recall_unconstrained"],
            },
            "n_total": len(traces),
        }

        per_task = _merge_per_task(
            tsr_result["per_task"],
            svr_result["per_task"],
            scor_result["per_task"],
            ef_result["per_task"],
            tur_result["per_task"],
            ccs_result["per_task"],
            ofr_result["per_task"],
            swfr_result["per_task"],
            lc_result["per_task"],
        )

        run_metadata = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "n_tasks": len(traces),
            "n_bootstrap": self.n_bootstrap,
            "bootstrap_seed": self.bootstrap_seed,
            "ccs_judge": ccs_result["judge_type"],
            "cass_alpha": self.cass_kwargs.get("alpha", 1.0),
            "cass_beta": self.cass_kwargs.get("beta", 1.0),
            "cass_gamma": self.cass_kwargs.get("gamma", 1.0),
        }

        self.output_dir.mkdir(parents=True, exist_ok=True)
        jsonl_path = write_jsonl_log(per_task, self.output_dir / "per_task_results.jsonl")
        summary_path = write_summary_markdown(
            {k: v for k, v in aggregate.items() if not isinstance(v, dict)},
            self.output_dir / "summary.md",
            run_metadata=run_metadata,
        )

        return {
            "traces": traces,
            "per_task": per_task,
            "aggregate": aggregate,
            "jsonl_path": jsonl_path,
            "summary_path": summary_path,
            "run_metadata": run_metadata,
        }


def _merge_per_task(*per_task_lists: list[dict]) -> list[dict]:
    """
    Merge per-task dicts from multiple metrics by task_id, preserving all fields.
    """
    if not per_task_lists or not per_task_lists[0]:
        return []

    merged: dict[str, dict] = {}
    for pt_list in per_task_lists:
        for entry in pt_list:
            tid = entry.get("task_id", "__unknown__")
            if tid not in merged:
                merged[tid] = {}
            merged[tid].update(entry)

    return list(merged.values())
