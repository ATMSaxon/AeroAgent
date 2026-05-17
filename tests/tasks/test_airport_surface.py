"""
Tests for the Airport Surface Operations pilot task family.

Validates:
- Schema correctness for all task cards
- Dev/test split distribution (70/30)
- Severity distribution (>=60% Critical+High)
- No test-split item appears in dev-split
- Every SYNTHETIC card has a generation_rule
- task_id uniqueness and format
- Family and task_type correctness
- Required fields present and non-empty
- Type D cards are surface conflict / hold-short / runway crossing decision scenarios
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from aerosafety.io import TaskCard

TASKS_DIR = (
    Path(__file__).parent.parent.parent
    / "aerosafety"
    / "tasks"
    / "airport_surface"
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
    assert 70 <= n <= 90, (
        f"Expected 70-90 task cards total (per T17 brief), got {n}"
    )


def test_family_is_airport_surface(all_cards: list[TaskCard]) -> None:
    for card in all_cards:
        assert card.family == "airport_surface", (
            f"task_id={card.task_id} has family={card.family!r}, "
            f"expected 'airport_surface'"
        )


def test_task_ids_unique(all_cards: list[TaskCard]) -> None:
    ids = [c.task_id for c in all_cards]
    dupes = {tid for tid in ids if ids.count(tid) > 1}
    assert not dupes, f"Duplicate task_ids found: {dupes}"


def test_task_id_format(all_cards: list[TaskCard]) -> None:
    pattern = re.compile(r"^AS-[ABCD]-\d{3}$")
    for card in all_cards:
        assert pattern.match(card.task_id), (
            f"task_id {card.task_id!r} does not match expected format AS-<TYPE>-<NNN>"
        )


def test_type_counts_within_spec(all_cards: list[TaskCard]) -> None:
    by_type: dict[str, int] = {}
    for card in all_cards:
        by_type[card.task_type] = by_type.get(card.task_type, 0) + 1

    # Per T17 brief:
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
# Severity distribution (>=60% Critical+High per T17 brief)
# ---------------------------------------------------------------------------


def test_severity_distribution_critical_high(all_cards: list[TaskCard]) -> None:
    critical_high = sum(
        1 for c in all_cards if c.severity in ("Critical", "High")
    )
    pct = critical_high / len(all_cards)
    assert pct >= 0.60, (
        f"Only {pct:.1%} of cards are Critical/High severity; expected >=60%"
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
    # Allow 60-80% dev to accommodate rounding on small sets
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


def test_all_cards_are_synthetic(all_cards: list[TaskCard]) -> None:
    # All Family 5 pilot cards are SYNTHETIC (no real airport diagrams accessed)
    for card in all_cards:
        assert card.provenance.source == "SYNTHETIC", (
            f"task_id={card.task_id}: Family 5 pilot cards must all be SYNTHETIC; "
            f"got source={card.provenance.source!r}"
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
# Type D specific: surface conflict / hold-short / runway crossing
# ---------------------------------------------------------------------------


def test_type_d_cards_mention_surface_conflict_keywords(
    all_cards: list[TaskCard],
) -> None:
    """Type D cards must be surface conflict / hold-short / runway crossing scenarios."""
    surface_keywords = {
        "hold short", "hold-short", "runway crossing", "line up and wait",
        "luaw", "conflict", "incursion", "crossing", "runway occupancy",
        "taxiway", "stop bar",
    }
    type_d_cards = [c for c in all_cards if c.task_type == "D"]
    for card in type_d_cards:
        prompt_lower = card.prompt.lower()
        gold_lower = card.gold_decision.lower()
        combined = prompt_lower + " " + gold_lower
        has_keyword = any(kw in combined for kw in surface_keywords)
        assert has_keyword, (
            f"task_id={card.task_id} (Type D): prompt/gold_decision does not mention "
            f"surface conflict keywords. Expected surface conflict / hold-short / "
            f"runway crossing decision content."
        )


def test_type_d_cards_reference_tools(all_cards: list[TaskCard]) -> None:
    """Type D cards must reference at least one surface ops tool in prompt or gold."""
    surface_tools = {
        "airport_graph", "route_conflict_checker", "runway_occupancy_calculator",
        "spatial_intersection_checker",
    }
    type_d_cards = [c for c in all_cards if c.task_type == "D"]
    for card in type_d_cards:
        combined = (card.prompt + " " + card.gold_decision).lower()
        has_tool = any(tool in combined for tool in surface_tools)
        assert has_tool, (
            f"task_id={card.task_id} (Type D): prompt/gold_decision does not reference "
            f"any required surface operations tool. Expected at least one of: "
            f"{sorted(surface_tools)}"
        )


# ---------------------------------------------------------------------------
# Escalation sanity checks
# ---------------------------------------------------------------------------


def test_critical_severity_escalation_rate(all_cards: list[TaskCard]) -> None:
    critical_cards = [c for c in all_cards if c.severity == "Critical"]
    if not critical_cards:
        pytest.skip("No Critical cards to check")
    escalation_rate = sum(
        1 for c in critical_cards if c.escalation_required
    ) / len(critical_cards)
    assert escalation_rate >= 0.50, (
        f"Only {escalation_rate:.1%} of Critical cards have escalation_required=True; "
        f"expected >=50%"
    )


# ---------------------------------------------------------------------------
# Evidence requirements reference authoritative sources
# ---------------------------------------------------------------------------


def test_evidence_requirements_cite_authoritative_sources(
    all_cards: list[TaskCard],
) -> None:
    """
    At least one evidence requirement per card must cite an FAA or ICAO source.
    Individual evidence items may reference scenario data (e.g. 'Airport graph
    provided in prompt') — that is acceptable as a supplementary item.
    """
    authoritative_prefixes = (
        "faa", "icao", "14 cfr", "49 cfr", "ac 91-73", "ac 150", "ac 120",
        "order 7110", "order 7050", "doc 4444", "aim §",
    )
    for card in all_cards:
        has_any_authority = any(
            any(p in ev.lower() for p in authoritative_prefixes)
            for ev in card.evidence_requirements
        )
        assert has_any_authority, (
            f"task_id={card.task_id}: no evidence_requirement cites an authoritative "
            f"FAA/ICAO source. Evidence list: {card.evidence_requirements}"
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

    print("\n=== Airport Surface Operations Task Family Summary ===")
    print(f"Total cards: {len(all_cards)}")
    print(f"By type:     {dict(sorted(by_type.items()))}")
    print(f"By severity: {dict(sorted(by_severity.items()))}")
    print(f"By split:    {dict(sorted(by_split.items()))}")
    print(
        f"Escalation required: {escalation_count} "
        f"({escalation_count / len(all_cards):.1%})"
    )
    critical_high = sum(1 for c in all_cards if c.severity in ("Critical", "High"))
    print(f"Critical+High: {critical_high} ({critical_high / len(all_cards):.1%})")
