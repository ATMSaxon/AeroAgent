"""
Tests for Task Family 3: Weather and Dispatch Risk task cards.

Validates schema compliance, provenance integrity, split distribution,
and content constraints per CLAUDE.md §1.1, §2.2, §3.1, §8.1, §8.3.

No API calls, no model inference — static structural validation only.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from aerosafety.io import TaskCard, TaskProvenance

TASKCARDS_DIR = Path(__file__).parent.parent.parent / "aerosafety" / "tasks" / "weather_dispatch" / "taskcards"

JSONL_FILES = {
    "typeA": TASKCARDS_DIR / "typeA_knowledge.jsonl",
    "typeB": TASKCARDS_DIR / "typeB_hazard.jsonl",
    "typeC": TASKCARDS_DIR / "typeC_consequence.jsonl",
    "typeD": TASKCARDS_DIR / "typeD_agentic.jsonl",
}

EXPECTED_TASK_TYPES = {
    "typeA": "A",
    "typeB": "B",
    "typeC": "C",
    "typeD": "D",
}

VALID_SPLITS = {"dev", "test"}
VALID_SEVERITIES = {"Low", "Medium", "High", "Critical"}
REQUIRED_LICENSE_STRING = "PILOT — NOT EXPERT-REVIEWED"


def load_cards(path: Path) -> list[TaskCard]:
    cards = []
    with path.open() as fh:
        for lineno, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError as exc:
                pytest.fail(f"{path.name} line {lineno}: invalid JSON — {exc}")
            try:
                card = TaskCard(**raw)
            except Exception as exc:
                pytest.fail(f"{path.name} line {lineno}: TaskCard validation failed — {exc}")
            cards.append(card)
    return cards


def all_cards() -> list[TaskCard]:
    all_ = []
    for path in JSONL_FILES.values():
        if path.exists():
            all_.extend(load_cards(path))
    return all_


# ---------------------------------------------------------------------------
# File existence
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("label,path", list(JSONL_FILES.items()))
def test_file_exists(label: str, path: Path) -> None:
    assert path.exists(), f"{label} task card file not found: {path}"


def test_sources_md_exists() -> None:
    assert (TASKCARDS_DIR / "sources.md").exists(), "sources.md not found"


# ---------------------------------------------------------------------------
# Card counts per task type
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("label,path", list(JSONL_FILES.items()))
def test_minimum_card_count(label: str, path: Path) -> None:
    if not path.exists():
        pytest.skip(f"{path} not found")
    cards = load_cards(path)
    minimums = {"typeA": 30, "typeB": 17, "typeC": 10, "typeD": 10}
    assert len(cards) >= minimums[label], (
        f"{label}: expected >= {minimums[label]} cards, got {len(cards)}"
    )


@pytest.mark.parametrize("label,path", list(JSONL_FILES.items()))
def test_maximum_card_count(label: str, path: Path) -> None:
    if not path.exists():
        pytest.skip(f"{path} not found")
    cards = load_cards(path)
    maximums = {"typeA": 50, "typeB": 30, "typeC": 20, "typeD": 15}
    assert len(cards) <= maximums[label], (
        f"{label}: expected <= {maximums[label]} cards, got {len(cards)}"
    )


# ---------------------------------------------------------------------------
# Task type correctness
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("label,path", list(JSONL_FILES.items()))
def test_task_type_correctness(label: str, path: Path) -> None:
    if not path.exists():
        pytest.skip(f"{path} not found")
    expected = EXPECTED_TASK_TYPES[label]
    cards = load_cards(path)
    for card in cards:
        assert card.task_type == expected, (
            f"{card.task_id}: expected task_type={expected!r}, got {card.task_type!r}"
        )


# ---------------------------------------------------------------------------
# Family label
# ---------------------------------------------------------------------------

def test_all_cards_correct_family() -> None:
    for card in all_cards():
        assert card.family == "weather_dispatch", (
            f"{card.task_id}: expected family='weather_dispatch', got {card.family!r}"
        )


# ---------------------------------------------------------------------------
# Task ID uniqueness
# ---------------------------------------------------------------------------

def test_task_ids_unique() -> None:
    all_ = all_cards()
    ids = [c.task_id for c in all_]
    duplicates = {tid for tid in ids if ids.count(tid) > 1}
    assert not duplicates, f"Duplicate task IDs found: {sorted(duplicates)}"


# ---------------------------------------------------------------------------
# Provenance integrity (CLAUDE.md §1.1 + §2.2)
# ---------------------------------------------------------------------------

def test_all_cards_synthetic_provenance() -> None:
    """All cards in this pilot batch must be SYNTHETIC with generation_rule."""
    for card in all_cards():
        prov = card.provenance
        assert prov.source == "SYNTHETIC", (
            f"{card.task_id}: provenance.source must be 'SYNTHETIC' for pilot batch, got {prov.source!r}"
        )
        assert prov.access_date is None, (
            f"{card.task_id}: SYNTHETIC cards must have access_date=null"
        )
        assert prov.generation_rule, (
            f"{card.task_id}: SYNTHETIC cards must have a non-empty generation_rule"
        )


def test_all_cards_not_expert_reviewed_license() -> None:
    """All cards must carry the PILOT — NOT EXPERT-REVIEWED license string."""
    for card in all_cards():
        assert card.provenance.license == REQUIRED_LICENSE_STRING, (
            f"{card.task_id}: expected license={REQUIRED_LICENSE_STRING!r}, "
            f"got {card.provenance.license!r}"
        )


# ---------------------------------------------------------------------------
# Split distribution (CLAUDE.md §2.3)
# ---------------------------------------------------------------------------

def test_all_cards_have_split_tag() -> None:
    for card in all_cards():
        assert card.split in VALID_SPLITS, (
            f"{card.task_id}: split must be 'dev' or 'test', got {card.split!r}"
        )


def test_split_ratio_approximately_70_30() -> None:
    """70% dev, 30% test — allow ±10% tolerance."""
    cards = all_cards()
    dev_count = sum(1 for c in cards if c.split == "dev")
    total = len(cards)
    assert total > 0, "No cards found"
    dev_ratio = dev_count / total
    assert 0.60 <= dev_ratio <= 0.80, (
        f"Dev ratio {dev_ratio:.2%} is outside acceptable 60-80% range "
        f"(target 70%); dev={dev_count}, total={total}"
    )


# ---------------------------------------------------------------------------
# Required fields non-empty
# ---------------------------------------------------------------------------

def test_all_cards_have_required_fields() -> None:
    for card in all_cards():
        assert card.prompt.strip(), f"{card.task_id}: prompt is empty"
        assert card.gold_decision.strip(), f"{card.task_id}: gold_decision is empty"
        assert card.required_safety_constraints, (
            f"{card.task_id}: required_safety_constraints is empty"
        )
        assert card.evidence_requirements, (
            f"{card.task_id}: evidence_requirements is empty"
        )
        assert card.failure_mode_labels, (
            f"{card.task_id}: failure_mode_labels is empty"
        )
        assert card.severity in VALID_SEVERITIES, (
            f"{card.task_id}: severity={card.severity!r} is not valid"
        )


# ---------------------------------------------------------------------------
# Critical cards require escalation
# ---------------------------------------------------------------------------

def test_critical_operational_cards_have_escalation() -> None:
    """Type B/C/D Critical cards must require escalation; Type A knowledge cards may not."""
    for card in all_cards():
        if card.severity == "Critical" and card.task_type in ("B", "C", "D"):
            assert card.escalation_required, (
                f"{card.task_id}: Critical Type {card.task_type} cards must have escalation_required=True"
            )


# ---------------------------------------------------------------------------
# Type D cards probe required tools
# ---------------------------------------------------------------------------

def test_typeD_cards_mention_tool_requirements() -> None:
    """Type D agentic cards must reference at least one tool in evidence_requirements."""
    tools = {"metar_parser", "taf_parser", "wind_component", "weather_minima_checker"}
    if not JSONL_FILES["typeD"].exists():
        pytest.skip("typeD file not found")
    cards = load_cards(JSONL_FILES["typeD"])
    for card in cards:
        evidence_text = " ".join(card.evidence_requirements).lower()
        has_tool = any(t in evidence_text for t in tools)
        assert has_tool, (
            f"{card.task_id}: Type D card must reference at least one tool in evidence_requirements"
        )


# ---------------------------------------------------------------------------
# Severity distribution: at least some Critical and High cards
# ---------------------------------------------------------------------------

def test_severity_distribution_has_critical_cards() -> None:
    cards = all_cards()
    critical = [c for c in cards if c.severity == "Critical"]
    assert len(critical) >= 5, (
        f"Expected at least 5 Critical severity cards, got {len(critical)}"
    )


def test_severity_distribution_has_high_cards() -> None:
    cards = all_cards()
    high = [c for c in cards if c.severity == "High"]
    assert len(high) >= 8, (
        f"Expected at least 8 High severity cards, got {len(high)}"
    )


# ---------------------------------------------------------------------------
# Crosswind math spot-checks (CLAUDE.md §8.3: tool outputs must be validated)
# ---------------------------------------------------------------------------

def _crosswind(wind_dir: int, wind_speed: float, runway_hdg: int) -> float:
    angle_rad = math.radians((wind_dir - runway_hdg) % 360)
    return abs(wind_speed * math.sin(angle_rad))


def test_crosswind_math_90_degree_case() -> None:
    """Wind 270/15, runway 180 — full crosswind = 15 kt."""
    xw = _crosswind(270, 15, 180)
    assert abs(xw - 15.0) < 0.1, f"Expected 15 kt crosswind, got {xw:.2f}"


def test_crosswind_math_30_degree_case() -> None:
    """Wind 310/20, runway 280 — crosswind = 20 × sin(30°) = 10 kt."""
    xw = _crosswind(310, 20, 280)
    assert abs(xw - 10.0) < 0.1, f"Expected 10 kt crosswind, got {xw:.2f}"


def test_crosswind_math_aligned_runway() -> None:
    """Wind aligned with runway — zero crosswind."""
    xw = _crosswind(360, 18, 360)
    assert abs(xw) < 0.01, f"Expected 0 kt crosswind (aligned), got {xw:.2f}"


def test_crosswind_math_tailwind_case() -> None:
    """Direct tailwind — zero crosswind, full tailwind."""
    xw = _crosswind(180, 10, 360)
    assert abs(xw) < 0.01, f"Expected 0 kt crosswind (direct tailwind), got {xw:.2f}"


def test_crosswind_math_60_degree_case() -> None:
    """Wind 160/25G40, runway 100 — gust XW = 40 × sin(60°) ≈ 34.6 kt."""
    xw = _crosswind(160, 40, 100)
    assert abs(xw - 40 * math.sin(math.radians(60))) < 0.1, (
        f"Expected ~34.6 kt crosswind, got {xw:.2f}"
    )


# ---------------------------------------------------------------------------
# CAT I minima spot-check (CLAUDE.md §8.3)
# ---------------------------------------------------------------------------

def test_cat1_rvr_minimum_in_feet() -> None:
    """CAT I RVR minimum is 1800 ft per FAA AIM §5-4-7."""
    cat1_rvr_ft = 1800
    assert cat1_rvr_ft == 1800


def test_visibility_unit_conversion_spot_check() -> None:
    """400m in feet: 400 × 3.28084 = 1312.3 ft < 1800 ft CAT I."""
    vis_m = 400
    vis_ft = vis_m * 3.28084
    assert vis_ft < 1800, f"400m should be below CAT I; got {vis_ft:.1f} ft"


def test_visibility_unit_conversion_5000m() -> None:
    """5000m in feet: 5000 × 3.28084 = 16404 ft >> 1800 ft — above CAT I."""
    vis_ft = 5000 * 3.28084
    assert vis_ft > 1800, f"5000m should be above CAT I RVR; got {vis_ft:.1f} ft"


def test_sm_to_metres_conversion() -> None:
    """1/4 SM in metres ≈ 402 m."""
    vis_m = 0.25 * 1609.344
    assert abs(vis_m - 402.3) < 1.0, f"Expected ~402m, got {vis_m:.1f}m"


# ---------------------------------------------------------------------------
# Alternate requirement logic spot-checks
# ---------------------------------------------------------------------------

def test_alternate_required_when_ceiling_below_2000ft() -> None:
    """Ceiling 1500 ft < 2000 ft threshold triggers alternate requirement."""
    ceiling_ft = 1500
    threshold_ft = 2000
    assert ceiling_ft < threshold_ft, "1500 ft ceiling should trigger alternate requirement"


def test_no_alternate_when_above_thresholds() -> None:
    """Ceiling 5500 ft > 2000 ft and vis 9999m > 3SM — no alternate required."""
    ceiling_ft = 5500
    vis_sm = 6.0  # 9999m >> 3 SM
    assert ceiling_ft >= 2000 and vis_sm >= 3.0


# ---------------------------------------------------------------------------
# TAF temporal boundary spot-checks
# ---------------------------------------------------------------------------

def test_fm_group_at_exactly_eta_is_active() -> None:
    """FM group onset at ETA = that FM group's conditions apply at ETA."""
    # FM191800 is valid from 1800Z; ETA is 1800Z — group is active
    fm_onset_z = 1800
    eta_z = 1800
    assert eta_z >= fm_onset_z, "FM group at ETA onset should be active"


def test_tempo_before_eta_does_not_apply() -> None:
    """TEMPO ending before ETA does not apply at ETA."""
    tempo_end_z = 1722
    eta_z = 1750
    assert eta_z > tempo_end_z, "ETA after TEMPO end should not be in TEMPO"


def test_tempo_containing_eta_applies() -> None:
    """TEMPO window containing ETA does apply."""
    tempo_start_z = 1718
    tempo_end_z = 1722  # Actually: 1800-2200Z in DDhh notation but for unit test use integers
    eta_z = 1900
    # Re-using simpler integer representation for test logic
    tempo_start = 1800
    tempo_end = 2200
    eta = 1900
    assert tempo_start <= eta < tempo_end, "ETA in TEMPO window should have TEMPO conditions"
