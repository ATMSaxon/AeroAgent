"""
Review record schema referenced by docs/expert_review_protocol.md.

PARTIAL IMPLEMENTATION (2026-05-18): the schema is defined but no
review records have been created yet — that requires PI-led expert
recruitment per the protocol §3 onboarding flow. Stub exists so that
the contamination_check audit and any future review-data ingest can
import from a stable location.
"""

from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field


class ReviewRecord(BaseModel):
    """One reviewer's evaluation of one TaskCard (per protocol §4)."""

    reviewer_id: str
    task_id: str
    review_timestamp: str  # ISO-8601 UTC

    elapsed_seconds: Optional[int] = None

    # Validation judgements
    realism_score: int = Field(ge=1, le=5)
    clarity_score: int = Field(ge=1, le=5)
    factual_correctness: Literal["True", "False", "Cannot determine"]

    # Ground-truth judgements
    agrees_with_gold_decision: bool
    proposed_gold_decision_if_disagrees: Optional[str] = None
    agrees_with_required_safety_constraints: bool
    missing_safety_constraints_to_add: list[str] = Field(default_factory=list)
    constraints_to_remove: list[str] = Field(default_factory=list)
    agrees_with_severity: bool
    proposed_severity_if_disagrees: Optional[Literal["Low", "Medium", "High", "Critical"]] = None
    agrees_with_escalation_required: bool

    # Failure-mode tagging
    applicable_failure_modes: list[str] = Field(default_factory=list)

    # Disqualification flags
    contains_outdated_rule: bool = False
    contains_jurisdiction_confusion: bool = False
    contains_safety_compromise: bool = False

    free_text_comments: Optional[str] = None
