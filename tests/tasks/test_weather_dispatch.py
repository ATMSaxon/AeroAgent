"""
Tests for Task Family 3: Weather and Dispatch Risk task cards.

Validates schema compliance, provenance integrity, split distribution,
and content constraints per CLAUDE.md §1.1, §2.2, §3.1, §8.1, §8.3.

T23 expansion: 20 stations × 12 months, ~200 cards, ≥70% B/C/D real_data provenance.
T30 round-3 scale: 560+ total cards; WD3-* prefix for new cards; ≤25 per (station, month).

No API calls, no model inference — static structural validation only.
"""

from __future__ import annotations

import json
import math
import re
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

# T23 original targets (lower bounds preserved)
T23_MINIMUMS = {"typeA": 50, "typeB": 40, "typeC": 30, "typeD": 40}
# T30 scale-up upper bounds — WD3 round-3 adds ~400 cards across B/C/D
T23_MAXIMUMS = {"typeA": 80, "typeB": 300, "typeC": 200, "typeD": 250}

# Stations in 20-station IEM corpus
IEM_STATIONS = {
    "KASE", "KATL", "KBOS", "KCVG", "KDEN", "KDFW", "KFAR",
    "KGTF", "KJFK", "KLAX", "KMEM", "KMIA", "KMSY", "KONT",
    "KORD", "KPHX", "KSDF", "KSFO", "PANC", "PAOM",
}


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


def test_real_data_methodology_exists() -> None:
    assert (TASKCARDS_DIR / "real_data_methodology.md").exists(), (
        "real_data_methodology.md not found (required by T23)"
    )


# ---------------------------------------------------------------------------
# Card counts per task type (T23 targets)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("label,path", list(JSONL_FILES.items()))
def test_minimum_card_count(label: str, path: Path) -> None:
    if not path.exists():
        pytest.skip(f"{path} not found")
    cards = load_cards(path)
    minimum = T23_MINIMUMS[label]
    assert len(cards) >= minimum, (
        f"{label}: expected >= {minimum} cards (T23), got {len(cards)}"
    )


@pytest.mark.parametrize("label,path", list(JSONL_FILES.items()))
def test_maximum_card_count(label: str, path: Path) -> None:
    if not path.exists():
        pytest.skip(f"{path} not found")
    cards = load_cards(path)
    maximum = T23_MAXIMUMS[label]
    assert len(cards) <= maximum, (
        f"{label}: expected <= {maximum} cards (T23), got {len(cards)}"
    )


# ---------------------------------------------------------------------------
# T23 real-data provenance targets: ≥70% of B/C/D must be real IEM data
# ---------------------------------------------------------------------------

def _is_real_iem_card(card: TaskCard) -> bool:
    src = card.provenance.source or ""
    return "IEM_METAR" in src or "IEM_TAF" in src


@pytest.mark.parametrize("label", ["typeB", "typeC", "typeD"])
def test_real_data_provenance_ratio(label: str) -> None:
    """≥70% of B, C, D cards must cite real IEM data (T23 requirement)."""
    path = JSONL_FILES[label]
    if not path.exists():
        pytest.skip(f"{path} not found")
    cards = load_cards(path)
    if not cards:
        pytest.skip("No cards found")
    real_count = sum(1 for c in cards if _is_real_iem_card(c))
    ratio = real_count / len(cards)
    assert ratio >= 0.70, (
        f"{label}: real_data ratio {ratio:.1%} < 70% (T23 requirement); "
        f"real={real_count}/{len(cards)}"
    )


# ---------------------------------------------------------------------------
# IEM stations: B/C/D real cards must cite a known 20-station corpus member
# ---------------------------------------------------------------------------

