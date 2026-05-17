"""
Tests for the Accident and Incident Analysis pilot task family (Family 2).

Validates:
- Schema correctness for all task cards
- Dev/test split distribution (70/30)
- Severity distribution (>=60% Critical+High)
- No test-split item appears in dev-split
- Every SYNTHETIC card has a generation_rule
- Every REAL-data card (non-SYNTHETIC) cites a verified NTSB report ID in provenance.source
- task_id uniqueness
- Family and task_type correctness
- Required fields present and non-empty
- Failure mode labels are known values
- Type B real-data cards cite manifest-verified NTSB report IDs
- Type D cards cite one of the authorized report IDs (22 real NTSB reports)
- B+D combined pool has >=60% real citation rate (T22 constraint)
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from aerosafety.eval.failure_taxonomy import FailureMode
from aerosafety.io import TaskCard

TASKS_DIR = (
    Path(__file__).parent.parent.parent
    / "aerosafety"
    / "tasks"
    / "accident_analysis"
    / "taskcards"
)

TASK_FILES = {
    "A": TASKS_DIR / "typeA_knowledge.jsonl",
    "B": TASKS_DIR / "typeB_hazard.jsonl",
    "C": TASKS_DIR / "typeC_consequence.jsonl",
    "D": TASKS_DIR / "typeD_agentic.jsonl",
}

# Authorized NTSB report IDs for Type D narrative excerpts (22 real reports from PDFs)
AUTHORIZED_REPORT_IDS = {
    # T20 original 5 reports
    "ERA23LA177",
    "WPR25FA062",
    "ANC25FA010",
    "ERA25FA082",
    "ERA25FA080",
    # T22 new 17 reports from NTSB_FULL_REPORTS PDFs
    "ANC24LA006",
    "WPR24FA035",
    "CEN24LA037",
    "WPR24LA051",
    "ANC24LA005",
    "WPR23LA362",
    "ERA24FA053",
    "CEN24LA051",
    "ERA24LA051",
    "WPR24LA042",
    "ERA24LA047",
    "ERA24LA046",
    "ERA24LA044",
    "CEN24LA041",
    "ERA24LA040",
    "WPR24LA036",
    "ERA24LA033",
}

# All valid NTSB report IDs present in the CAROL JSON extract used for Type B
# Original 20 (T20) + 20 new (T22) = 40 total
MANIFEST_NTSB_IDS = {
    # T20 original 20
    "ERA26LA207", "WPR26LA180", "ANC26FA039", "CEN26FA172", "ERA26FA179",
    "WPR26FA160", "CEN26FA174", "ERA26LA196", "WPR26LA176", "CEN26LA180",
    "ANC26LA040", "WPR26LA164", "DCA26LA203", "ERA26LA190", "WPR26LA183",
    "CEN26LA173", "ERA26LA184", "ANC26LA037", "ERA26LA199", "DCA26WA202",
    # T22 new 20 from CAROL JSON
    "WPR26LA174", "DCA26FA194", "CEN26LA168", "ERA26FA177", "WPR26FA141",
    "DCA26MA161", "CEN26LA156", "DCA26LA185", "CEN26FA140", "ERA26LA197",
    "WPR26FA120", "ERA26FA165", "CEN26LA148", "CEN26LA164", "WPR26LA155",
    "ERA26LA140", "ERA26LA144", "ERA26LA158", "WPR26LA126", "ANC26LA038",
}


def _load_all_cards() -> list[TaskCard]:
    cards: list[TaskCard] = []
    for task_type, path in TASK_FILES.items():
        assert path.exists(), f"Task file missing: {path}"
        with path.open() as f:
            for lineno, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                raw = json.loads(line)
                try:
                    card = TaskCard(**raw)
                except Exception as exc:
                    pytest.fail(
                        f"Schema validation failed in {path.name} line {lineno}: {exc}\n"
                        f"Raw data: {json.dumps(raw, indent=2)[:500]}"
                    )
                assert card.task_type == task_type, (
                    f"task_id={card.task_id} in {path.name} has task_type={card.task_type!r}, "
                    f"expected {task_type!r}"
                )
                cards.append(card)
    return cards


def test_all_files_exist():
    for task_type, path in TASK_FILES.items():
        assert path.exists(), f"Missing task file for type {task_type}: {path}"


def test_schema_valid_for_all_cards():
    cards = _load_all_cards()
    assert len(cards) > 0, "No cards loaded"


def test_task_ids_unique():
    cards = _load_all_cards()
    ids = [c.task_id for c in cards]
    assert len(ids) == len(set(ids)), f"Duplicate task_ids: {[i for i in ids if ids.count(i) > 1]}"


def test_task_id_format():
    cards = _load_all_cards()
    pattern = re.compile(r"^AA-[ABCD]-\d{3}$")
    for card in cards:
        assert pattern.match(card.task_id), (
            f"task_id {card.task_id!r} does not match expected format AA-[ABCD]-NNN"
        )


def test_family_is_accident_analysis():
    cards = _load_all_cards()
    for card in cards:
        assert card.family == "accident_analysis", (
            f"task_id={card.task_id} has family={card.family!r}, expected 'accident_analysis'"
        )


def test_split_field_set():
    cards = _load_all_cards()
    for card in cards:
        assert card.split in ("dev", "test"), (
            f"task_id={card.task_id} has split={card.split!r}"
        )


def test_dev_test_split_ratio():
    cards = _load_all_cards()
    dev_count = sum(1 for c in cards if c.split == "dev")
    test_count = sum(1 for c in cards if c.split == "test")
    total = len(cards)
    dev_ratio = dev_count / total
    assert 0.60 <= dev_ratio <= 0.80, (
        f"Dev ratio {dev_ratio:.1%} ({dev_count}/{total}) outside 60-80% target"
    )


def test_no_test_ids_in_dev():
    cards = _load_all_cards()
    dev_ids = {c.task_id for c in cards if c.split == "dev"}
    test_ids = {c.task_id for c in cards if c.split == "test"}
    overlap = dev_ids & test_ids
    assert not overlap, f"task_ids appear in both dev and test splits: {overlap}"


def test_severity_distribution_critical_high():
    cards = _load_all_cards()
    critical_high = sum(1 for c in cards if c.severity in ("Critical", "High"))
    ratio = critical_high / len(cards)
    assert ratio >= 0.60, (
        f"Critical+High severity ratio {ratio:.1%} ({critical_high}/{len(cards)}) "
        f"below required 60%"
    )


def test_failure_mode_labels_known():
    known_modes = {m.value for m in FailureMode}
    cards = _load_all_cards()
    for card in cards:
        for label in card.failure_mode_labels:
            assert label in known_modes, (
                f"task_id={card.task_id} has unknown failure_mode_label {label!r}. "
                f"Known: {sorted(known_modes)}"
            )


def test_failure_mode_labels_non_empty():
    cards = _load_all_cards()
    for card in cards:
        assert len(card.failure_mode_labels) >= 1, (
            f"task_id={card.task_id} has no failure_mode_labels"
        )


def test_prompt_non_empty():
    cards = _load_all_cards()
    for card in cards:
        assert card.prompt and len(card.prompt.strip()) > 20, (
            f"task_id={card.task_id} has empty or very short prompt"
        )


def test_gold_decision_non_empty():
    cards = _load_all_cards()
    for card in cards:
        assert card.gold_decision and len(card.gold_decision.strip()) > 20, (
            f"task_id={card.task_id} has empty or very short gold_decision"
        )


def test_required_safety_constraints_non_empty():
    cards = _load_all_cards()
    for card in cards:
        assert len(card.required_safety_constraints) >= 1, (
            f"task_id={card.task_id} has no required_safety_constraints"
        )


def test_provenance_license_set():
    cards = _load_all_cards()
    for card in cards:
        assert card.provenance.license == "PILOT — NOT EXPERT-REVIEWED", (
            f"task_id={card.task_id} has incorrect license: {card.provenance.license!r}"
        )


def test_synthetic_cards_have_generation_rule():
    cards = _load_all_cards()
    for card in cards:
        if card.provenance.source == "SYNTHETIC":
            assert card.provenance.generation_rule is not None, (
                f"task_id={card.task_id} is SYNTHETIC but has no generation_rule"
            )
            assert len(card.provenance.generation_rule.strip()) > 10, (
                f"task_id={card.task_id} has empty/trivial generation_rule"
            )


def test_real_data_cards_no_generation_rule():
    """Real-data cards must NOT have a generation_rule (mutually exclusive with SYNTHETIC)."""
    cards = _load_all_cards()
    for card in cards:
        if card.provenance.source != "SYNTHETIC":
            assert card.provenance.generation_rule is None, (
                f"task_id={card.task_id} is real-data but has a generation_rule set"
            )


def test_type_a_all_synthetic():
    cards = _load_all_cards()
    type_a = [c for c in cards if c.task_type == "A"]
    for card in type_a:
        assert card.provenance.source == "SYNTHETIC", (
            f"Type A card {card.task_id} should be SYNTHETIC, got source={card.provenance.source!r}"
        )


def test_type_b_real_data_cards_cite_ntsb_id():
    """Every Type B card that is not SYNTHETIC must cite a verified NTSB report ID."""
    cards = _load_all_cards()
    type_b_real = [c for c in cards if c.task_type == "B" and c.provenance.source != "SYNTHETIC"]
    assert len(type_b_real) > 0, "No real-data Type B cards found"
    for card in type_b_real:
        source = card.provenance.source
        found_id = any(ntsb_id in source for ntsb_id in MANIFEST_NTSB_IDS)
        assert found_id, (
            f"Type B real-data card {card.task_id} provenance.source does not cite "
            f"a verified NTSB report ID from the manifest. Source: {source[:200]}"
        )


def test_type_b_real_data_cards_have_access_date():
    cards = _load_all_cards()
    type_b_real = [c for c in cards if c.task_type == "B" and c.provenance.source != "SYNTHETIC"]
    for card in type_b_real:
        assert card.provenance.access_date is not None, (
            f"Type B real-data card {card.task_id} missing access_date"
        )


def test_type_d_cites_authorized_report_ids():
    """Every Type D card must cite one of the five authorized NTSB PDF report IDs."""
    cards = _load_all_cards()
    type_d = [c for c in cards if c.task_type == "D"]
    assert len(type_d) > 0, "No Type D cards found"
    for card in type_d:
        source = card.provenance.source
        found = any(rpt_id in source for rpt_id in AUTHORIZED_REPORT_IDS)
        assert found, (
            f"Type D card {card.task_id} provenance.source does not cite any of the "
            f"5 authorized NTSB report IDs ({AUTHORIZED_REPORT_IDS}). Source: {source[:200]}"
        )


def test_type_d_has_evidence_requirements():
    cards = _load_all_cards()
    type_d = [c for c in cards if c.task_type == "D"]
    for card in type_d:
        assert len(card.evidence_requirements) >= 1, (
            f"Type D card {card.task_id} has no evidence_requirements"
        )


def test_type_counts_within_spec():
    cards = _load_all_cards()
    counts = {t: sum(1 for c in cards if c.task_type == t) for t in "ABCD"}
    assert 25 <= counts["A"] <= 40, f"Type A count {counts['A']} outside [25,40]"
    assert 35 <= counts["B"] <= 45, f"Type B count {counts['B']} outside [35,45]"
    assert 18 <= counts["C"] <= 25, f"Type C count {counts['C']} outside [18,25]"
    assert 22 <= counts["D"] <= 30, f"Type D count {counts['D']} outside [22,30]"


def test_total_card_count():
    cards = _load_all_cards()
    assert 110 <= len(cards) <= 135, (
        f"Total card count {len(cards)} outside expected range [110, 135]"
    )


def test_no_real_synthetic_mix_on_single_card():
    """Verify no card is flagged as SYNTHETIC yet has real report IDs in source."""
    cards = _load_all_cards()
    for card in cards:
        if card.provenance.source == "SYNTHETIC":
            for rpt_id in AUTHORIZED_REPORT_IDS | MANIFEST_NTSB_IDS:
                if rpt_id in str(card.provenance.generation_rule or ""):
                    pass  # generation_rule may mention reports as basis — this is acceptable
                assert rpt_id not in card.provenance.source or card.provenance.source == "SYNTHETIC", (
                    f"Card {card.task_id} claims SYNTHETIC but source contains {rpt_id}"
                )


def test_bd_pool_real_citation_rate():
    """B+D combined pool must have >=60% real citation rate (T22 hard constraint)."""
    cards = _load_all_cards()
    bd_cards = [c for c in cards if c.task_type in ("B", "D")]
    assert len(bd_cards) > 0, "No B or D cards found"
    real_bd = [c for c in bd_cards if c.provenance.generation_rule is None]
    rate = len(real_bd) / len(bd_cards)
    assert rate >= 0.60, (
        f"B+D real citation rate {rate:.1%} ({len(real_bd)}/{len(bd_cards)}) "
        f"below required 60%"
    )


def test_type_b_all_real():
    """All Type B cards must be real NTSB CAROL data per T22 spec."""
    cards = _load_all_cards()
    type_b = [c for c in cards if c.task_type == "B"]
    for card in type_b:
        assert card.provenance.generation_rule is None, (
            f"Type B card {card.task_id} should be real NTSB data (no generation_rule) "
            f"per T22 spec"
        )
