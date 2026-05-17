"""
Structural Protocols for AgentTrace and TaskCard.

These Protocols allow the eval framework to function before aerosafety.io
is published by infra-architect (task #1). When io.py is available, replace
these imports in consuming modules with the concrete classes.

AgentTrace fields used by metrics:
  - task_id: str
  - predicted_decision: str          # agent's final answer/decision
  - gold_decision: str               # ground-truth correct answer
  - confidence: float                # in [0, 1]; 1.0 = maximally confident
  - unsafe_recommendation: bool      # REQUIRED - must be set by agents-builder
  - citations: list[str]             # evidence IDs cited
  - unsupported_claims: list[str]    # claims flagged as unsupported
  - hallucinated_evidence: list[str] # citations that don't exist in corpus
  - contradictions: list[str]        # claims contradicting retrieved evidence
  - tool_calls: list[ToolCall]
  - severity: str                    # "Low"|"Medium"|"High"|"Critical"
  - token_count: int
  - tool_call_count: int
  - latency_seconds: float

TaskCard fields used by metrics:
  - task_id: str
  - required_safety_constraints: list[str]
  - required_tool_names: list[str]
  - ground_truth_consequence_points: list[str]
  - severity: str                    # same scale as AgentTrace.severity

ToolCall fields:
  - name: str                        # tool name called
  - inputs: dict
  - output: Any
  - correct_selection: bool
  - correct_input: bool
  - correct_interpretation: bool
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ToolCallProtocol(Protocol):
    name: str
    inputs: dict
    output: Any
    correct_selection: bool
    correct_input: bool
    correct_interpretation: bool


@runtime_checkable
class AgentTraceProtocol(Protocol):
    task_id: str
    predicted_decision: str
    gold_decision: str
    confidence: float
    unsafe_recommendation: bool
    citations: list[str]
    unsupported_claims: list[str]
    hallucinated_evidence: list[str]
    contradictions: list[str]
    tool_calls: list[ToolCallProtocol]
    severity: str
    token_count: int
    tool_call_count: int
    latency_seconds: float


@runtime_checkable
class TaskCardProtocol(Protocol):
    task_id: str
    required_safety_constraints: list[str]
    required_tool_names: list[str]
    ground_truth_consequence_points: list[str]
    severity: str


# ---------------------------------------------------------------------------
# Concrete stub classes — used in unit tests and until io.py is published
# ---------------------------------------------------------------------------

class ToolCallStub:
    """Concrete minimal ToolCall for tests and type-stub use."""

    def __init__(
        self,
        name: str,
        inputs: dict | None = None,
        output: Any = None,
        correct_selection: bool = True,
        correct_input: bool = True,
        correct_interpretation: bool = True,
    ) -> None:
        self.name = name
        self.inputs = inputs or {}
        self.output = output
        self.correct_selection = correct_selection
        self.correct_input = correct_input
        self.correct_interpretation = correct_interpretation


class AgentTraceStub:
    """Concrete minimal AgentTrace for tests and type-stub use."""

    def __init__(
        self,
        task_id: str,
        predicted_decision: str,
        gold_decision: str,
        confidence: float = 1.0,
        unsafe_recommendation: bool = False,
        citations: list[str] | None = None,
        unsupported_claims: list[str] | None = None,
        hallucinated_evidence: list[str] | None = None,
        contradictions: list[str] | None = None,
        tool_calls: list[ToolCallStub] | None = None,
        severity: str = "Low",
        token_count: int = 0,
        tool_call_count: int = 0,
        latency_seconds: float = 0.0,
    ) -> None:
        self.task_id = task_id
        self.predicted_decision = predicted_decision
        self.gold_decision = gold_decision
        self.confidence = confidence
        self.unsafe_recommendation = unsafe_recommendation
        self.citations = citations or []
        self.unsupported_claims = unsupported_claims or []
        self.hallucinated_evidence = hallucinated_evidence or []
        self.contradictions = contradictions or []
        self.tool_calls = tool_calls or []
        self.severity = severity
        self.token_count = token_count
        self.tool_call_count = tool_call_count
        self.latency_seconds = latency_seconds


class TaskCardStub:
    """Concrete minimal TaskCard for tests and type-stub use."""

    def __init__(
        self,
        task_id: str,
        required_safety_constraints: list[str] | None = None,
        required_tool_names: list[str] | None = None,
        ground_truth_consequence_points: list[str] | None = None,
        severity: str = "Low",
    ) -> None:
        self.task_id = task_id
        self.required_safety_constraints = required_safety_constraints or []
        self.required_tool_names = required_tool_names or []
        self.ground_truth_consequence_points = ground_truth_consequence_points or []
        self.severity = severity
