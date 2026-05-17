"""
Pydantic schemas for Phase 2 training dataset artefacts.

Every training example records full source lineage so that:
  - dataset provenance is auditable per CLAUDE.md §6.1
  - test-split exclusion can be verified post-hoc
  - downstream fine-tuning scripts know the generation method

License tag "PILOT — NOT EXPERT-REVIEWED" is mandatory on all Phase 1 outputs.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# SFT
# ---------------------------------------------------------------------------

class SFTExample(BaseModel):
    """
    One supervised fine-tuning example in HuggingFace / TRL SFTTrainer format.

    Fields match the standard `{instruction, input, output}` convention so this
    object can be serialised directly to JSONL for use with trl.SFTTrainer or
    any HF dataset loader.
    """

    instruction: str
    input: str
    output: str

    # Lineage (mandatory per CLAUDE.md §6.1)
    source_task_id: str
    source_family: str
    source_split: str   # always "dev" for SFT — test cards are excluded at source
    generation_timestamp: str = Field(default_factory=_utcnow)
    generation_method: Literal["gold_card_expansion"] = "gold_card_expansion"
    license: str = "PILOT — NOT EXPERT-REVIEWED"


# ---------------------------------------------------------------------------
# DPO
# ---------------------------------------------------------------------------

class DPOPair(BaseModel):
    """
    One DPO preference pair in standard {prompt, chosen, rejected} format.

    PARTIAL IMPLEMENTATION — Phase 1 uses synthetic chosen/rejected derivation
    because real AgentTrace pairs from T8b do not yet exist.

    Synthetic generation rule is documented in `synthetic_generation_rule`.
    Real AgentTrace-based pairs will replace these in Phase 2 (T8b dependent).
    """

    prompt: str
    chosen: str    # safe, correct, grounded response
    rejected: str  # unsafe / omitted-constraint / hallucinated-evidence response

    # Lineage
    source_task_id: str
    source_family: str
    source_split: str
    generation_timestamp: str = Field(default_factory=_utcnow)
    generation_method: Literal[
        "synthetic_gold_vs_worst_case",  # Phase 1 synthetic path
        "agent_trace_pair",              # Phase 2: real AgentTrace chosen/rejected
    ] = "synthetic_gold_vs_worst_case"

    # PARTIAL IMPLEMENTATION marker (CLAUDE.md §2.2)
    # Must be non-None whenever generation_method == "synthetic_gold_vs_worst_case"
    synthetic_generation_rule: str | None = None
    partial_implementation: bool = True
    license: str = "PILOT — NOT EXPERT-REVIEWED"

    @model_validator(mode="after")
    def _require_rule_for_synthetic(self) -> "DPOPair":
        if self.generation_method == "synthetic_gold_vs_worst_case" and not self.synthetic_generation_rule:
            raise ValueError(
                "synthetic_generation_rule is required when generation_method == 'synthetic_gold_vs_worst_case' "
                "(CLAUDE.md §2.2)"
            )
        return self


# ---------------------------------------------------------------------------
# Verifier
# ---------------------------------------------------------------------------

class VerifierExample(BaseModel):
    """
    One labelled example for AeroVerifier training (proposal §11.3).

    PARTIAL IMPLEMENTATION — Phase 1 uses synthetic label derivation from
    TaskCard gold fields. Real AgentTrace-based labels require T8b outputs.

    Label = "pass" if the (synthetic) trace matches gold constraints;
            "fail" if it omits or violates them;
            "needs_escalation" if escalation_required == True and decision is positive.
    """

    trace_features: dict[str, Any]   # flat feature dict extracted from AgentTrace or synthetic
    label: Literal["pass", "fail", "needs_escalation"]
    violated_constraint: str | None  # None iff label == "pass"
    severity: Literal["Low", "Medium", "High", "Critical"]
    missing_evidence_type: str | None  # e.g. "safety_constraint_omission", "hallucinated_evidence"

    # Lineage
    source_task_id: str
    source_family: str
    source_split: str
    generation_timestamp: str = Field(default_factory=_utcnow)
    generation_method: Literal[
        "synthetic_gold_derivation",  # Phase 1
        "agent_trace_annotation",     # Phase 2: rule_based_annotate on real trace
    ] = "synthetic_gold_derivation"

    synthetic_generation_rule: str | None = None
    partial_implementation: bool = True
    license: str = "PILOT — NOT EXPERT-REVIEWED"

    @model_validator(mode="after")
    def _require_rule_for_synthetic(self) -> "VerifierExample":
        if self.generation_method == "synthetic_gold_derivation" and not self.synthetic_generation_rule:
            raise ValueError(
                "synthetic_generation_rule is required when generation_method == 'synthetic_gold_derivation' "
                "(CLAUDE.md §2.2)"
            )
        return self


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------

class DatasetManifest(BaseModel):
    """
    Summary manifest written alongside each training set output.

    Provides audit trail for lineage, counts, and generation parameters
    without embedding the full JSONL content.
    """

    kind: Literal["sft", "dpo", "verifier"]
    generation_timestamp: str = Field(default_factory=_utcnow)
    output_path: str
    n_examples: int
    source_task_families: list[str]
    source_splits_included: list[str]   # must never contain "test"
    generation_method: str
    partial_implementation: bool
    partial_implementation_notes: str
    license: str = "PILOT — NOT EXPERT-REVIEWED"
    extra: dict[str, Any] = Field(default_factory=dict)
