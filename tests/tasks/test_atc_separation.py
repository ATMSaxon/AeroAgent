"""
Tests for the ATC Separation and Conflict Detection pilot task family.

Validates:
- Schema correctness for all task cards
- Dev/test split distribution (70/30)
- Severity distribution (>=65% Critical+High)
- No test-split item appears in dev-split
- Every SYNTHETIC card has a generation_rule
- task_id uniqueness
- Family and task_type correctness
- Required fields present and non-empty
- Failure mode labels are known values
- Critical severity escalation rate
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
    / "atc_separation"
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
# Basic schema and coverage tests
# ---------------------------------------------------------------------------


def test_all_files_exist() -> None:
    for task_type, path in TASK_FILES.items():
        assert path.exists(), f"Expected task file for type {task_type}: {path}"


def test_all_cards_parse(all_cards: list[TaskCard]) -> None:
    assert len(all_cards) > 0, "No task cards loaded"


def test_total_card_count(all_cards: list[TaskCard]) -> None:
    n = len(all_cards)
    assert 65 <= n <= 90, (
        f"Expected 65-90 task cards total (per T18 brief 70-80 target), got {n}"
    )


def test_family_is_atc_separation(all_cards: list[TaskCard]) -> None:
    for card in all_cards:
        assert card.family == "atc_separation", (
            f"task_id={card.task_id} has family={card.family!r}, expected 'atc_separation'"
        )


def test_task_ids_unique(all_cards: list[TaskCard]) -> None:
    ids = [c.task_id for c in all_cards]
    dupes = {tid for tid in ids if ids.count(tid) > 1}
    assert not dupes, f"Duplicate task_ids found: {dupes}"


def test_task_id_format(all_cards: list[TaskCard]) -> None:
    import re
    pattern = re.compile(r"^AS-[ABCD]-\d{3}$")
    for card in all_cards:
        assert pattern.match(card.task_id), (
            f"task_id {card.task_id!r} does not match expected format AS-<TYPE>-<NNN>"
        )


def test_type_counts_within_spec(all_cards: list[TaskCard]) -> None:
    by_type: dict[str, int] = {}
    for card in all_cards:
        by_type[card.task_type] = by_type.get(card.task_type, 0) + 1

    # Per T18 brief:
    # Type A: 25-35, Type B: 18-22, Type C: 12-15, Type D: 10-15
    assert 25 <= by_type.get("A", 0) <= 35, (
        f"Type A count {by_type.get('A', 0)} outside 25-35"
    )
    assert 18 <= by_type.get("B", 0) <= 22, (
        f"Type B count {by_type.get('B', 0)} outside 18-22"
    )
    assert 12 <= by_type.get("C", 0) <= 15, (
        f"Type C count {by_type.get('C', 0)} outside 12-15"
    )
    assert 10 <= by_type.get("D", 0) <= 15, (
        f"Type D count {by_type.get('D', 0)} outside 10-15"
    )


# ---------------------------------------------------------------------------
# Required fields non-empty
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
    assert pct >= 0.65, (
        f"Only {pct:.1%} of cards are Critical/High severity; expected >=65% per T18 brief"
    )


def test_all_severity_levels_present(all_cards: list[TaskCard]) -> None:
    levels = {c.severity for c in all_cards}
    assert "Critical" in levels, "No Critical severity cards found"
    assert "High" in levels, "No High severity cards found"


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
    # Allow 60-80% dev to accommodate rounding on sets of this size
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


def test_real_adsb_cards_have_access_date(all_cards: list[TaskCard]) -> None:
    """Real ADS-B cards must have an access_date; SYNTHETIC cards must not."""
    for card in all_cards:
        if card.provenance.source != "SYNTHETIC":
            assert card.provenance.access_date is not None, (
                f"task_id={card.task_id}: non-SYNTHETIC card missing access_date"
            )


def test_bcd_real_adsb_share(all_cards: list[TaskCard]) -> None:
    """At least 60% of Type B, C, D cards must cite a real ADS-B Exchange file + timestamp."""
    bcd_cards = [c for c in all_cards if c.task_type in ("B", "C", "D")]
    assert bcd_cards, "No B/C/D cards found"
    real_count = sum(
        1 for c in bcd_cards
        if c.provenance.source != "SYNTHETIC"
        and "acas_" in c.provenance.source or "operations_" in c.provenance.source
        or "ADS-B Exchange" in c.provenance.source
    )
    real_pct = real_count / len(bcd_cards)
    assert real_pct >= 0.60, (
        f"Only {real_pct:.1%} of B/C/D cards cite real ADS-B Exchange data; "
        f"expected >=60% (got {real_count}/{len(bcd_cards)})"
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


# ---------------------------------------------------------------------------
# Type D tool-use verification
# ---------------------------------------------------------------------------


def test_type_d_references_separation_calculator(all_cards: list[TaskCard]) -> None:
    """Every Type D card must reference separation_calculator in evidence_requirements."""
    type_d_cards = [c for c in all_cards if c.task_type == "D"]
    assert type_d_cards, "No Type D cards found"
    for card in type_d_cards:
        has_ref = any(
            "separation_calculator" in req for req in card.evidence_requirements
        )
        assert has_ref, (
            f"task_id={card.task_id}: Type D card must reference 'separation_calculator' "
            f"in evidence_requirements (per T18 brief: Type D must use this tool)"
        )


def test_type_d_generation_rules_mention_tool_inputs(all_cards: list[TaskCard]) -> None:
    """Type D generation_rules should describe specific tool call arguments."""
    type_d_cards = [c for c in all_cards if c.task_type == "D"]
    for card in type_d_cards:
        rule = card.provenance.generation_rule or ""
        has_tool_args = (
            "separation_calculator" in rule
            or "lat" in rule.lower()
            or "lon" in rule.lower()
        )
        assert has_tool_args, (
            f"task_id={card.task_id}: Type D generation_rule should include "
            f"tool call argument details (lat/lon coordinates for separation_calculator)"
        )


# ---------------------------------------------------------------------------
# Type B trajectory data validation
# ---------------------------------------------------------------------------


def test_type_b_mentions_trajectory_generation(all_cards: list[TaskCard]) -> None:
    """Every Type B card's generation_rule must mention trajectory generation method."""
    type_b_cards = [c for c in all_cards if c.task_type == "B"]
    assert type_b_cards, "No Type B cards found"
    for card in type_b_cards:
        rule = card.provenance.generation_rule or ""
        has_trajectory = (
            "straight-line" in rule.lower()
            or "constant-altitude" in rule.lower()
            or "trajectory" in rule.lower()
        )
        assert has_trajectory, (
            f"task_id={card.task_id}: Type B generation_rule must describe "
            f"trajectory generation method (e.g., 'straight-line constant-altitude tracks')"
        )


# ---------------------------------------------------------------------------
# Summary report (printed, not asserted)
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

    print("\n=== ATC Separation and Conflict Detection Task Family Summary ===")
    print(f"Total cards: {len(all_cards)}")
    print(f"By type:     {dict(sorted(by_type.items()))}")
    print(f"By severity: {dict(sorted(by_severity.items()))}")
    print(f"By split:    {dict(sorted(by_split.items()))}")
    print(f"Escalation required: {escalation_count} ({escalation_count/len(all_cards):.1%})")
    critical_high = sum(1 for c in all_cards if c.severity in ("Critical", "High"))
    print(f"Critical+High: {critical_high} ({critical_high/len(all_cards):.1%})")
