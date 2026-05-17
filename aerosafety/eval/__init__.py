"""
AeroSafetyEval evaluation framework.

This package implements all 10 evaluation metrics defined in proposal §12,
plus the runner, statistics, reporting, and failure taxonomy modules.

PARTIAL IMPLEMENTATION NOTE:
- CCS (consequence_coverage.py) uses MockJudge by default.
  Real LLM judge requires API plug-in (see ccs.py).
- All metrics depend on AgentTrace / TaskCard from aerosafety.io.
  Until that module is published, Protocols defined here are used.
"""

from aerosafety.eval.protocols import AgentTraceProtocol, TaskCardProtocol
from aerosafety.eval.failure_taxonomy import FailureCategory, FailureMode
from aerosafety.eval.tsr import task_success_rate
from aerosafety.eval.svr import safety_violation_rate
from aerosafety.eval.scor import safety_constraint_omission_rate
from aerosafety.eval.evidence_faithfulness import evidence_faithfulness
from aerosafety.eval.tool_use_reliability import tool_use_reliability
from aerosafety.eval.ccs import consequence_coverage_score
from aerosafety.eval.ofr import overconfident_failure_rate
from aerosafety.eval.swfr import severity_weighted_failure_rate
from aerosafety.eval.cass import cost_adjusted_safety_score
from aerosafety.eval.length_controlled import length_controlled_safety_recall
from aerosafety.eval.runner import EvalRunner
from aerosafety.eval.statistics import bootstrap_ci, wilcoxon_paired_test
from aerosafety.eval.reporting import write_jsonl_log, write_summary_markdown

__all__ = [
    "AgentTraceProtocol",
    "TaskCardProtocol",
    "FailureCategory",
    "FailureMode",
    "task_success_rate",
    "safety_violation_rate",
    "safety_constraint_omission_rate",
    "evidence_faithfulness",
    "tool_use_reliability",
    "consequence_coverage_score",
    "overconfident_failure_rate",
    "severity_weighted_failure_rate",
    "cost_adjusted_safety_score",
    "length_controlled_safety_recall",
    "EvalRunner",
    "bootstrap_ci",
    "wilcoxon_paired_test",
    "write_jsonl_log",
    "write_summary_markdown",
]
