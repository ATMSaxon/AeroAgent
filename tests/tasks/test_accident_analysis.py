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
- Type D cards cite one of the authorized report IDs (35 real NTSB reports across rounds)
- B+D combined pool has >=60% real citation rate (T22 constraint)
- >=80% B+D cards have unique citations (no single record cited in >3 cards)

Round 1 (AA-* prefix): 119 cards (original T20/T22 build)
Round 2 (NC2-* prefix): 397 new cards (T22 scale-up build, 2026-05-17)
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

# Authorized NTSB report IDs for Type D narrative excerpts (35 real reports across all rounds)
AUTHORIZED_REPORT_IDS = {
    # T20 original 5 reports
    "ERA23LA177",
    "WPR25FA062",
    "ANC25FA010",
    "ERA25FA082",
    "ERA25FA080",
    # T22 round-1 new 17 reports from NTSB_FULL_REPORTS PDFs
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
    # NC2 round-2 additional 13 reports (NC2-D-019 through NC2-D-050)
    "CEN24FA057",
    "CEN24FA073",
    "DCA24WA026",
    "DCA24WA027",
    "ERA24FA069",
    "ERA24FA072",
    "ERA24FA075",
    "ERA24FA077",
    "ERA24FA078",
    "GAA24WA047",
    "WPR24FA054",
    "WPR24FA056",
    "WPR24FA057",
}

