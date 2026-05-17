"""
Adapters bridging aerosafety.io (AgentTrace, TaskCard) to the eval framework.

The concrete AgentTrace from io.py does not carry all eval-specific fields
(unsafe_recommendation, per-tool correctness annotations, etc.) because those
are determined at evaluation time, not agent execution time. This module
provides:

1. EvalAnnotation — eval-time annotation added on top of a raw AgentTrace.
2. EvalTaskCard — wraps io.TaskCard and adds eval-specific fields.
3. make_eval_view — combines AgentTrace + EvalAnnotation + TaskCard into the
   flat view consumed by all metric functions.
4. EvalView — the flat dataclass consumed by metrics.

Design principle: agents-builder writes AgentTrace; eval-builder adds
EvalAnnotation; nothing is fabricated — if a field is unknown, it raises.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from aerosafety.io import AgentTrace, TaskCard, ToolCall


# ---------------------------------------------------------------------------
# Per-tool evaluation annotation
# ---------------------------------------------------------------------------

@dataclass
class ToolCallAnnotation:
    """Evaluation-time annotation for a single tool call."""

    tool_call_index: int       # index into AgentTrace.tool_calls
    correct_selection: bool    # was the right tool chosen?
    correct_input: bool        # were the inputs correct?
    correct_interpretation: bool  # was the output interpreted correctly?


# ---------------------------------------------------------------------------
# EvalAnnotation — eval-time fields added to an AgentTrace
# ---------------------------------------------------------------------------

@dataclass
class EvalAnnotation:
    """
    Evaluation-time annotation for one AgentTrace.

    Fields that cannot be determined from the raw trace alone must be
    provided explicitly. Do NOT guess or impute — raise if unknown.

    unsafe_recommendation : bool
        Whether the agent made an unsafe recommendation. MUST be set.
        Raise if not annotated (set to None means "not annotated").
    unsupported_claims : list[str]
        IDs / short descriptions of claims the agent made without citation.
    hallucinated_evidence : list[str]
        Citation IDs the agent used that do not exist in the evidence corpus.
    contradictions : list[str]
        Claims the agent made that contradict retrieved evidence.
    tool_annotations : list[ToolCallAnnotation]
        Per-tool-call correctness annotations (same order as trace.tool_calls).
    """

    unsafe_recommendation: Optional[bool] = None
    unsupported_claims: list[str] = field(default_factory=list)
    hallucinated_evidence: list[str] = field(default_factory=list)
    contradictions: list[str] = field(default_factory=list)
    tool_annotations: list[ToolCallAnnotation] = field(default_factory=list)


# ---------------------------------------------------------------------------
# EvalTaskCard — TaskCard extended with eval-specific fields
# ---------------------------------------------------------------------------

@dataclass
class EvalTaskCard:
    """
    Wraps a TaskCard with additional fields needed by eval metrics.

    required_tool_names               : list[str]
        Tool names the agent must have called for this task (for tool-use reliability).
    ground_truth_consequence_points   : list[str]
        Ground-truth consequence point IDs/texts (for CCS and length-controlled recall).
    """

    task_card: TaskCard
    required_tool_names: list[str] = field(default_factory=list)
    ground_truth_consequence_points: list[str] = field(default_factory=list)

    @property
    def task_id(self) -> str:
        return self.task_card.task_id

    @property
    def required_safety_constraints(self) -> list[str]:
        return self.task_card.required_safety_constraints

    @property
    def severity(self) -> str:
        return self.task_card.severity

    @property
    def gold_decision(self) -> str:
        return self.task_card.gold_decision


# ---------------------------------------------------------------------------
# EvalView — flat dataclass consumed by all metric functions
# ---------------------------------------------------------------------------

@dataclass
class AnnotatedToolCall:
    name: str
    inputs: dict
    output: Any
    correct_selection: bool
    correct_input: bool
    correct_interpretation: bool


@dataclass
class EvalView:
    """
    Flat view of one evaluation instance, combining trace + annotation + task.

    This satisfies both AgentTraceProtocol and TaskCardProtocol from protocols.py,
    and is what metric functions should receive.
    """

    # Identity
    task_id: str

    # Decision
    predicted_decision: str
    gold_decision: str

    # Confidence (default 1.0 if agent did not emit calibrated score)
    confidence: float

    # Safety flag — REQUIRED; raises if not set
    unsafe_recommendation: bool

    # Evidence faithfulness fields
    citations: list[str]
    unsupported_claims: list[str]
    hallucinated_evidence: list[str]
    contradictions: list[str]

    # Tool use
    tool_calls: list[AnnotatedToolCall]

    # Cost fields
    severity: str
    token_count: int
    tool_call_count: int
    latency_seconds: float


def make_eval_view(
    trace: AgentTrace,
    annotation: EvalAnnotation,
    eval_card: EvalTaskCard,
) -> EvalView:
    """
    Combine a raw AgentTrace + EvalAnnotation + EvalTaskCard into an EvalView.

    Raises
    ------
    ValueError
        If unsafe_recommendation is None (not annotated).
    ValueError
        If task_ids do not match.
    """
    if trace.task_id != eval_card.task_id:
        raise ValueError(
            f"task_id mismatch: trace '{trace.task_id}' vs card '{eval_card.task_id}'."
        )
    if annotation.unsafe_recommendation is None:
        raise ValueError(
            f"EvalAnnotation.unsafe_recommendation is None for task '{trace.task_id}'. "
            "This field MUST be set by eval annotators — do not guess."
        )

    # predicted_decision: prefer structured recommendation, fall back to raw_output
    if trace.final_recommendation is not None:
        predicted_decision = trace.final_recommendation.decision
    elif trace.raw_output is not None:
        predicted_decision = trace.raw_output
    else:
        predicted_decision = ""

    # citations = safety constraints cited + evidence cited (from Recommendation)
    if trace.final_recommendation is not None:
        citations = (
            trace.final_recommendation.safety_constraints_cited
            + trace.final_recommendation.evidence_cited
        )
    else:
        citations = []

    # confidence
    confidence = trace.confidence if trace.confidence is not None else 1.0

    # token count
    if trace.token_usage is not None:
        token_count = trace.token_usage.get("total", 0)
    else:
        token_count = 0

    # tool call count
    tool_call_count = len(trace.tool_calls)

    # latency
    latency_seconds = (
        trace.total_runtime_ms / 1000.0 if trace.total_runtime_ms is not None else 0.0
    )

    # annotated tool calls
    ann_index = {a.tool_call_index: a for a in annotation.tool_annotations}
    annotated_tools: list[AnnotatedToolCall] = []
    for i, tc in enumerate(trace.tool_calls):
        ann = ann_index.get(i)
        annotated_tools.append(
            AnnotatedToolCall(
                name=tc.name,
                inputs=tc.args,
                output=tc.result,
                correct_selection=ann.correct_selection if ann else True,
                correct_input=ann.correct_input if ann else True,
                correct_interpretation=ann.correct_interpretation if ann else True,
            )
        )

    return EvalView(
        task_id=trace.task_id,
        predicted_decision=predicted_decision,
        gold_decision=eval_card.gold_decision,
        confidence=confidence,
        unsafe_recommendation=annotation.unsafe_recommendation,
        citations=citations,
        unsupported_claims=annotation.unsupported_claims,
        hallucinated_evidence=annotation.hallucinated_evidence,
        contradictions=annotation.contradictions,
        tool_calls=annotated_tools,
        severity=eval_card.severity,
        token_count=token_count,
        tool_call_count=tool_call_count,
        latency_seconds=latency_seconds,
    )
