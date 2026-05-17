"""
dataset_builder.py — Convert pilot TaskCards into Phase 2 training JSONL.

Three public functions:
  build_sft_dataset        — SFT examples (instruction / input / output)
  build_dpo_preference_pairs — DPO chosen/rejected pairs (PARTIAL IMPLEMENTATION)
  build_verifier_dataset   — AeroVerifier labelled examples (PARTIAL IMPLEMENTATION)

No GPU, no API, no model loading. Pure deterministic data transforms.

PARTIAL IMPLEMENTATION notes
-----------------------------
DPO and Verifier builders use SYNTHETIC preference/label generation for Phase 1
because real AgentTrace pairs from T8b do not yet exist.  Each synthetic example
is explicitly marked with:
  - partial_implementation = True
  - synthetic_generation_rule = <documented rule string>
  - generation_method = "synthetic_gold_vs_worst_case" | "synthetic_gold_derivation"

These must be replaced with real AgentTrace-based construction in Phase 2 (T8b).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aerosafety.io import AgentTrace, TaskCard
from aerosafety.training.schemas import (
    DatasetManifest,
    DPOPair,
    SFTExample,
    VerifierExample,
)
from aerosafety.training.splits import assert_no_test_leakage, filter_train_only


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_jsonl(examples: list[Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for ex in examples:
            fh.write(ex.model_dump_json() + "\n")


def _write_manifest(manifest: DatasetManifest, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        fh.write(manifest.model_dump_json(indent=2))


# ---------------------------------------------------------------------------
# SFT
# ---------------------------------------------------------------------------

_SFT_INSTRUCTION_TEMPLATE = (
    "You are an aviation safety AI assistant. Given the following aviation scenario, "
    "provide a decision (PROCEED / NO-GO / DELAY / ESCALATE / UNCERTAIN) with a clear "
    "rationale that cites all applicable safety constraints and evidence.\n\n"
    "Safety constraints that MUST be addressed: {constraints}"
)

_SFT_OUTPUT_TEMPLATE = (
    "Decision: {decision}\n\n"
    "Rationale: {rationale}\n\n"
    "Safety constraints cited:\n{constraints_block}\n\n"
    "Evidence requirements:\n{evidence_block}"
)


def _derive_sft_rationale(card: TaskCard) -> str:
    """Build a gold rationale from card fields for SFT training target."""
    parts = [card.gold_decision]
    if card.required_safety_constraints:
        parts.append(
            "The following safety constraints apply: "
            + "; ".join(card.required_safety_constraints)
            + "."
        )
    if card.evidence_requirements:
        parts.append(
            "Supporting evidence: "
            + "; ".join(card.evidence_requirements)
            + "."
        )
    if card.escalation_required:
        parts.append(
            "This scenario requires escalation to a qualified authority "
            "before any operational decision."
        )
    return " ".join(parts)


def build_sft_dataset(
    task_cards: list[TaskCard],
    output_path: str | Path,
) -> tuple[Path, DatasetManifest]:
    """
    Convert dev-split TaskCards into SFT training JSONL.

    Each card produces one SFTExample: instruction = task prompt + constraint list;
    output = gold_decision + rationale derived from card fields.

    Test-split cards are excluded via filter_train_only + assert_no_test_leakage
    (hard error per CLAUDE.md §2.3).

    Parameters
    ----------
    task_cards:
        All TaskCards to consider.  Test-split cards are automatically excluded.
    output_path:
        Destination JSONL file (e.g. data/training_sets/2026-05-17/sft.jsonl).

    Returns
    -------
    (output_path, manifest)
    """
    output_path = Path(output_path)
    # Hard error: any test card in the input is a leakage attempt (CLAUDE.md §2.3).
    # assert_no_test_leakage runs on the RAW input so callers cannot bypass the guard
    # by relying on filter_train_only to silently drop test cards.
    assert_no_test_leakage(task_cards)
    train_cards = filter_train_only(task_cards)

    examples: list[SFTExample] = []
    families_seen: set[str] = set()

    for card in train_cards:
        constraints_str = "; ".join(card.required_safety_constraints) if card.required_safety_constraints else "none specified"
        instruction = _SFT_INSTRUCTION_TEMPLATE.format(constraints=constraints_str)

        constraints_block = "\n".join(
            f"- {c}" for c in card.required_safety_constraints
        ) or "  (none)"
        evidence_block = "\n".join(
            f"- {e}" for e in card.evidence_requirements
        ) or "  (none)"
        rationale = _derive_sft_rationale(card)

        output_text = _SFT_OUTPUT_TEMPLATE.format(
            decision=card.gold_decision,
            rationale=rationale,
            constraints_block=constraints_block,
            evidence_block=evidence_block,
        )

        examples.append(SFTExample(
            instruction=instruction,
            input=card.prompt,
            output=output_text,
            source_task_id=card.task_id,
            source_family=card.family,
            source_split=card.split or "dev",
        ))
        families_seen.add(card.family)

    _write_jsonl(examples, output_path)

    manifest = DatasetManifest(
        kind="sft",
        output_path=str(output_path),
        n_examples=len(examples),
        source_task_families=sorted(families_seen),
        source_splits_included=["dev"],
        generation_method="gold_card_expansion",
        partial_implementation=False,
        partial_implementation_notes=(
            "SFT output is derived deterministically from gold_decision + "
            "required_safety_constraints + evidence_requirements fields in each TaskCard. "
            "No LLM generation used. Output quality is bounded by card quality — "
            "expert review of gold fields is pending."
        ),
    )
    _write_manifest(manifest, output_path.with_suffix(".manifest.json"))
    return output_path, manifest


# ---------------------------------------------------------------------------
# DPO
# ---------------------------------------------------------------------------

# PARTIAL IMPLEMENTATION — synthetic_generation_rule for Phase 1 DPO pairs
_DPO_SYNTHETIC_RULE = (
    "PARTIAL IMPLEMENTATION (Phase 1 synthetic path). "
    "Chosen response = gold_decision + all required_safety_constraints cited. "
    "Rejected response = synthetic worst-case: decision contradicts gold (e.g. PROCEED "
    "when gold is NO-GO) with safety constraints omitted and a plausible-but-wrong "
    "rationale derived from card context. "
    "This synthetic pair MUST be replaced with real AgentTrace chosen/rejected pairs "
    "from T8b (real LLM execution) in Phase 2. "
    "Do NOT use these synthetic pairs to claim DPO training efficacy."
)

_DPO_CHOSEN_TEMPLATE = (
    "Decision: {gold_decision}\n\n"
    "Rationale: {rationale}\n\n"
    "Safety constraints cited:\n{constraints_block}\n\n"
    "Escalation recommended: {escalation}"
)

_DPO_REJECTED_TEMPLATE = (
    "Decision: {wrong_decision}\n\n"
    "Rationale: {wrong_rationale}\n\n"
    "Safety constraints cited: (none)\n\n"
    "Escalation recommended: False"
)

_PROCEED_COUNTERPART = {
    "NO-GO": "PROCEED",
    "DELAY": "PROCEED",
    "ESCALATE": "PROCEED",
    "UNCERTAIN": "PROCEED",
    "PROCEED": "NO-GO",  # if gold is PROCEED, reject is NO-GO
}

def _wrong_decision(gold: str) -> str:
    # Derive a plausible-but-wrong decision from gold
    upper = gold.upper()
    for key, wrong in _PROCEED_COUNTERPART.items():
        if key in upper:
            return wrong
    return "PROCEED"


def _wrong_rationale(card: TaskCard) -> str:
    return (
        f"[SYNTHETIC REJECTED — PARTIAL IMPLEMENTATION] "
        f"Based on a superficial reading of the scenario, the operation appears feasible. "
        f"No NOTAM or weather constraints were identified as blocking. "
        f"(This rationale intentionally omits: {'; '.join(card.required_safety_constraints[:2]) or 'all constraints'}. "
        f"It is the REJECTED arm of a synthetic DPO pair.)"
    )


def build_dpo_preference_pairs(
    task_cards: list[TaskCard],
    agent_traces: list[AgentTrace] | None,
    output_path: str | Path,
) -> tuple[Path, DatasetManifest]:
    """
    Build DPO preference pairs from TaskCards (Phase 1 synthetic) or AgentTraces (Phase 2).

    PARTIAL IMPLEMENTATION: When agent_traces is None (Phase 1), synthetic chosen/rejected
    pairs are derived from card gold fields.  This is explicitly labelled and must not be
    used for final training efficacy claims.

    Parameters
    ----------
    task_cards:
        TaskCards for which to construct pairs.
    agent_traces:
        Real AgentTrace objects from T8b.  If None, falls back to synthetic generation
        (PARTIAL IMPLEMENTATION).
    output_path:
        Destination JSONL file.

    Returns
    -------
    (output_path, manifest)
    """
    output_path = Path(output_path)

    if agent_traces is not None:
        raise NotImplementedError(
            "DPO construction from real AgentTraces is PARTIAL IMPLEMENTATION. "
            "Phase 2 implementation requires T8b AgentTrace outputs. "
            "Pass agent_traces=None to use the Phase 1 synthetic path."
        )

    assert_no_test_leakage(task_cards)
    train_cards = filter_train_only(task_cards)

    pairs: list[DPOPair] = []
    families_seen: set[str] = set()

    for card in train_cards:
        constraints_block = "\n".join(
            f"- {c}" for c in card.required_safety_constraints
        ) or "  (none)"
        rationale = _derive_sft_rationale(card)

        chosen = _DPO_CHOSEN_TEMPLATE.format(
            gold_decision=card.gold_decision,
            rationale=rationale,
            constraints_block=constraints_block,
            escalation=str(card.escalation_required),
        )

        wrong_dec = _wrong_decision(card.gold_decision)
        rejected = _DPO_REJECTED_TEMPLATE.format(
            wrong_decision=wrong_dec,
            wrong_rationale=_wrong_rationale(card),
        )

        pairs.append(DPOPair(
            prompt=card.prompt,
            chosen=chosen,
            rejected=rejected,
            source_task_id=card.task_id,
            source_family=card.family,
            source_split=card.split or "dev",
            generation_method="synthetic_gold_vs_worst_case",
            synthetic_generation_rule=_DPO_SYNTHETIC_RULE,
            partial_implementation=True,
        ))
        families_seen.add(card.family)

    _write_jsonl(pairs, output_path)

    manifest = DatasetManifest(
        kind="dpo",
        output_path=str(output_path),
        n_examples=len(pairs),
        source_task_families=sorted(families_seen),
        source_splits_included=["dev"],
        generation_method="synthetic_gold_vs_worst_case",
        partial_implementation=True,
        partial_implementation_notes=(
            "PARTIAL IMPLEMENTATION — Phase 1 DPO pairs are SYNTHETIC. "
            "Chosen = gold card expansion; rejected = deterministic worst-case inversion. "
            "Real AgentTrace-based pairs from T8b are required for Phase 2. "
            "Do NOT use these pairs to claim DPO alignment efficacy."
        ),
    )
    _write_manifest(manifest, output_path.with_suffix(".manifest.json"))
    return output_path, manifest


# ---------------------------------------------------------------------------
# Verifier
# ---------------------------------------------------------------------------

_VERIFIER_SYNTHETIC_RULE = (
    "PARTIAL IMPLEMENTATION (Phase 1 synthetic path). "
    "Label derived from TaskCard gold fields only — no real AgentTrace is evaluated. "
    "Positive examples (label=pass): synthetic trace features assume gold_decision cited, "
    "all required_safety_constraints present, escalation honoured. "
    "Negative examples (label=fail): synthetic trace features assume safety_constraint omission "
    "or incorrect decision. "
    "label=needs_escalation: escalation_required==True but synthetic decision is positive. "
    "Must be replaced with real annotated AgentTraces from T8b in Phase 2."
)


def _make_pass_features(card: TaskCard) -> dict[str, Any]:
    """Synthetic 'pass' trace features derived from gold fields."""
    return {
        "task_id": card.task_id,
        "predicted_decision": card.gold_decision,
        "safety_constraints_cited": card.required_safety_constraints,
        "evidence_cited": card.evidence_requirements[:2] if card.evidence_requirements else [],
        "escalation_recommended": card.escalation_required,
        "had_parse_error": False,
        "had_tool_error": False,
        "n_tool_calls": 0,
        "synthetic": True,
    }


def _make_fail_features(card: TaskCard) -> dict[str, Any]:
    """Synthetic 'fail' trace features — constraint omission, wrong decision."""
    wrong_dec = _wrong_decision(card.gold_decision)
    return {
        "task_id": card.task_id,
        "predicted_decision": wrong_dec,
        "safety_constraints_cited": [],   # omitted — the failure mode
        "evidence_cited": [],
        "escalation_recommended": False,
        "had_parse_error": False,
        "had_tool_error": False,
        "n_tool_calls": 0,
        "synthetic": True,
    }


def _make_escalation_fail_features(card: TaskCard) -> dict[str, Any]:
    """Synthetic 'needs_escalation' trace features — correct decision but escalation missed."""
    return {
        "task_id": card.task_id,
        "predicted_decision": "PROCEED",   # positive when escalation was required
        "safety_constraints_cited": card.required_safety_constraints,
        "evidence_cited": [],
        "escalation_recommended": False,   # missed escalation
        "had_parse_error": False,
        "had_tool_error": False,
        "n_tool_calls": 0,
        "synthetic": True,
    }


def build_verifier_dataset(
    task_cards: list[TaskCard],
    agent_traces: list[AgentTrace] | None,
    output_path: str | Path,
) -> tuple[Path, DatasetManifest]:
    """
    Build AeroVerifier labelled training examples.

    PARTIAL IMPLEMENTATION: When agent_traces is None (Phase 1), synthetic labels are
    derived from TaskCard gold fields. Each card generates two examples: one 'pass'
    (synthetic correct trace) and one 'fail' (synthetic constraint-omission trace).
    Cards with escalation_required=True also generate a 'needs_escalation' example.

    Parameters
    ----------
    task_cards:
        Source TaskCards.
    agent_traces:
        Real annotated AgentTrace objects (Phase 2).  Pass None for Phase 1 synthetic path.
    output_path:
        Destination JSONL file.

    Returns
    -------
    (output_path, manifest)
    """
    output_path = Path(output_path)

    if agent_traces is not None:
        raise NotImplementedError(
            "Verifier dataset construction from real AgentTraces is PARTIAL IMPLEMENTATION. "
            "Phase 2 implementation requires T8b AgentTrace + annotation outputs. "
            "Pass agent_traces=None to use the Phase 1 synthetic path."
        )

    assert_no_test_leakage(task_cards)
    train_cards = filter_train_only(task_cards)

    examples: list[VerifierExample] = []
    families_seen: set[str] = set()

    for card in train_cards:
        # Pass example
        examples.append(VerifierExample(
            trace_features=_make_pass_features(card),
            label="pass",
            violated_constraint=None,
            severity=card.severity,
            missing_evidence_type=None,
            source_task_id=card.task_id,
            source_family=card.family,
            source_split=card.split or "dev",
            generation_method="synthetic_gold_derivation",
            synthetic_generation_rule=_VERIFIER_SYNTHETIC_RULE,
            partial_implementation=True,
        ))

        # Fail example — safety constraint omission
        first_constraint = card.required_safety_constraints[0] if card.required_safety_constraints else "unspecified"
        examples.append(VerifierExample(
            trace_features=_make_fail_features(card),
            label="fail",
            violated_constraint=first_constraint,
            severity=card.severity,
            missing_evidence_type="safety_constraint_omission",
            source_task_id=card.task_id,
            source_family=card.family,
            source_split=card.split or "dev",
            generation_method="synthetic_gold_derivation",
            synthetic_generation_rule=_VERIFIER_SYNTHETIC_RULE,
            partial_implementation=True,
        ))

        # Needs escalation example (only for cards that require it)
        if card.escalation_required:
            examples.append(VerifierExample(
                trace_features=_make_escalation_fail_features(card),
                label="needs_escalation",
                violated_constraint="escalation_required",
                severity=card.severity,
                missing_evidence_type="missed_escalation",
                source_task_id=card.task_id,
                source_family=card.family,
                source_split=card.split or "dev",
                generation_method="synthetic_gold_derivation",
                synthetic_generation_rule=_VERIFIER_SYNTHETIC_RULE,
                partial_implementation=True,
            ))

        families_seen.add(card.family)

    _write_jsonl(examples, output_path)

    n_pass = sum(1 for e in examples if e.label == "pass")
    n_fail = sum(1 for e in examples if e.label == "fail")
    n_esc = sum(1 for e in examples if e.label == "needs_escalation")

    manifest = DatasetManifest(
        kind="verifier",
        output_path=str(output_path),
        n_examples=len(examples),
        source_task_families=sorted(families_seen),
        source_splits_included=["dev"],
        generation_method="synthetic_gold_derivation",
        partial_implementation=True,
        partial_implementation_notes=(
            "PARTIAL IMPLEMENTATION — Phase 1 verifier labels are SYNTHETIC. "
            "Each card generates pass + fail examples; escalation_required cards "
            "also generate needs_escalation examples. "
            "Real annotated AgentTraces from T8b required for Phase 2. "
            "Do NOT use these labels to claim AeroVerifier training efficacy."
        ),
        extra={
            "n_pass": n_pass,
            "n_fail": n_fail,
            "n_needs_escalation": n_esc,
        },
    )
    _write_manifest(manifest, output_path.with_suffix(".manifest.json"))
    return output_path, manifest
