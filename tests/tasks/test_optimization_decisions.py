"""
Tests for the Optimization-Integrated Aviation Decisions task family (Family 9).

Validates:
- Schema correctness for all task cards
- Dev/test split distribution (70/30)
- Severity distribution (>=55% Critical+High per task brief)
- No test-split item appears in dev-split
- Every SYNTHETIC card has a generation_rule
- task_id uniqueness and format
- Family and task_type correctness
- Required fields present and non-empty
- Failure mode labels are valid FailureMode values
- Critical card escalation rate
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aerosafety.io import TaskCard

TASKS_DIR = (
    Path(__file__).parent.parent.parent
    / "aerosafety"
    / "tasks"
    / "optimization_decisions"
    / "taskcards"
)

TASK_FILES = {
    "A": TASKS_DIR / "typeA_knowledge.jsonl",
    "B": TASKS_DIR / "typeB_hazard.jsonl",
    "C": TASKS_DIR / "typeC_consequence.jsonl",
    "D": TASKS_DIR / "typeD_agentic.jsonl",
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


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def all_cards() -> list[TaskCard]:
    return _load_all_cards()


@pytest.fixture(scope="module")
def dev_cards(all_cards: list[TaskCard]) -> list[TaskCard]:
    return [c for c in all_cards if c.split == "dev"]


@pytest.fixture(scope="module")
def test_cards(all_cards: list[TaskCard]) -> list[TaskCard]:
    return [c for c in all_cards if c.split == "test"]


# ---------------------------------------------------------------------------
# Basic schema and file existence
# ---------------------------------------------------------------------------


def test_all_files_exist() -> None:
    for task_type, path in TASK_FILES.items():
        assert path.exists(), f"Expected task file for type {task_type}: {path}"


def test_all_cards_parse(all_cards: list[TaskCard]) -> None:
    assert len(all_cards) > 0, "No task cards loaded"


def test_total_card_count(all_cards: list[TaskCard]) -> None:
    n = len(all_cards)
    # Scaled to 250+ cards (OPT2-* expansion); original brief was ~60-70
    assert 250 <= n, (
        f"Expected >=250 task cards total (OPT2 scale target), got {n}"
    )


def test_family_is_optimization_decisions(all_cards: list[TaskCard]) -> None:
    for card in all_cards:
        assert card.family == "optimization_decisions", (
            f"task_id={card.task_id} has family={card.family!r}, "
            f"expected 'optimization_decisions'"
        )


def test_task_ids_unique(all_cards: list[TaskCard]) -> None:
    ids = [c.task_id for c in all_cards]
    dupes = {tid for tid in ids if ids.count(tid) > 1}
    assert not dupes, f"Duplicate task_ids found: {dupes}"


def test_task_id_format(all_cards: list[TaskCard]) -> None:
    import re
    # Original OD-* cards + OPT2-* scaled cards
    pattern = re.compile(r"^(OD|OPT2)-[ABCD]-\d{3}$")
    for card in all_cards:
        assert pattern.match(card.task_id), (
            f"task_id {card.task_id!r} does not match expected format OD-<TYPE>-<NNN> or OPT2-<TYPE>-<NNN>"
        )


# ---------------------------------------------------------------------------
# Type distribution
# ---------------------------------------------------------------------------


def test_type_counts_within_spec(all_cards: list[TaskCard]) -> None:
    by_type: dict[str, int] = {}
    for card in all_cards:
        by_type[card.task_type] = by_type.get(card.task_type, 0) + 1

    # OPT2 scale targets: A ~35, B ~117, C ~60, D ~38
    assert 30 <= by_type.get("A", 0), (
        f"Type A count {by_type.get('A',0)} below 30 (OPT2 scale target)"
    )
    assert 100 <= by_type.get("B", 0), (
        f"Type B count {by_type.get('B',0)} below 100 (OPT2 scale target)"
    )
    assert 50 <= by_type.get("C", 0), (
        f"Type C count {by_type.get('C',0)} below 50 (OPT2 scale target)"
    )
    assert 30 <= by_type.get("D", 0), (
        f"Type D count {by_type.get('D',0)} below 30 (OPT2 scale target)"
    )


# ---------------------------------------------------------------------------
# Required fields
# ---------------------------------------------------------------------------


def test_required_fields_non_empty(all_cards: list[TaskCard]) -> None:
    for card in all_cards:
        assert card.prompt.strip(), f"task_id={card.task_id}: prompt is empty"
        assert card.gold_decision.strip(), (
            f"task_id={card.task_id}: gold_decision is empty"
        )
        assert len(card.required_safety_constraints) >= 1, (
            f"task_id={card.task_id}: required_safety_constraints is empty"
        )
        assert len(card.evidence_requirements) >= 1, (
            f"task_id={card.task_id}: evidence_requirements is empty"
        )
        assert card.failure_mode_labels, (
            f"task_id={card.task_id}: failure_mode_labels is empty"
        )


# ---------------------------------------------------------------------------
# Severity distribution
# ---------------------------------------------------------------------------


def test_severity_distribution_critical_high(all_cards: list[TaskCard]) -> None:
    critical_high = sum(
        1 for c in all_cards if c.severity in ("Critical", "High")
    )
    pct = critical_high / len(all_cards)
    # Per T19 brief: >=55% Critical+High
    assert pct >= 0.55, (
        f"Only {pct:.1%} of cards are Critical/High severity; expected >=55%"
    )


def test_all_severity_levels_present(all_cards: list[TaskCard]) -> None:
    levels = {c.severity for c in all_cards}
    assert "Critical" in levels, "No Critical severity cards found"
    assert "High" in levels, "No High severity cards found"
    assert "Medium" in levels, "No Medium severity cards found"


# ---------------------------------------------------------------------------
# Split distribution (70/30 dev/test)
# ---------------------------------------------------------------------------


def test_split_field_set_on_all_cards(all_cards: list[TaskCard]) -> None:
    for card in all_cards:
        assert card.split in ("dev", "test"), (
            f"task_id={card.task_id}: split={card.split!r} must be 'dev' or 'test'"
        )


def test_dev_test_split_ratio(
    dev_cards: list[TaskCard], test_cards: list[TaskCard]
) -> None:
    total = len(dev_cards) + len(test_cards)
    assert total > 0
    dev_ratio = len(dev_cards) / total
    # Allow 60-80% dev to accommodate rounding
    assert 0.60 <= dev_ratio <= 0.80, (
        f"Dev ratio {dev_ratio:.1%} outside 60-80% expected range "
        f"(dev={len(dev_cards)}, test={len(test_cards)})"
    )


def test_no_test_id_in_dev(
    dev_cards: list[TaskCard], test_cards: list[TaskCard]
) -> None:
    dev_ids = {c.task_id for c in dev_cards}
    test_ids = {c.task_id for c in test_cards}
    overlap = dev_ids & test_ids
    assert not overlap, (
        f"task_ids appear in both dev and test splits: {overlap}"
    )


# ---------------------------------------------------------------------------
# Provenance and synthetic labeling
# ---------------------------------------------------------------------------


def test_every_card_has_provenance_license(all_cards: list[TaskCard]) -> None:
    for card in all_cards:
        assert card.provenance.license == "PILOT — NOT EXPERT-REVIEWED", (
            f"task_id={card.task_id}: provenance.license must be "
            f"'PILOT — NOT EXPERT-REVIEWED', got {card.provenance.license!r}"
        )


def test_synthetic_cards_have_generation_rule(all_cards: list[TaskCard]) -> None:
    for card in all_cards:
        if card.provenance.source == "SYNTHETIC":
            assert card.provenance.generation_rule, (
                f"task_id={card.task_id}: SYNTHETIC card missing generation_rule"
            )
            assert len(card.provenance.generation_rule) > 20, (
                f"task_id={card.task_id}: generation_rule is suspiciously short: "
                f"{card.provenance.generation_rule!r}"
            )


def test_synthetic_cards_have_no_access_date(all_cards: list[TaskCard]) -> None:
    for card in all_cards:
        if card.provenance.source == "SYNTHETIC":
            assert card.provenance.access_date is None, (
                f"task_id={card.task_id}: SYNTHETIC card should have access_date=None"
            )


def test_type_a_cards_are_synthetic(all_cards: list[TaskCard]) -> None:
    for card in all_cards:
        if card.task_type == "A":
            assert card.provenance.source == "SYNTHETIC", (
                f"task_id={card.task_id}: Type A knowledge cards must be SYNTHETIC; "
                f"got source={card.provenance.source!r}"
            )


def test_real_bd_cards_cite_or_library(all_cards: list[TaskCard]) -> None:
    bd_cards = [c for c in all_cards if c.task_type in ("B", "D")]
    beasley_doi = "10.2307/2582903"
    or_lib_keyword = "OR_LIBRARY"

    def has_citation(card: TaskCard) -> bool:
        src = card.provenance.source or ""
        return beasley_doi in src and or_lib_keyword in src

    citing = sum(1 for c in bd_cards if has_citation(c))
    pct = citing / len(bd_cards)
    assert pct >= 0.60, (
        f"Only {pct:.1%} of B+D cards cite OR-Library + Beasley DOI; expected >=60%"
    )


def test_real_c_cards_cite_bts(all_cards: list[TaskCard]) -> None:
    c_cards = [c for c in all_cards if c.task_type == "C"]
    bts_keyword = "BTS_ONTIME"
    citing = sum(1 for c in c_cards if bts_keyword in (c.provenance.source or ""))
    pct = citing / len(c_cards)
    assert pct >= 0.80, (
        f"Only {pct:.1%} of C cards cite BTS data; expected >=80%"
    )


# ---------------------------------------------------------------------------
# Failure mode label validation
# ---------------------------------------------------------------------------


def test_failure_mode_labels_are_known_values(all_cards: list[TaskCard]) -> None:
    from aerosafety.eval.failure_taxonomy import FailureMode

    valid_modes = {m.value for m in FailureMode}
    for card in all_cards:
        for label in card.failure_mode_labels:
            assert label in valid_modes, (
                f"task_id={card.task_id}: failure_mode_label {label!r} "
                f"is not a known FailureMode value"
            )


# ---------------------------------------------------------------------------
# Escalation sanity checks
# ---------------------------------------------------------------------------


def test_critical_severity_escalation_rate(all_cards: list[TaskCard]) -> None:
    critical_cards = [c for c in all_cards if c.severity == "Critical"]
    if not critical_cards:
        pytest.skip("No Critical cards to check")
    escalation_rate = sum(1 for c in critical_cards if c.escalation_required) / len(
        critical_cards
    )
    assert escalation_rate >= 0.50, (
        f"Only {escalation_rate:.1%} of Critical cards have escalation_required=True; "
        f"expected >=50%"
    )


def test_type_d_cards_reference_tool(all_cards: list[TaskCard]) -> None:
    """Type D cards should reference the optimization_solver tool in prompt or evidence."""
    type_d_cards = [c for c in all_cards if c.task_type == "D"]
    for card in type_d_cards:
        has_tool_ref = (
            "optimization_solver" in card.prompt.lower()
            or any("optimization_solver" in e.lower() for e in card.evidence_requirements)
            or any("solver" in e.lower() for e in card.evidence_requirements)
            or "solver" in card.prompt.lower()
        )
        assert has_tool_ref, (
            f"task_id={card.task_id}: Type D card should reference optimization_solver "
            f"tool in prompt or evidence_requirements"
        )


def test_type_d_cards_include_tool_use_failure_modes(all_cards: list[TaskCard]) -> None:
    """Type D agentic cards should include tool-use related failure modes."""
    type_d_cards = [c for c in all_cards if c.task_type == "D"]
    tool_use_modes = {
        "missing_required_tool_call",
        "wrong_tool_selected",
        "wrong_tool_input",
        "correct_output_misinterpreted",
        "tool_output_overtrusted",
    }
    for card in type_d_cards:
        has_tool_mode = any(label in tool_use_modes for label in card.failure_mode_labels)
        assert has_tool_mode, (
            f"task_id={card.task_id}: Type D card should include at least one tool-use "
            f"failure mode label; got {card.failure_mode_labels}"
        )


# ---------------------------------------------------------------------------
# Optimization-specific content checks
# ---------------------------------------------------------------------------


def test_type_a_cards_reference_separation_or_optimization(all_cards: list[TaskCard]) -> None:
    """Type A cards should reference optimization or separation concepts."""
    type_a_cards = [c for c in all_cards if c.task_type == "A"]
    optimization_keywords = {
        "separation", "sequence", "wake", "gate", "gdp", "delay", "slot",
        "constraint", "feasib", "optim", "assign", "capacity",
    }
    for card in type_a_cards:
        text = (card.prompt + card.gold_decision).lower()
        has_keyword = any(kw in text for kw in optimization_keywords)
        assert has_keyword, (
            f"task_id={card.task_id}: Type A card prompt/gold_decision does not contain "
            f"any optimization-relevant keyword"
        )


def test_wake_separation_evidence_in_sequencing_cards(all_cards: list[TaskCard]) -> None:
    """Cards about wake separation should cite ICAO Doc 4444 or AC 90-23G."""
    wake_cards = [
        c for c in all_cards
        if any("separation" in (e.lower() or "") for e in c.evidence_requirements)
        or any("wake" in (e.lower() or "") for e in c.evidence_requirements)
    ]
    if not wake_cards:
        return  # no wake cards — skip (shouldn't happen but don't fail)
    for card in wake_cards:
        ev_text = " ".join(card.evidence_requirements).lower()
        has_icao = "icao" in ev_text or "4444" in ev_text or "ac 90-23" in ev_text
        assert has_icao, (
            f"task_id={card.task_id}: wake/separation card should cite ICAO Doc 4444 "
            f"or FAA AC 90-23G in evidence_requirements"
        )


# ---------------------------------------------------------------------------
# OPT2 scale coverage tests
# ---------------------------------------------------------------------------


def test_csp_instance_diversity(all_cards: list[TaskCard]) -> None:
    """Every OR-Library CSP instance file (csp{N}.txt) must be cited in at least one B or D card."""
    CSP_FILES = [
        "csp1.txt", "csp2.txt", "csp3.txt", "csp4.txt", "csp6.txt",
        "csp7.txt", "csp8.txt", "csp9.txt", "csp11.txt", "csp12.txt",
        "csp13.txt", "csp14.txt", "csp16.txt", "csp17.txt", "csp18.txt",
        "csp19.txt", "csp21.txt", "csp22.txt", "csp23.txt", "csp24.txt",
    ]
    bd_cards = [c for c in all_cards if c.task_type in ("B", "D")]
    for csp_file in CSP_FILES:
        cited = any(csp_file in (c.provenance.source or "") for c in bd_cards)
        assert cited, (
            f"OR-Library instance {csp_file} is not cited in any B or D card. "
            f"Every CSP instance must be covered (hard rule from OPT2 task brief)."
        )


def test_bts_month_diversity(all_cards: list[TaskCard]) -> None:
    """Every downloaded BTS ZIP must be cited in at least one C card."""
    BTS_ZIPS = [
        "BTS_OnTime_2024_07.zip",
        "BTS_OnTime_2024_08.zip",
        "BTS_OnTime_2024_09.zip",
        "BTS_OnTime_2024_10.zip",
        "BTS_OnTime_2024_11.zip",
        "BTS_OnTime_2024_12.zip",
    ]
    c_cards = [c for c in all_cards if c.task_type == "C"]
    for zip_name in BTS_ZIPS:
        cited = any(zip_name in (c.provenance.source or "") for c in c_cards)
        assert cited, (
            f"BTS ZIP {zip_name} is not cited in any C card. "
            f"Every BTS month file must be covered (hard rule from OPT2 task brief)."
        )


# ---------------------------------------------------------------------------
# Summary report
# ---------------------------------------------------------------------------


def test_print_summary(all_cards: list[TaskCard]) -> None:
    by_type: dict[str, int] = {}
    by_severity: dict[str, int] = {}
    by_split: dict[str, int] = {}
    escalation_count = 0

    for card in all_cards:
        by_type[card.task_type] = by_type.get(card.task_type, 0) + 1
        by_severity[card.severity] = by_severity.get(card.severity, 0) + 1
        by_split[card.split or "unset"] = by_split.get(card.split or "unset", 0) + 1
        if card.escalation_required:
            escalation_count += 1

    print("\n=== Optimization Decisions Task Family Summary ===")
    print(f"Total cards: {len(all_cards)}")
    print(f"By type:     {dict(sorted(by_type.items()))}")
    print(f"By severity: {dict(sorted(by_severity.items()))}")
    print(f"By split:    {dict(sorted(by_split.items()))}")
    print(
        f"Escalation required: {escalation_count} "
        f"({escalation_count/len(all_cards):.1%})"
    )
    critical_high = sum(1 for c in all_cards if c.severity in ("Critical", "High"))
    print(f"Critical+High: {critical_high} ({critical_high/len(all_cards):.1%})")
