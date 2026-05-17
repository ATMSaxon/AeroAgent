"""
Shared Pydantic schemas for AeroSafetyEval.

All agents, tools, evaluation modules, and logging pipelines must import
from this module — do not duplicate or shadow these types elsewhere.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# ToolCall
# ---------------------------------------------------------------------------

class ToolCall(BaseModel):
    """Record of a single tool invocation by an agent."""

    name: str
    args: dict[str, Any]
    result: Any | None = None
    error: str | None = None
    runtime_ms: float | None = None


# ---------------------------------------------------------------------------
# RetrievedDoc
# ---------------------------------------------------------------------------

class RetrievedDoc(BaseModel):
    """A single document chunk retrieved during RAG."""

    doc_id: str
    source: str
    chunk_text: str
    score: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Recommendation
# ---------------------------------------------------------------------------

class Recommendation(BaseModel):
    """Structured agent recommendation on an aviation decision task."""

    decision: str
    rationale: str
    safety_constraints_cited: list[str] = Field(default_factory=list)
    evidence_cited: list[str] = Field(default_factory=list)
    escalation_recommended: bool = False
    uncertainty_flags: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# AgentTrace
# ---------------------------------------------------------------------------

class AgentTrace(BaseModel):
    """
    Complete reproducible record of one agent execution on one TaskCard.

    Per CLAUDE.md §5.1: all fields required for full reproducibility.
    Absent optional fields must be explicitly None — do not silently omit.
    """

    # Identity
    task_id: str
    run_id: str

    # Model provenance
    model_version: str
    model_provider: str

    # Prompt provenance (SHA-256 hex of the serialised prompt string)
    prompt_hash: str

    # Full conversation
    system_prompt: str
    messages: list[dict[str, Any]]

    # Tool execution log
    tool_calls: list[ToolCall] = Field(default_factory=list)

    # Retrieval log
    retrieved_docs: list[RetrievedDoc] = Field(default_factory=list)

    # Output
    final_recommendation: Recommendation | None = None
    raw_output: str | None = None

    # Confidence (0–1); None means the agent did not emit a calibrated score
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)

    # Escalation flag
    requested_escalation: bool = False

    # Performance
    total_runtime_ms: float | None = None
    token_usage: dict[str, int] | None = None  # {"prompt": N, "completion": M, "total": N+M}

    # Hardware / environment
    hardware: dict[str, Any] | None = None

    # Timestamps (ISO-8601)
    started_at: str | None = None
    finished_at: str | None = None

    # Failure flags (per CLAUDE.md §4.3)
    had_tool_error: bool = False
    had_retrieval_error: bool = False
    had_parse_error: bool = False


# ---------------------------------------------------------------------------
# TaskCard
# ---------------------------------------------------------------------------

SeverityLevel = Literal["Low", "Medium", "High", "Critical"]

TaskType = Literal["A", "B", "C", "D"]


class TaskProvenance(BaseModel):
    """Source citation for a TaskCard."""

    # One of: a human-readable citation string OR "SYNTHETIC"
    source: str
    access_date: str | None = None   # ISO-8601 date; None iff source == "SYNTHETIC"
    # Required when source == "SYNTHETIC"
    generation_rule: str | None = None
    # License/data-use notes
    license: str | None = None


# ---------------------------------------------------------------------------
# Multimodal
# ---------------------------------------------------------------------------

AttachmentKind = Literal["image", "pdf_region", "trajectory_plot", "lidar_plot"]


class MultimodalAttachment(BaseModel):
    """
    A single multimodal asset attached to a TaskCard.

    Per CLAUDE.md §2.2: all attachments must carry provenance; synthetic
    assets must be labeled as such in provenance.source == "SYNTHETIC".
    sha256 is the hex digest of the file at file_path and is verified
    by validate_attachments() — NOT during model construction (avoids I/O).
    """

    attachment_id: str
    kind: AttachmentKind
    # Path relative to the base_dir passed to validate_attachments()
    file_path: str
    description: str
    provenance: TaskProvenance
    # SHA-256 hex digest of the file contents; verified out-of-band
    sha256: str


class TaskCard(BaseModel):
    """
    Canonical unit of evaluation in AeroSafetyEval.

    Every field is required for evaluation integrity (CLAUDE.md §1.4, §3.1).
    Synthetic tasks must set provenance.source == "SYNTHETIC" and provide
    provenance.generation_rule; they must never be mixed with real tasks
    without explicit split-labelling.
    """

    task_id: str
    family: str  # e.g. "weather_dispatch", "notam_compliance"

    # Task type per §8 of proposal
    task_type: TaskType

    # The prompt shown to the agent (text; multimodal refs are separate attachments)
    prompt: str

    # Ground truth
    gold_decision: str
    required_safety_constraints: list[str]
    acceptable_variants: list[str] = Field(default_factory=list)
    evidence_requirements: list[str] = Field(default_factory=list)

    # Safety metadata
    severity: SeverityLevel
    escalation_required: bool
    failure_mode_labels: list[str] = Field(default_factory=list)

    # Data provenance — mandatory; no task without a provenance record
    provenance: TaskProvenance

    # Optional split tag
    split: Literal["dev", "test"] | None = None

    # Multimodal attachments — empty list for text-only tasks (backward compat)
    attachments: list[MultimodalAttachment] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# validate_attachments — out-of-band I/O check (CLAUDE.md §8.1)
# ---------------------------------------------------------------------------

def validate_attachments(card: TaskCard, base_dir: Path) -> None:
    """
    Verify that every attachment in card.attachments exists on disk and that
    its sha256 matches the stored digest.

    NOT called during Pydantic model validation — I/O must stay out of the
    deserialization path (CLAUDE.md §8.1: no silent failure, but also no
    hidden side-effects during schema construction).

    Raises:
        FileNotFoundError: if an attachment file is absent.
        ValueError: if the sha256 digest does not match.
    """
    for att in card.attachments:
        full_path = base_dir / att.file_path
        if not full_path.exists():
            raise FileNotFoundError(
                f"Attachment '{att.attachment_id}' file not found: {full_path}"
            )
        digest = hashlib.sha256(full_path.read_bytes()).hexdigest()
        if digest != att.sha256:
            raise ValueError(
                f"Attachment '{att.attachment_id}' sha256 mismatch: "
                f"expected {att.sha256!r}, got {digest!r} for {full_path}"
            )
