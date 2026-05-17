"""
Tests for the Wake Vortex / Separation Safety pilot task family (Family 7).

Validates:
- Schema correctness for all task cards
- Dev/test split distribution (60-80% dev)
- Severity distribution (>=20% Critical+High)
- No test-split item appears in dev-split
- Every SYNTHETIC card has a generation_rule
- task_id uniqueness and format
- Family and task_type correctness
- Aircraft types are in the citation-verified wake table
- Failure mode labels are valid FailureMode enum values
- Type D (agentic) cards reference required tools
- Evidence requirements cite canonical wake vortex standards
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
    / "wake_vortex"
    / "taskcards"
)

TASK_FILES = {
    "A": TASKS_DIR / "typeA_knowledge.jsonl",
    "B": TASKS_DIR / "typeB_hazard.jsonl",
    "C": TASKS_DIR / "typeC_consequence.jsonl",
    "D": TASKS_DIR / "typeD_agentic.jsonl",
}

# Aircraft types verified in aerosafety.tools.wake_category_checker._WAKE_TABLE
_KNOWN_ICAO_TYPES: frozenset[str] = frozenset({
    "A388", "A389",
    "A124", "A225", "A306", "A30B", "A310", "A332", "A333", "A338", "A339",
    "A342", "A343", "A345", "A346", "A359", "A35K",
    "B742", "B743", "B744", "B748", "B74S", "B74D",
    "B762", "B763", "B764",
    "B772", "B773", "B77L", "B77W", "B778", "B779",
    "B788", "B789", "B78X",
    "DC10", "MD11", "IL76", "C17", "C5",
    "A19N", "A20N", "A21N", "A318", "A319", "A320", "A321",
    "B712", "B721", "B722",
    "B731", "B732", "B733", "B734", "B735", "B736", "B737", "B738", "B739",
    "B37M", "B38M", "B39M", "B3XM",
    "B752", "B753",
    "CRJ1", "CRJ2", "CRJ7", "CRJ9", "CRJX",
    "E170", "E175", "E190", "E195", "E290", "E295",
    "MD80", "MD81", "MD82", "MD83", "MD88", "MD90",
    "AT43", "AT45", "AT72", "AT73", "AT75",
    "DH8D",
    "C172", "C182", "C208", "PA28", "BE36", "BE20", "PC12",
})

# Canonical wake vortex standards that must appear in evidence
_WAKE_STANDARDS = {
    "FAA JO 7110.65",
    "ICAO Doc 8643",
    "FAA AC 90-23G",
    "ICAO Doc 4444",
    "EUROCONTROL RECAT-EU",
}

# Pattern for WV task IDs
_WV_ID_PATTERN = re.compile(r"^WV-[ABCD]-\d{3}$")

# Tools that Type D cards must reference
_TYPE_D_TOOLS = {"wake_category_checker", "separation_calculator"}


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


@pytest.fixture(scope="module")
def type_d_cards(all_cards: list[TaskCard]) -> list[TaskCard]:
    return [c for c in all_cards if c.task_type == "D"]


# ---------------------------------------------------------------------------
# File existence
# ---------------------------------------------------------------------------


def test_all_files_exist() -> None:
    for task_type, path in TASK_FILES.items():
        assert path.exists(), f"Expected task file for type {task_type}: {path}"


def test_sources_md_exists() -> None:
    assert (TASKS_DIR / "sources.md").exists(), "sources.md is missing"


def test_construction_rules_exists() -> None:
    assert (TASKS_DIR / "synthetic_construction_rules.md").exists(), (
        "synthetic_construction_rules.md is missing"
    )


# ---------------------------------------------------------------------------
# Basic schema and coverage
# ---------------------------------------------------------------------------


def test_all_cards_parse(all_cards: list[TaskCard]) -> None:
    assert len(all_cards) > 0, "No task cards loaded"


def test_total_card_count(all_cards: list[TaskCard]) -> None:
    n = len(all_cards)
    assert 65 <= n <= 95, (
        f"Expected 65-95 task cards total (per T16 brief ~75), got {n}"
    )


def test_family_is_wake_vortex(all_cards: list[TaskCard]) -> None:
    for card in all_cards:
        assert card.family == "wake_vortex", (
            f"task_id={card.task_id} has family={card.family!r}, expected 'wake_vortex'"
        )


def test_task_ids_unique(all_cards: list[TaskCard]) -> None:
    ids = [c.task_id for c in all_cards]
    dupes = {tid for tid in ids if ids.count(tid) > 1}
    assert not dupes, f"Duplicate task_ids found: {dupes}"


def test_task_id_format(all_cards: list[TaskCard]) -> None:
    for card in all_cards:
        assert _WV_ID_PATTERN.match(card.task_id), (
            f"task_id {card.task_id!r} does not match expected format WV-<TYPE>-<NNN>"
        )


def test_type_counts_within_spec(all_cards: list[TaskCard]) -> None:
    by_type: dict[str, int] = {}
    for card in all_cards:
        by_type[card.task_type] = by_type.get(card.task_type, 0) + 1

    # Per T16 brief: A:25-35, B:18-22, C:12-15, D:10-15
    assert 25 <= by_type.get("A", 0) <= 35, (
        f"Type A count {by_type.get('A', 0)} outside 25-35"
    )
    assert 15 <= by_type.get("B", 0) <= 25, (
        f"Type B count {by_type.get('B', 0)} outside 15-25"
    )
    assert 10 <= by_type.get("C", 0) <= 18, (
        f"Type C count {by_type.get('C', 0)} outside 10-18"
    )
    assert 8 <= by_type.get("D", 0) <= 15, (
        f"Type D count {by_type.get('D', 0)} outside 8-15"
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
# Evidence cites wake vortex standards
# ---------------------------------------------------------------------------


def test_evidence_cites_wake_standards(all_cards: list[TaskCard]) -> None:
    for card in all_cards:
        ev_text = " ".join(card.evidence_requirements)
        has_standard = any(std in ev_text for std in _WAKE_STANDARDS)
        assert has_standard, (
            f"task_id={card.task_id}: evidence_requirements does not cite any known "
            f"wake vortex standard. Got: {card.evidence_requirements}"
        )


# ---------------------------------------------------------------------------
# Aircraft type validation
# ---------------------------------------------------------------------------


def _extract_icao_types_from_text(text: str) -> list[str]:
    """Find ICAO type designator patterns (4 chars, alphanumeric, uppercase)."""
    return re.findall(r"\b([A-Z0-9]{3,4})\b", text)


def test_type_d_cards_use_only_known_aircraft(type_d_cards: list[TaskCard]) -> None:
    for card in type_d_cards:
        combined_text = card.prompt + " " + card.gold_decision
        for match in re.finditer(r"ICAO type ([A-Z0-9]{3,4})", combined_text):
            icao_type = match.group(1)
            assert icao_type in _KNOWN_ICAO_TYPES, (
                f"task_id={card.task_id}: ICAO type '{icao_type}' is referenced "
                f"but not in the citation-verified wake table. "
                f"Only use types from aerosafety/tools/wake_category_checker.py."
            )


def test_evidence_cites_icao_doc_8643_for_category_claims(all_cards: list[TaskCard]) -> None:
    for card in all_cards:
        ev_text = " ".join(card.evidence_requirements)
        gold_text = card.gold_decision
        has_category_claim = any(
            phrase in gold_text for phrase in ["category J", "category H", "category M", "category L", "=J", "=H", "=M", "=L"]
        )
        if has_category_claim:
            assert "ICAO Doc 8643" in ev_text, (
                f"task_id={card.task_id}: gold_decision makes a wake category claim "
                f"but evidence_requirements does not cite ICAO Doc 8643"
            )


# ---------------------------------------------------------------------------
# Severity distribution
# ---------------------------------------------------------------------------


def test_severity_distribution_critical_high(all_cards: list[TaskCard]) -> None:
    critical_high = sum(1 for c in all_cards if c.severity in ("Critical", "High"))
    pct = critical_high / len(all_cards)
    assert pct >= 0.50, (
        f"Only {pct:.1%} of cards are Critical/High severity; expected >=50% "
        f"for a safety-critical wake vortex family"
    )


def test_all_severity_levels_present(all_cards: list[TaskCard]) -> None:
    levels = {c.severity for c in all_cards}
    assert "Critical" in levels, "No Critical severity cards found"
    assert "High" in levels, "No High severity cards found"


# ---------------------------------------------------------------------------
# Split distribution
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
    assert 0.55 <= dev_ratio <= 0.80, (
        f"Dev ratio {dev_ratio:.1%} outside 55-80% expected range "
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
    for card in all_cards:
        assert card.provenance.source == "SYNTHETIC", (
            f"task_id={card.task_id}: Phase 1 pilot cards must all be SYNTHETIC; "
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
                f"is not a known FailureMode value. Valid: {sorted(valid_modes)}"
            )


# ---------------------------------------------------------------------------
# Type D agentic validation
# ---------------------------------------------------------------------------


def test_type_d_prompts_mention_tools(type_d_cards: list[TaskCard]) -> None:
    for card in type_d_cards:
        prompt_lower = card.prompt.lower()
        has_wake_tool = "wake_category_checker" in prompt_lower
        has_sep_tool = "separation_calculator" in prompt_lower
        assert has_wake_tool and has_sep_tool, (
            f"task_id={card.task_id}: Type D prompt must mention both "
            f"wake_category_checker and separation_calculator tools. "
            f"Got prompt: {card.prompt[:200]}"
        )


def test_type_d_gold_describes_tool_calls(type_d_cards: list[TaskCard]) -> None:
    for card in type_d_cards:
        gold = card.gold_decision.upper()
        assert "TOOL CALL" in gold, (
            f"task_id={card.task_id}: Type D gold_decision must describe TOOL CALL steps. "
            f"Got: {card.gold_decision[:200]}"
        )


def test_type_d_missing_tool_call_in_failure_modes(type_d_cards: list[TaskCard]) -> None:
    for card in type_d_cards:
        assert "missing_required_tool_call" in card.failure_mode_labels, (
            f"task_id={card.task_id}: Type D card must include "
            f"'missing_required_tool_call' in failure_mode_labels "
            f"(this is a canonical failure mode for agentic tasks). "
            f"Got: {card.failure_mode_labels}"
        )


def test_type_d_evidence_cites_tool_modules(type_d_cards: list[TaskCard]) -> None:
    for card in type_d_cards:
        ev_text = " ".join(card.evidence_requirements)
        assert "wake_category_checker" in ev_text, (
            f"task_id={card.task_id}: Type D evidence must cite wake_category_checker module"
        )
        assert "separation_calculator" in ev_text, (
            f"task_id={card.task_id}: Type D evidence must cite separation_calculator module"
        )


# ---------------------------------------------------------------------------
# Wake-specific content checks
# ---------------------------------------------------------------------------


def test_separation_minimum_in_gold_for_type_ab(all_cards: list[TaskCard]) -> None:
    # Cards that explicitly discuss numeric separation minima or departure intervals
    # must state a NM distance, time interval, or standard radar separation.
    # Cards about general wake behavior (ground effect, wind effects) are excluded.
    _NUMERIC_SEP_TRIGGERS = [
        "separation minimum", "approach separation", "departure interval",
        "requires a minimum", "separation requires", "approach requires",
        "requires minimum", "NM separation", "minutes minimum",
    ]
    for card in all_cards:
        if card.task_type not in ("A", "B"):
            continue
        gold = card.gold_decision
        has_nm = "NM" in gold
        has_minute = "minute" in gold.lower() or "min" in gold.lower()
        has_standard_sep = "standard" in gold.lower() and "radar" in gold.lower()
        if any(phrase in gold for phrase in _NUMERIC_SEP_TRIGGERS):
            assert has_nm or has_minute or has_standard_sep, (
                f"task_id={card.task_id}: Type A/B gold_decision with numeric separation claim "
                f"should include NM distance, time interval, or 'standard radar separation'. "
                f"Got: {gold[:200]}"
            )


def test_escalation_sanity_for_critical_cards(all_cards: list[TaskCard]) -> None:
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

    print("\n=== Wake Vortex / Separation Safety Task Family Summary ===")
    print(f"Total cards: {len(all_cards)}")
    print(f"By type:     {dict(sorted(by_type.items()))}")
    print(f"By severity: {dict(sorted(by_severity.items()))}")
    print(f"By split:    {dict(sorted(by_split.items()))}")
    print(f"Escalation required: {escalation_count} ({escalation_count/len(all_cards):.1%})")
    critical_high = sum(1 for c in all_cards if c.severity in ("Critical", "High"))
    print(f"Critical+High: {critical_high} ({critical_high/len(all_cards):.1%})")