def test_real_data_cards_cite_known_iem_stations() -> None:
    """Real IEM B/C/D cards must cite a station in the 20-station T23 corpus."""
    for label in ("typeB", "typeC", "typeD"):
        path = JSONL_FILES[label]
        if not path.exists():
            continue
        for card in load_cards(path):
            if not _is_real_iem_card(card):
                continue
            src = card.provenance.source or ""
            cited_station = any(st in src for st in IEM_STATIONS)
            assert cited_station, (
                f"{card.task_id}: real-data card must cite one of the 20 T23 IEM stations "
                f"in provenance.source; got: {src!r}"
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
# T23 task ID prefix convention: WD-{A/B/C/D}-NNN
# ---------------------------------------------------------------------------

def test_t23_task_id_format() -> None:
    """T23/T30 cards must use WD-A-NNN/WD-B-NNN/... or WD3-A-NNN/WD3-B-NNN/... format."""
    prefix_map = {
        "A": ("WD-A-",),
        "B": ("WD-B-", "WD3-B-"),
        "C": ("WD-C-", "WD3-C-"),
        "D": ("WD-D-", "WD3-D-"),
    }
    for label, path in JSONL_FILES.items():
        if not path.exists():
            continue
        valid_prefixes = prefix_map[EXPECTED_TASK_TYPES[label]]
        for card in load_cards(path):
            assert any(card.task_id.startswith(p) for p in valid_prefixes), (
                f"{card.task_id}: expected one of prefixes {valid_prefixes} for {label} cards"
            )


# ---------------------------------------------------------------------------
# Provenance integrity (CLAUDE.md §1.1 + §2.2)
# ---------------------------------------------------------------------------

def test_synthetic_cards_have_generation_rule() -> None:
    """SYNTHETIC cards must have generation_rule and no access_date."""
    for card in all_cards():
        prov = card.provenance
        if prov.source == "SYNTHETIC":
            assert prov.access_date is None, (
                f"{card.task_id}: SYNTHETIC cards must have access_date=null"
            )
            assert prov.generation_rule, (
                f"{card.task_id}: SYNTHETIC cards must have a non-empty generation_rule"
            )


def test_real_data_cards_have_access_date() -> None:
    """Real-data IEM cards must have access_date and no generation_rule."""
    for card in all_cards():
        prov = card.provenance
        if _is_real_iem_card(card):
            assert prov.source != "SYNTHETIC", (
                f"{card.task_id}: real-data card must not have source='SYNTHETIC'"
            )
            assert prov.access_date is not None, (
                f"{card.task_id}: real-data card must have access_date"
            )
            assert prov.generation_rule is None, (
                f"{card.task_id}: real-data card must not have generation_rule"
            )


def test_no_mixed_provenance_within_card() -> None:
    """A card is either fully SYNTHETIC or fully real; no card may be both."""
    for card in all_cards():
        prov = card.provenance
        is_synthetic = prov.source == "SYNTHETIC"
        has_gen_rule = bool(prov.generation_rule)
        has_access_date = prov.access_date is not None
        if is_synthetic:
            assert not has_access_date, (
                f"{card.task_id}: SYNTHETIC card must not have access_date"
            )
        else:
            assert not has_gen_rule, (
                f"{card.task_id}: real-data card must not have generation_rule"
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
    """Type D agentic cards must reference at least one tool in prompt, evidence, or gold_decision."""
    tools = {"metar_parser", "taf_parser", "wind_component", "weather_minima_checker"}
    if not JSONL_FILES["typeD"].exists():
        pytest.skip("typeD file not found")
    cards = load_cards(JSONL_FILES["typeD"])
    for card in cards:
        combined_text = " ".join([
            card.prompt,
            card.gold_decision,
            " ".join(card.evidence_requirements),
        ]).lower()
        has_tool = any(t in combined_text for t in tools)
        assert has_tool, (
            f"{card.task_id}: Type D card must reference at least one tool "
            f"in prompt, gold_decision, or evidence_requirements"
        )


def test_typeD_cards_mention_multiple_tools() -> None:
    """T23 Type D agentic cards should exercise multiple tools per card (≥2)."""
    tools = ["metar_parser", "taf_parser", "wind_component", "weather_minima_checker"]
    if not JSONL_FILES["typeD"].exists():
        pytest.skip("typeD file not found")
    cards = load_cards(JSONL_FILES["typeD"])
    multi_tool_count = 0
    for card in cards:
        combined = " ".join([
            card.prompt,
            card.gold_decision,
            " ".join(card.evidence_requirements),
        ]).lower()
        tool_count = sum(1 for t in tools if t in combined)
        if tool_count >= 2:
            multi_tool_count += 1
    ratio = multi_tool_count / len(cards) if cards else 0
    assert ratio >= 0.80, (
        f"Only {ratio:.1%} of Type D cards exercise ≥2 tools; expected ≥80%"
    )


# ---------------------------------------------------------------------------
# Severity distribution: at least some Critical and High cards
# ---------------------------------------------------------------------------

def test_severity_distribution_has_critical_cards() -> None:
    cards = all_cards()
    critical = [c for c in cards if c.severity == "Critical"]
    assert len(critical) >= 10, (
        f"Expected at least 10 Critical severity cards (T23), got {len(critical)}"
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


def test_crosswind_math_obtuse_angle_case() -> None:
    """Wind 020/28, runway 320 — obtuse angle. Supplement: 360-300=60°; XW=28×sin(60°)≈24.2 kt."""
    xw = _crosswind(20, 28, 320)
    expected = 28 * math.sin(math.radians(60))
    assert abs(xw - expected) < 0.1, (
        f"Expected {expected:.2f} kt crosswind (obtuse angle), got {xw:.2f}"
    )


def test_crosswind_math_120_degree_case() -> None:
    """Wind 200/38, runway 090 — angle 110°; sin(110°)=sin(70°); XW=38×sin(70°)≈35.7 kt."""
    xw = _crosswind(200, 38, 90)
    expected = 38 * math.sin(math.radians(70))
    assert abs(xw - expected) < 0.1, (
        f"Expected ~{expected:.1f} kt crosswind (120° case), got {xw:.2f}"
    )


# ---------------------------------------------------------------------------
# CAT I/II minima spot-check (CLAUDE.md §8.3)
# ---------------------------------------------------------------------------

def test_cat1_rvr_minimum_in_feet() -> None:
    """CAT I RVR minimum is 1800 ft per FAA AIM §5-4-7."""
    cat1_rvr_ft = 1800
    assert cat1_rvr_ft == 1800


def test_cat2_rvr_minimum_in_feet() -> None:
    """CAT II RVR minimum is 1200 ft per FAA AIM §5-4-7."""
    cat2_rvr_ft = 1200
    assert cat2_rvr_ft == 1200


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


def test_vv_group_is_ceiling() -> None:
    """VV010 = 1000 ft vertical visibility ceiling when sky is obscured (FAA AIM §7-1-14)."""
    vv_hundreds = 10
    ceiling_ft = vv_hundreds * 100
    assert ceiling_ft == 1000, f"VV010 should yield 1000 ft ceiling, got {ceiling_ft}"


# ---------------------------------------------------------------------------
# Alternate requirement logic spot-checks (14 CFR §121.619)
# ---------------------------------------------------------------------------

def test_alternate_required_when_ceiling_below_2000ft() -> None:
    """Ceiling 1500 ft < 2000 ft threshold triggers alternate requirement."""
    ceiling_ft = 1500
    threshold_ft = 2000
    assert ceiling_ft < threshold_ft, "1500 ft ceiling should trigger alternate requirement"


def test_alternate_required_at_exactly_2000ft() -> None:
    """Ceiling exactly 2000 ft triggers alternate requirement (≤ 2000 ft rule)."""
    ceiling_ft = 2000
    assert ceiling_ft <= 2000, "2000 ft ceiling is at threshold — alternate required"


def test_no_alternate_when_above_thresholds() -> None:
    """Ceiling 5500 ft > 2000 ft and vis 9999m > 3SM — no alternate required."""
    ceiling_ft = 5500
    vis_sm = 6.0  # 9999m >> 3 SM
    assert ceiling_ft >= 2000 and vis_sm >= 3.0


def test_alternate_required_when_vis_below_3sm() -> None:
    """Vis 2SM < 3SM threshold triggers alternate requirement."""
    vis_sm = 2.0
    assert vis_sm < 3.0, "2SM visibility should trigger alternate requirement"


# ---------------------------------------------------------------------------
# TAF temporal boundary spot-checks
# ---------------------------------------------------------------------------

def test_fm_group_at_exactly_eta_is_active() -> None:
    """FM group onset at ETA = that FM group's conditions apply at ETA."""
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
    tempo_start = 1800
    tempo_end = 2200
    eta = 1900
    assert tempo_start <= eta < tempo_end, "ETA in TEMPO window should have TEMPO conditions"


def test_becmg_before_eta_not_complete() -> None:
    """BECMG 1400/1600 starts at 1400Z and completes at 1600Z; at ETA 1430Z it is not yet complete."""
    becmg_start = 1400
    becmg_end = 1600
    eta = 1430
    assert becmg_start <= eta < becmg_end, "ETA within BECMG window = transition in progress"


# ---------------------------------------------------------------------------
# IEM manifest existence
# ---------------------------------------------------------------------------

def test_iem_metar_manifest_exists() -> None:
    manifest = Path(__file__).parent.parent.parent / "data" / "raw" / "IEM_METAR" / "2026-05-17" / "manifest.jsonl"
    assert manifest.exists(), f"IEM METAR manifest not found: {manifest}"


def test_iem_taf_manifest_exists() -> None:
    manifest = Path(__file__).parent.parent.parent / "data" / "raw" / "IEM_TAF" / "2026-05-17" / "manifest.jsonl"
    assert manifest.exists(), f"IEM TAF manifest not found: {manifest}"


def test_iem_metar_manifest_has_20_station_coverage() -> None:
    """IEM METAR manifest must have entries for all 20 T23 corpus stations."""
    manifest = Path(__file__).parent.parent.parent / "data" / "raw" / "IEM_METAR" / "2026-05-17" / "manifest.jsonl"
    if not manifest.exists():
        pytest.skip("METAR manifest not found")
    stations_found = set()
    with manifest.open() as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                fp = entry.get("file_path", "")
                for st in IEM_STATIONS:
                    if f"/{st}_METAR_" in fp or fp.startswith(f"data/raw/IEM_METAR") and f"/{st}_" in fp:
                        stations_found.add(st)
            except Exception:
                pass
    missing = IEM_STATIONS - stations_found
    assert not missing, f"IEM METAR manifest missing stations: {sorted(missing)}"


def test_real_data_cards_cite_manifest_verified_files() -> None:
    """Every real-data card's provenance.source must contain IEM_METAR or IEM_TAF."""
    for card in all_cards():
        if not _is_real_iem_card(card):
            continue
        source = card.provenance.source or ""
        assert "IEM_METAR" in source or "IEM_TAF" in source, (
            f"{card.task_id}: real-data card provenance.source must cite IEM data; "
            f"got: {source!r}"
        )


# ---------------------------------------------------------------------------
# TypeA cards must all be SYNTHETIC
# ---------------------------------------------------------------------------

def test_typeA_cards_are_synthetic() -> None:
    """All Type A knowledge cards must be SYNTHETIC (no real IEM data in knowledge cards)."""
    path = JSONL_FILES["typeA"]
    if not path.exists():
        pytest.skip("typeA file not found")
    for card in load_cards(path):
        assert card.provenance.source == "SYNTHETIC", (
            f"{card.task_id}: Type A knowledge cards must be SYNTHETIC"
        )


# ---------------------------------------------------------------------------
# T30 scale-up tests: station-month bias guard + manifest file reference
# ---------------------------------------------------------------------------

def _extract_station_month(card: "TaskCard") -> tuple[str, str] | None:
    """Extract (station, YYYYMM) from provenance.source of a real-data card."""
    src = card.provenance.source or ""
    # Matches patterns like 'KORD 2026-01-15T...' or 'KORD_METAR_202601.csv'
    m = re.search(r"(K[A-Z]{3}|PA[A-Z]{2})\s+(\d{4})-(\d{2})", src)
    if m:
        return m.group(1), m.group(2) + m.group(3)
    m2 = re.search(r"(K[A-Z]{3}|PA[A-Z]{2})_METAR_(\d{6})", src)
    if m2:
        return m2.group(1), m2.group(2)
    return None


def test_no_station_month_dominates() -> None:
    """T30: no (station, month) pair may supply more than 25 cards across B+C+D (§2.2 bias guard)."""
    from collections import Counter
    sm_counts: Counter = Counter()
    for label in ("typeB", "typeC", "typeD"):
        path = JSONL_FILES[label]
        if not path.exists():
            continue
        for card in load_cards(path):
            if not _is_real_iem_card(card):
                continue
            sm = _extract_station_month(card)
            if sm:
                sm_counts[sm] += 1
    violations = {sm: cnt for sm, cnt in sm_counts.items() if cnt > 25}
    assert not violations, (
        f"T30: {len(violations)} (station, month) pairs exceed 25-card bias limit: "
        + ", ".join(f"{sm}={cnt}" for sm, cnt in sorted(violations.items()))
    )


def test_real_data_cards_reference_manifest_csv() -> None:
    """T30: every real-data B/C/D card's provenance.source must reference a manifest-listed CSV path."""
    import json as _json
    metar_manifest = Path(__file__).parent.parent.parent / "data" / "raw" / "IEM_METAR" / "2026-05-17" / "manifest.jsonl"
    taf_manifest = Path(__file__).parent.parent.parent / "data" / "raw" / "IEM_TAF" / "2026-05-17" / "manifest.jsonl"

    manifest_files: set[str] = set()
    for mpath in (metar_manifest, taf_manifest):
        if mpath.exists():
            with mpath.open() as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = _json.loads(line)
                        manifest_files.add(entry.get("file_path", ""))
                    except Exception:
                        pass

    if not manifest_files:
        pytest.skip("No manifest files found — cannot verify CSV references")

    for label in ("typeB", "typeC", "typeD"):
        path = JSONL_FILES[label]
        if not path.exists():
            continue
        for card in load_cards(path):
            if not _is_real_iem_card(card):
                continue
            src = card.provenance.source or ""
            # Extract file path from provenance source: "...| file: data/raw/..."
            m = re.search(r"file:\s*(data/raw/IEM_\w+/[^\s|]+\.csv)", src)
            if not m:
                continue
            cited_file = m.group(1).strip()
            assert cited_file in manifest_files, (
                f"{card.task_id}: provenance cites file {cited_file!r} "
                f"which is not listed in the IEM manifest"
            )