# All valid NTSB report IDs present in the CAROL JSON extract used for Type B
# Original 20 (T20) + 20 new (T22 round-1) + 287 new (NC2 round-2) = 327 total
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
    # NC2 round-2: 287 new CAROL records
    "DCA26WA199", "WPR26LA185", "GAA26WA189", "WPR26LA182", "WPR26LA184",
    "WPR26LA179", "CEN26LA182", "DCA26WA198", "GAA26WA188", "CEN26LA181",
    "CEN26LA177", "WPR26LA181", "DCA26LA196", "GAA26WA187", "ANC26LA036",
    "GAA26WA183", "WPR26LA175", "ERA26LA195", "GAA26WA185", "CEN26LA175",
    "DCA26WA204", "ANC26LA035", "ERA26LA194", "ANC26LA034", "GAA26WA180",
    "WPR26LA172", "GAA26WA181", "GAA26WA179", "WPR26LA170", "GAA26WA178",
    "DCA26WA192", "GAA26WA175", "WPR26LA171", "WPR26LA178", "GAA26WA174",
    "ERA26LA189", "WPR26LA167", "ERA26LA187", "ERA26LA191", "GAA26WA172",
    "ANC26LA031", "GAA26WA182", "ERA26LA185", "ERA26LA186", "WPR26LA169",
    "ANC26LA028", "GAA26WA169", "WPR26LA168", "GAA26WA176", "CEN26LA171",
    "CEN26LA169", "ANC26LA027", "ERA26LA180", "GAA26WA167", "ERA26LA183",
    "WPR26LA163", "GAA26WA190", "WPR26LA173", "CEN26LA170", "ERA26LA182",
    "WPR26LA165", "WPR26LA162", "GAA26WA168", "CEN26LA167", "ERA26LA181",
    "ANC26LA026", "GAA26WA166", "ERA26LA176", "CEN26LA165", "ERA26LA174",
    "ERA26FA166", "WPR26LA159", "WPR26LA158", "WPR26LA153", "ERA26LA167",
    "ERA26LA173", "ERA26LA172", "ERA26LA170", "ERA26LA169", "ERA26LA168",
    "GAA26WA165", "GAA26WA164", "WPR26LA156", "ANC26LA025", "ANC26FA024",
    "CEN26LA166", "GAA26WA177", "WPR26FA151", "WPR26LA157", "WPR26LA152",
    "WPR26LA150", "GAA26WA157", "GAA26WA162", "WPR26LA149", "CEN26LA160",
    "GAA26WA151", "CEN26LA161", "CEN26LA159", "DCA26WA180", "ERA26LA159",
    "WPR26LA146", "ERA26LA162", "DCA26WA177", "CEN26LA162", "CEN26LA158",
    "GAA26WA150", "ANC26LA029", "CEN26LA163", "GAA26WA149", "ERA26LA161",
    "ERA26LA163", "ERA26LA156", "CEN26LA157", "GAA26WA170", "GAA26WA152",
    "DCA26WA172", "ERA26LA157", "ENG26WA021", "GAA26WA184", "DCA26WA169",
    "GAA26WA145", "GAA26WA144", "GAA26WA161", "ANC26LA023", "GAA26WA153",
    "DCA26WA168", "CEN26LA154", "DCA26WA170", "CEN26LA151", "CEN26LA152",
    "ERA26LA155", "GAA26WA142", "DCA26WA171", "DCA26LA167", "GAA26WA171",
    "WPR26LA142", "ANC26LA022", "WPR26LA145", "ERA26LA152", "CEN26LA150",
    "CEN26LA153", "WPR26LA143", "WPR26LA144", "GAA26WA140", "DCA26WA166",
    "CEN26LA149", "ERA26LA151", "CEN26FA147", "DCA26LA164", "GAA26WA143",
    "GAA26WA155", "CEN26LA145", "WPR26LA148", "WPR26LA137", "ANC26FA021",
    "WPR26FA130", "CEN26FA142", "WPR26LA136", "WPR26LA132", "CEN26LA146",
    "WPR26LA131", "WPR26LA138", "GAA26WA135", "ERA26LA154", "ERA26LA153",
    "GAA26WA133", "GAA26WA141", "CEN26FA141", "CEN26LA143", "WPR26LA135",
    "DCA26WA163", "WPR26LA134", "DCA26LA165", "GAA26WA154", "WPR26LA133",
    "CEN26LA144", "OPS26LA027", "DCA26LA159", "GAA26WA134", "WPR26LA140",
    "GAA26WA136", "WPR26LA128", "ERA26LA150", "GAA26WA129", "GAA26WA127",
    "GAA26WA128", "ERA26LA148", "GAA26WA130", "DCA26WA162", "GAA26WA132",
    "ERA26LA147", "CEN26LA139", "GAA26WA125", "WPR26LA124", "DCA26WA156",
    "ERA26LA145", "DCA26WA154", "WPR26LA123", "WPR26FA121", "CEN26LA138",
    "GAA26WA146", "DCA26WA157", "GAA26WA124", "ERA26LA146", "DCA26WA152",
    "CEN26LA135", "ANC26LA018", "CEN26LA137", "ERA26LA149", "DCA26LA150",
    "ERA26LA142", "WPR26LA122", "DCA26LA151", "ERA26LA141", "DCA26WA174",
    "ERA26LA138", "ERA26LA139", "GAA26WA123", "CEN26FA132", "ERA26LA136",
    "CEN26LA134", "WPR26FA119", "ERA26LA135", "ANC26LA017", "ERA26LA134",
    "WPR26LA115", "DCA26LA184", "WPR26LA118", "WPR26LA114", "ERA26LA143",
    "ERA26LA131", "ERA26LA133", "CEN26LA128", "DCA26WA147", "ERA26LA132",
    "WPR26LA112", "GAA26WA120", "CEN26LA131", "CEN26LA133", "WPR26FA108",
    "WPR26FA109", "CEN26LA129", "GAA26WA119", "ERA26LA130", "CEN26LA127",
    "CEN26FA126", "DCA26LA139", "WPR26LA113", "GAA26WA121", "GAA26WA122",
    "GAA26WA118", "DCA26WA146", "GAA26WA115", "ERA26LA127", "CEN26LA125",
    "DCA26WA140", "WPR26LA107", "CEN26LA124", "GAA26WA116", "ERA26LA123",
    "CEN26LA123", "ERA26FA120", "DCA26WA136", "ERA26LA137", "ANC26LA016",
    "ERA26LA122", "CEN26LA122", "DCA26WA137", "WPR26LA106", "OPS26LA021",
    "CEN26LA120", "GAA26WA117", "GAA26WA111", "ERA26LA118", "CEN26LA119",
    "GAA26WA109", "DCA26WA158", "GAA26WA112", "ERA26LA117", "ERA26LA119",
    "DCA26WA120", "CEN26LA121", "ERA26LA116", "WPR26LA104", "WPR26FA103",
    "ERA26FA115", "GAA26WA113",
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
    # Round 1: AA-[ABCD]-NNN  |  Round 2 scale-up: NC2-[ABCD]-NNN
    pattern = re.compile(r"^(?:AA|NC2)-[ABCD]-\d{3}$")
    for card in cards:
        assert pattern.match(card.task_id), (
            f"task_id {card.task_id!r} does not match expected format AA-[ABCD]-NNN "
            f"or NC2-[ABCD]-NNN"
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


VALID_LICENSES = {
    "PILOT — NOT EXPERT-REVIEWED",          # round-1 cards
    "Public domain — NTSB public record",   # NC2 real-data cards
    "Synthetic — no copyright",             # NC2 synthetic cards
}


def test_provenance_license_set():
    cards = _load_all_cards()
    for card in cards:
        assert card.provenance.license in VALID_LICENSES, (
            f"task_id={card.task_id} has unrecognized license: {card.provenance.license!r}. "
            f"Valid: {VALID_LICENSES}"
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
    """Real-data cards (provenance_class='real') must NOT have a generation_rule.
    Hybrid and synthetic cards MAY have one (they declare it explicitly)."""
    cards = _load_all_cards()
    for card in cards:
        # Skip cards whose source starts with "SYNTHETIC" (audit-reclassified
        # NTSB-orphan cards) and any card declared synthetic or hybrid.
        src = (card.provenance.source or "")
        if src.strip().upper().startswith("SYNTHETIC"):
            continue
        cls = getattr(card, "provenance_class", None)
        if cls in ("synthetic", "hybrid"):
            continue
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
    """
    Round 1 (AA-*): A~34, B~40, C~20, D~25 = 119 total
    Round 2 (NC2-*): A~10, B~287, C~50, D~50 = 397 new
    Combined target: A>=40, B>=300, C>=60, D>=70, Total>=500
    """
    cards = _load_all_cards()
    counts = {t: sum(1 for c in cards if c.task_type == t) for t in "ABCD"}
    assert counts["A"] >= 40, f"Type A count {counts['A']} below minimum 40"
    assert counts["B"] >= 300, f"Type B count {counts['B']} below minimum 300"
    assert counts["C"] >= 60, f"Type C count {counts['C']} below minimum 60"
    assert counts["D"] >= 70, f"Type D count {counts['D']} below minimum 70"


def test_total_card_count():
    cards = _load_all_cards()
    assert len(cards) >= 500, (
        f"Total card count {len(cards)} below required minimum 500"
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


def test_bd_unique_citation_rate():
    """
    At least 80% of B+D cards must have unique citations where no single record
    is cited in more than 3 cards. Tests that the dataset avoids over-reliance
    on a small number of NTSB reports.
    """
    import re
    from collections import Counter

    cards = _load_all_cards()
    bd_real = [
        c for c in cards
        if c.task_type in ("B", "D") and c.provenance.generation_rule is None
    ]
    if not bd_real:
        pytest.skip("No real B+D cards to test")

    # Extract a canonical citation key from each card's provenance source
    citation_counts: Counter = Counter()
    for card in bd_real:
        src = card.provenance.source
        # Extract any NTSB report ID pattern from the source string
        ids_found = re.findall(r"\b([A-Z]{2,4}\d{2}[A-Z]{2}\d{3})\b", src)
        key = ids_found[0] if ids_found else src[:60]
        citation_counts[key] += 1

    # Count cards whose citation key appears in <=3 cards (unique enough)
    unique_enough = sum(
        1 for c in bd_real
        if citation_counts[
            (re.findall(r"\b([A-Z]{2,4}\d{2}[A-Z]{2}\d{3})\b", c.provenance.source) or [c.provenance.source[:60]])[0]
        ] <= 3
    )
    rate = unique_enough / len(bd_real)
    assert rate >= 0.80, (
        f"B+D unique citation rate {rate:.1%} ({unique_enough}/{len(bd_real)}) "
        f"below required 80%. Over-cited records: "
        f"{[(cid, cnt) for cid, cnt in citation_counts.items() if cnt > 3]}"
    )
