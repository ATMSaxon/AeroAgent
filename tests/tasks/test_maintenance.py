"""
Tests for the Maintenance / MEL / Service Difficulty task family (Family 8).

Validates:
- Schema correctness for all task cards
- Dev/test split distribution (60-80% dev)
- Severity distribution (>=65% Critical+High per T15 brief)
- No test-split item appears in dev-split
- Every SYNTHETIC card has a generation_rule
- task_id uniqueness and format (MX-<TYPE>-<NNN>)
- Family and task_type correctness
- Required fields present and non-empty
- Type D cards reference mel_checker tool in prompt
- Escalation rate for Critical-severity cards (>=50%)
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
    / "maintenance"
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
    return [c for c in all_cards if c.split in ("test", "provisional_test")]


@pytest.fixture(scope="module")
def type_d_cards(all_cards: list[TaskCard]) -> list[TaskCard]:
    return [c for c in all_cards if c.task_type == "D"]


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
    assert 70 <= n <= 115, (
        f"Expected 70-115 task cards total (per T15 brief), got {n}"
    )


def test_family_is_maintenance(all_cards: list[TaskCard]) -> None:
    for card in all_cards:
        assert card.family == "maintenance", (
            f"task_id={card.task_id} has family={card.family!r}, expected 'maintenance'"
        )


def test_task_ids_unique(all_cards: list[TaskCard]) -> None:
    ids = [c.task_id for c in all_cards]
    dupes = {tid for tid in ids if ids.count(tid) > 1}
    assert not dupes, f"Duplicate task_ids found: {dupes}"


def test_task_id_format(all_cards: list[TaskCard]) -> None:
    pattern = re.compile(r"^MX-[ABCD]-\d{3}$")
    for card in all_cards:
        assert pattern.match(card.task_id), (
            f"task_id {card.task_id!r} does not match expected format MX-<TYPE>-<NNN>"
        )


# ---------------------------------------------------------------------------
# Type counts per T15 brief
# ---------------------------------------------------------------------------


def test_type_counts_within_spec(all_cards: list[TaskCard]) -> None:
    by_type: dict[str, int] = {}
    for card in all_cards:
        by_type[card.task_type] = by_type.get(card.task_type, 0) + 1

    # Per T15 brief:
    # Type A: 30-40, Type B: 20-25, Type C: 12-15, Type D: 12-15
    assert 30 <= by_type.get("A", 0) <= 40, (
        f"Type A count {by_type.get('A', 0)} outside 30-40"
    )
    assert 20 <= by_type.get("B", 0) <= 25, (
        f"Type B count {by_type.get('B', 0)} outside 20-25"
    )
    assert 12 <= by_type.get("C", 0) <= 15, (
        f"Type C count {by_type.get('C', 0)} outside 12-15"
    )
    assert 12 <= by_type.get("D", 0) <= 15, (
        f"Type D count {by_type.get('D', 0)} outside 12-15"
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
# Severity distribution (T15 brief: >=65% Critical+High)
# ---------------------------------------------------------------------------


def test_severity_distribution_critical_high(all_cards: list[TaskCard]) -> None:
    critical_high = sum(
        1 for c in all_cards if c.severity in ("Critical", "High")
    )
    pct = critical_high / len(all_cards)
    assert pct >= 0.65, (
        f"Only {pct:.1%} of cards are Critical/High severity; "
        f"T15 brief requires >=65%"
    )


def test_all_severity_levels_present(all_cards: list[TaskCard]) -> None:
    levels = {c.severity for c in all_cards}
    assert "Critical" in levels, "No Critical severity cards found"
    assert "High" in levels, "No High severity cards found"


# ---------------------------------------------------------------------------
# Split distribution (60-80% dev / 20-40% test)
# ---------------------------------------------------------------------------


def test_split_field_set_on_all_cards(all_cards: list[TaskCard]) -> None:
    for card in all_cards:
        assert card.split in ("dev", "test", "provisional_test"), (
            f"task_id={card.task_id}: split={card.split!r} must be 'dev' or 'test'"
        )


def test_dev_test_split_ratio(
    dev_cards: list[TaskCard], test_cards: list[TaskCard]
) -> None:
    total = len(dev_cards) + len(test_cards)
    assert total > 0
    dev_ratio = len(dev_cards) / total
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
        assert (card.provenance.review_status or "") == "PILOT — NOT EXPERT-REVIEWED", (
            f"task_id={card.task_id}: provenance.license must be "
            f"'PILOT — NOT EXPERT-REVIEWED', got {card.provenance.license!r}"
        )


def test_synthetic_cards_have_generation_rule(all_cards: list[TaskCard]) -> None:
    for card in all_cards:
        src = card.provenance.source or ""
        if src.startswith("SYNTHETIC"):
            assert card.provenance.generation_rule, (
                f"task_id={card.task_id}: SYNTHETIC card missing generation_rule"
            )
            assert len(card.provenance.generation_rule) > 20, (
                f"task_id={card.task_id}: generation_rule is suspiciously short: "
                f"{card.provenance.generation_rule!r}"
            )


def test_synthetic_cards_have_no_access_date(all_cards: list[TaskCard]) -> None:
    for card in all_cards:
        src = card.provenance.source or ""
        if src.startswith("SYNTHETIC"):
            assert card.provenance.access_date is None, (
                f"task_id={card.task_id}: SYNTHETIC card should have access_date=None"
            )


REAL_SOURCE_PREFIXES = ("NTSB accident report", "CAROL case")
# F8 SYNTHETIC B/C/D cards must explain why no real-data anchor is used.
# Acceptable explanations: (1) the original MEL proprietary justification
# from T27; (2) the 2026-05-18 audit reclassification from NTSB-orphan to
# pure synthetic (cards that originally cited unverifiable NTSB IDs and
# were rewritten to remove the false-real claim).
SYNTHETIC_PROVENANCE_NOTE = (
    "real MEL is operator-specific and proprietary"  # substring match
)

MANIFEST_NTSB_IDS = {
    "ERA24FA013",
    "WPR24FA056",
    "ERA24FA078",
    "WPR24FA054",
}

MANIFEST_CAROL_IDS = {
    "DCA26WA168",
    "DCA26WA147",
    "DCA26LA184",
    "WPR26FA141",
    "DCA26WA169",
    "ERA26LA137",
    "ERA26FA179",
}


def test_real_cards_cite_verified_source(all_cards: list[TaskCard]) -> None:
    """Every REAL-tagged card (non-SYNTHETIC source) must cite a manifest-verified
    NTSB report_id or CAROL record_id."""
    for card in all_cards:
        src = card.provenance.source or ""
        if not src.startswith("SYNTHETIC"):
            # Must be a real-data card — verify it cites a known manifest entry
            is_ntsb = any(ntsb_id in src for ntsb_id in MANIFEST_NTSB_IDS)
            is_carol = any(carol_id in src for carol_id in MANIFEST_CAROL_IDS)
            assert is_ntsb or is_carol, (
                f"task_id={card.task_id}: non-SYNTHETIC card source does not cite a "
                f"manifest-verified NTSB or CAROL ID.\n"
                f"Source: {src!r}\n"
                f"Expected one of NTSB IDs: {MANIFEST_NTSB_IDS}\n"
                f"or CAROL IDs: {MANIFEST_CAROL_IDS}"
            )


def test_real_anchored_cards_have_access_date(all_cards: list[TaskCard]) -> None:
    """Every real-anchored card (provenance_class real or hybrid, with non-
    SYNTHETIC source) must have an access_date. Round-4: most B/C/D cards
    are hybrid; access_date applies to the real anchor portion."""
    for card in all_cards:
        if card.provenance_class not in ("real", "hybrid"):
            continue
        src = card.provenance.source or ""
        if src.upper().startswith("SYNTHETIC"):
            continue
        assert card.provenance.access_date is not None, (
            f"task_id={card.task_id}: real-anchored card missing access_date"
        )


def test_synthetic_cards_have_proprietary_note(all_cards: list[TaskCard]) -> None:
    """Type B/C/D SYNTHETIC cards must include the MEL proprietary provenance note
    explaining why real MEL data is not available. Type A cards predating T27 are exempt."""
    for card in all_cards:
        if card.task_type == "A":
            continue  # Type A remains fully SYNTHETIC per original T15 brief
        src = card.provenance.source or ""
        if src.startswith("SYNTHETIC"):
            assert SYNTHETIC_PROVENANCE_NOTE in src, (
                f"task_id={card.task_id}: SYNTHETIC Type B/C/D card source must include the "
                f"proprietary MEL provenance note.\n"
                f"Got: {src!r}\n"
                f"Expected to contain: {SYNTHETIC_PROVENANCE_NOTE!r}"
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
# Type D — agentic task specific checks
# ---------------------------------------------------------------------------


def test_type_d_cards_reference_mel_checker(type_d_cards: list[TaskCard]) -> None:
    assert len(type_d_cards) > 0, "No Type D cards found"
    for card in type_d_cards:
        assert "mel_checker" in card.prompt, (
            f"task_id={card.task_id}: Type D card prompt must reference mel_checker tool"
        )


def test_type_d_gold_decisions_acknowledge_mock_result(
    type_d_cards: list[TaskCard],
) -> None:
    for card in type_d_cards:
        gold = card.gold_decision.lower()
        assert "mock" in gold or "unknown" in gold, (
            f"task_id={card.task_id}: Type D gold_decision should acknowledge "
            f"mel_checker MOCK/UNKNOWN result; got: {card.gold_decision[:100]!r}"
        )


def test_type_d_evidence_requires_tool_call(type_d_cards: list[TaskCard]) -> None:
    for card in type_d_cards:
        evidence_text = " ".join(card.evidence_requirements).lower()
        assert "mel_checker" in evidence_text or "tool call" in evidence_text, (
            f"task_id={card.task_id}: Type D evidence_requirements should reference "
            f"mel_checker tool call"
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
# MEL-specific content checks
# ---------------------------------------------------------------------------


def test_type_a_cards_have_regulatory_references(all_cards: list[TaskCard]) -> None:
    type_a = [c for c in all_cards if c.task_type == "A"]
    assert len(type_a) > 0
    for card in type_a:
        combined = card.prompt + card.gold_decision
        has_regulatory = any(
            ref in combined
            for ref in ("§", "CFR", "FAA", "ICAO", "AC ", "Order ", "MEL", "MMEL")
        )
        assert has_regulatory, (
            f"task_id={card.task_id}: Type A knowledge card should contain "
            f"regulatory references in prompt or gold_decision"
        )


def test_type_b_cards_have_dispatch_decision(all_cards: list[TaskCard]) -> None:
    type_b = [c for c in all_cards if c.task_type == "B"]
    assert len(type_b) > 0
    dispatch_keywords = {"dispatch", "ground", "unsafe", "eligible", "refused", "prohibited"}
    for card in type_b:
        gold_lower = card.gold_decision.lower()
        has_dispatch_keyword = any(kw in gold_lower for kw in dispatch_keywords)
        assert has_dispatch_keyword, (
            f"task_id={card.task_id}: Type B hazard card gold_decision should contain "
            f"a dispatch decision keyword (dispatch/ground/unsafe/refused/prohibited)"
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

    print("\n=== Maintenance / MEL / Service Difficulty Task Family Summary ===")
    print(f"Total cards: {len(all_cards)}")
    print(f"By type:     {dict(sorted(by_type.items()))}")
    print(f"By severity: {dict(sorted(by_severity.items()))}")
    print(f"By split:    {dict(sorted(by_split.items()))}")
    print(
        f"Escalation required: {escalation_count} "
        f"({escalation_count / len(all_cards):.1%})"
    )
    critical_high = sum(1 for c in all_cards if c.severity in ("Critical", "High"))
    print(
        f"Critical+High: {critical_high} ({critical_high / len(all_cards):.1%})"
    )
    type_d = [c for c in all_cards if c.task_type == "D"]
    print(f"Type D (agentic) cards: {len(type_d)}")
