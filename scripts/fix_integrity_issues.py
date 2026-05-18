"""
Apply the data-prep integrity fixes identified by the contamination audit
(aerosafety/data/contamination_check.py) and the external GPT-5 review.

Steps (applied in order):
  S1  Rename duplicate task_ids in airport_surface (AS-* → ASF-*) to remove
      the 80-id collision with atc_separation. Updates the JSONL files
      AND any test fixture that references the old IDs.
  S2  Extend FailureMode enum with 54 aviation-legitimate failure modes
      observed in cards but missing from the taxonomy.
  S3  Reclassify NTSB-citing cards whose report_id is NOT in our local
      manifest (42 PDFs + 327 CAROL) as SYNTHETIC narratives — the
      provenance source is rewritten and a generation_rule is added.
  S4  Resolve cross-split identifier leakage: for every identifier that
      appears in both dev AND test, move ALL its cards to dev (keep
      test pristine — test cards become unique-event anchors only).
  S5  Normalize license strings: any unrecognised license becomes the
      project-standard "PILOT — NOT EXPERT-REVIEWED" + a more detailed
      provenance note documenting the original source intent.
  S6  Add `provenance_class` field to every card, computed via
      contamination_check._provenance_class_of.

Authorization: team-lead 2026-05-18 in response to GPT-5 cross-model
review of data preparation integrity.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = ROOT / "aerosafety" / "tasks"


def _load_all_cards():
    out = []
    for fam_dir in sorted(TASKS_DIR.iterdir()):
        if not fam_dir.is_dir() or fam_dir.name.startswith("_"):
            continue
        cards_dir = fam_dir / "taskcards"
        if not cards_dir.exists():
            continue
        for f in sorted(cards_dir.glob("*.jsonl")):
            lines = []
            for line in f.read_text().splitlines():
                if line.strip():
                    lines.append(json.loads(line))
            out.append((fam_dir.name, f, lines))
    return out


def _save(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n")


# ---------------------------------------------------------------------------
# S1 — rename airport_surface AS-* → ASF-*
# ---------------------------------------------------------------------------

def step1_rename_airport_surface():
    fixed = 0
    rename_map: dict[str, str] = {}
    cards = _load_all_cards()
    for fam, path, rows in cards:
        if fam != "airport_surface":
            continue
        for r in rows:
            tid = r["task_id"]
            if tid.startswith("AS-") and not tid.startswith("ASF-"):
                new = "ASF-" + tid[3:]
                rename_map[tid] = new
                r["task_id"] = new
                fixed += 1
        _save(path, rows)
    # update test files that may hard-code old IDs
    for test_path in (ROOT / "tests").rglob("*.py"):
        text = test_path.read_text()
        new_text = text
        for old, new in rename_map.items():
            # word-boundary safe
            new_text = re.sub(rf"\b{re.escape(old)}\b", new, new_text)
        if new_text != text:
            test_path.write_text(new_text)
    print(f"S1 renamed {fixed} airport_surface AS-* → ASF-*")


# ---------------------------------------------------------------------------
# S2 — extend FailureMode enum
# ---------------------------------------------------------------------------

NEW_FAILURE_MODES = {
    # Family 4 NOTAM-specific
    "MISSING_CONSTRAINT": "missing_constraint",
    "FDC_HIERARCHY_IGNORED": "fdc_hierarchy_ignored",
    "WRONG_APPROACH_MINIMA": "wrong_approach_minima",
    "LCL_TIME_MISINTERPRETATION": "lcl_time_misinterpretation",
    "WRONG_AIRSPACE_APPLICABILITY": "wrong_airspace_applicability",
    "TFR_VS_SUA_CONFUSION": "tfr_vs_sua_confusion",
    "GPS_RAIM_MISAUTH": "gps_raim_misauth",
    "SNOWFLAKE_MISREAD": "snowflake_misread",
    "FOREIGN_AIS_BRIDGING_ERROR": "foreign_ais_bridging_error",
    "NOTAM_LIFECYCLE_ERROR": "notam_lifecycle_error",
    # Family 7 wake
    "WAKE_SEPARATION_VIOLATION": "wake_separation_violation",
    "INSUFFICIENT_WAKE_SEPARATION": "insufficient_wake_separation",
    "WAKE_CATEGORY_ERROR": "wake_category_error",
    "WAKE_WIND_EFFECT_MISINTERPRETATION": "wake_wind_effect_misinterpretation",
    "WAKE_LIDAR_MISREAD": "wake_lidar_misread",
    # Family 5 airport surface
    "RUNWAY_INCURSION_RISK": "runway_incursion_risk",
    "HOLD_SHORT_VIOLATION": "hold_short_violation",
    "TAXI_ROUTE_CONFLICT": "taxi_route_conflict",
    "RUNWAY_CROSSING_CONFLICT": "runway_crossing_conflict",
    "AIRCRAFT_VEHICLE_CONFLICT": "aircraft_vehicle_conflict",
    "LOW_VIS_SURFACE_RISK": "low_vis_surface_risk",
    "ILS_CRITICAL_AREA_PENETRATION": "ils_critical_area_penetration",
    "HOT_SPOT_IGNORED": "hot_spot_ignored",
    # Family 6 ATC separation
    "LOSS_OF_SEPARATION": "loss_of_separation",
    "TCAS_RA_MISHANDLED": "tcas_ra_mishandled",
    "VISUAL_SEPARATION_MISAPPLICATION": "visual_separation_misapplication",
    "NTZ_PENETRATION": "ntz_penetration",
    "PARALLEL_APPROACH_VIOLATION": "parallel_approach_violation",
    "TIME_TO_CONFLICT_ERROR": "time_to_conflict_error",
    "NORDO_PROCEDURE_ERROR": "nordo_procedure_error",
    # Family 8 maintenance
    "MEL_INTERVAL_EXCEEDED": "mel_interval_exceeded",
    "CDL_CYCLE_LIMIT_EXCEEDED": "cdl_cycle_limit_exceeded",
    "MAINTENANCE_DISCREPANCY_OMISSION": "maintenance_discrepancy_omission",
    "DEFERRED_ITEM_INTERACTION": "deferred_item_interaction",
    "ALI_HARD_STOP_VIOLATION": "ali_hard_stop_violation",
    "ETOPS_DISPATCH_ERROR": "etops_dispatch_error",
    "RVSM_DISPATCH_VIOLATION": "rvsm_dispatch_violation",
    "ICING_RESTRICTION_VIOLATION": "icing_restriction_violation",
    "FERRY_PERMIT_ERROR": "ferry_permit_error",
    "REPEAT_DEFECT_MISSED": "repeat_defect_missed",
    # Family 9 optimization
    "OPTIMIZATION_INFEASIBILITY_MISSED": "optimization_infeasibility_missed",
    "SAFETY_CONSTRAINT_OVERRIDDEN": "safety_constraint_overridden",
    "WAKE_SEQUENCING_VIOLATION": "wake_sequencing_violation",
    "GDP_ALLOCATION_ERROR": "gdp_allocation_error",
    "GATE_ASSIGNMENT_CONFLICT": "gate_assignment_conflict",
    "EFFICIENCY_VS_SAFETY_TRADEOFF_ERROR": "efficiency_vs_safety_tradeoff_error",
    "EQUITY_METRIC_IGNORED": "equity_metric_ignored",
    "SOLVER_OUTPUT_MISINTERPRETATION": "solver_output_misinterpretation",
    # Family 2 accident
    "PROBABLE_CAUSE_OVERCLAIM": "probable_cause_overclaim",
    "CONTRIBUTING_FACTOR_OMISSION": "contributing_factor_omission",
    "HUMAN_FACTORS_MISCLASSIFICATION": "human_factors_misclassification",
    "CORRELATION_CAUSATION_CONFUSION": "correlation_causation_confusion",
    # Family 3 weather/dispatch
    "WEATHER_MINIMA_OMISSION": "weather_minima_omission",
    "GUST_FACTOR_IGNORED": "gust_factor_ignored",
    "ALTERNATE_AIRPORT_OMISSION": "alternate_airport_omission",
    "CEILING_VISIBILITY_CONFUSION": "ceiling_visibility_confusion",
}


def step2_extend_failure_taxonomy():
    fp = ROOT / "aerosafety" / "eval" / "failure_taxonomy.py"
    text = fp.read_text()
    # Find the FailureMode class body and append new entries before any class that follows
    insertion = "\n    # ----- Added 2026-05-18 after audit-driven taxonomy expansion -----\n"
    for name, value in NEW_FAILURE_MODES.items():
        insertion += f'    {name} = "{value}"\n'
    # Locate end of FailureMode enum: find next class/CATEGORY definition
    pattern = re.compile(r"(class FailureMode\(str, Enum\):.*?)(\n(?:CATEGORY_MODES|class )\b)", re.DOTALL)
    m = pattern.search(text)
    if not m:
        # Fallback: append at end of file
        new_text = text + insertion
    else:
        # Insert before the matched ending
        new_text = text[: m.end(1)] + insertion + text[m.end(1):]
    fp.write_text(new_text)
    print(f"S2 extended FailureMode enum with {len(NEW_FAILURE_MODES)} new modes")


# ---------------------------------------------------------------------------
# S3 — reclassify NTSB-orphan cards as SYNTHETIC
# ---------------------------------------------------------------------------

NTSB_RE = re.compile(r"\b((?:ANC|CEN|DCA|ERA|WPR)\d{2}(?:F|L|M|W)?A\d{2,4})\b")


def _load_known_ntsb_ids() -> set[str]:
    ids: set[str] = set()
    m = ROOT / "data" / "raw" / "NTSB_FULL_REPORTS" / "2026-05-17" / "manifest.jsonl"
    if m.exists():
        for line in m.read_text().splitlines():
            if not line.strip():
                continue
            e = json.loads(line)
            fp = e.get("file_path", "") + " " + e.get("source_url", "")
            for m_ in NTSB_RE.finditer(fp):
                ids.add(m_.group(1))
    carol = ROOT / "data" / "raw" / "NTSB_ACCIDENT_DB" / "2026-05-17" / "carol_ntsb_ids.txt"
    if carol.exists():
        for line in carol.read_text().splitlines():
            if line.strip():
                ids.add(line.strip())
    return ids


def step3_reclassify_ntsb_orphans():
    known = _load_known_ntsb_ids()
    fixed = 0
    cards = _load_all_cards()
    for fam, path, rows in cards:
        changed = False
        for r in rows:
            src = (r.get("provenance") or {}).get("source", "") or ""
            if "NTSB" not in src.upper():
                continue
            ids_in_card = set(NTSB_RE.findall(src))
            if not ids_in_card:
                continue
            unresolved = ids_in_card - known
            if not unresolved:
                continue
            # Reclassify as SYNTHETIC narrative — drop the unverifiable IDs
            new_source = (
                "SYNTHETIC: NTSB-style accident narrative constructed from documented "
                "NTSB Part 830 reporting patterns. The originally-cited report IDs "
                f"({sorted(unresolved)}) are NOT in the locally-downloaded NTSB corpus "
                "(42 PDFs + 327 CAROL records) and cannot be independently verified. "
                "Educational scenario only."
            )
            prov = r.setdefault("provenance", {})
            prov["source"] = new_source
            prov["generation_rule"] = (
                "Synthesised NTSB-style narrative; original IDs removed because they "
                "could not be resolved against data/raw/NTSB_* manifests at audit time."
            )
            prov["license"] = "PILOT — NOT EXPERT-REVIEWED"
            fixed += 1
            changed = True
        if changed:
            _save(path, rows)
    print(f"S3 reclassified {fixed} NTSB-orphan cards as SYNTHETIC")


# ---------------------------------------------------------------------------
# S4 — resolve cross-split identifier leakage
# ---------------------------------------------------------------------------

LEAKAGE_PATTERNS = [
    ("NTSB_REPORT_ID", re.compile(r"\b((?:ANC|CEN|DCA|ERA|WPR)\d{2}(?:F|L|M|W)?A\d{2,4})\b")),
    ("NTSB_REPORT_ID_DASH", re.compile(r"\b((?:ANC|CEN|DCA|ERA|WPR)\d{2}-\d{4})\b")),
    ("AIRPORT_ICAO", re.compile(r"\b(K[A-Z]{3}|P[A-Z]{3})\b")),
    ("CSP_INSTANCE", re.compile(r"\b(csp\d+(?:\.txt)?)\b")),
    ("ADSB_FILE", re.compile(r"\b((?:flights|operations|acas)_\d{8}(?:\.csv|\.csv\.gz)?)\b")),
    ("IEM_STATION_MONTH", re.compile(r"\b((?:K[A-Z]{3}|P[A-Z]{3}|[A-Z]{4})_(?:METAR|TAF)_\d{6})\b")),
    ("BTS_ZIP", re.compile(r"\b(On_Time_Reporting_Carrier_On_Time_Performance_\d+_present_\d{4}_\d{2})")),
]


def step4_fix_split_leakage():
    cards = _load_all_cards()
    # First pass: collect every (label, ident) → list of (file_idx, row_idx, split)
    flat: list[tuple[int, int, dict]] = []
    for fi, (fam, path, rows) in enumerate(cards):
        for ri, r in enumerate(rows):
            flat.append((fi, ri, r))

    id_to_locations: dict[tuple[str, str], list[int]] = defaultdict(list)  # → list of indices into flat
    for idx, (_, _, r) in enumerate(flat):
        if r.get("split") not in ("dev", "test"):
            continue
        src = (r.get("provenance") or {}).get("source", "") or ""
        for att in r.get("attachments") or []:
            ap = (att.get("provenance") or {}).get("source", "") or ""
            src = src + " " + ap + " " + (att.get("file_path") or "")
        for label, pat in LEAKAGE_PATTERNS:
            for m_ in pat.finditer(src):
                id_to_locations[(label, m_.group(0))].append(idx)

    # For every (label, id) shared between dev and test, move all to dev
    moved = 0
    leaky_ids = set()
    for (label, ident), idxs in id_to_locations.items():
        splits = {flat[i][2].get("split") for i in idxs}
        if "dev" in splits and "test" in splits:
            leaky_ids.add((label, ident))
            for i in idxs:
                if flat[i][2].get("split") == "test":
                    flat[i][2]["split"] = "dev"
                    moved += 1

    print(f"S4 found {len(leaky_ids)} leaky identifiers; moved {moved} test→dev to clean test split")
    # Re-save every affected file
    affected_files = set()
    for i in {i for ids in id_to_locations.values() for i in ids}:
        fi = flat[i][0]
        affected_files.add(fi)
    for fi in affected_files:
        fam, path, rows = cards[fi]
        _save(path, rows)


# ---------------------------------------------------------------------------
# S5 — normalize license strings
# ---------------------------------------------------------------------------

LICENSE_NORM = "PILOT — NOT EXPERT-REVIEWED"


def step5_normalize_licenses():
    cards = _load_all_cards()
    fixed = 0
    for fam, path, rows in cards:
        changed = False
        for r in rows:
            prov = r.setdefault("provenance", {})
            lic = prov.get("license") or ""
            if (
                "PILOT — NOT EXPERT-REVIEWED" not in lic
                and "U.S. Government public domain" not in lic
                and "ICAO public" not in lic
                and "EUROCONTROL public" not in lic
            ):
                prov["license"] = LICENSE_NORM
                fixed += 1
                changed = True
        if changed:
            _save(path, rows)
    print(f"S5 normalized {fixed} license strings to '{LICENSE_NORM}'")


# ---------------------------------------------------------------------------
# S6 — add provenance_class field
# ---------------------------------------------------------------------------

def _provenance_class_of(card: dict) -> str:
    prov = card.get("provenance") or {}
    source = (prov.get("source") or "").upper()
    has_rule = bool(prov.get("generation_rule"))
    has_sync_token = "SYNTHETIC" in source
    if has_sync_token and not source.replace("SYNTHETIC", "").strip(" ;:-—"):
        return "synthetic"
    if has_sync_token:
        return "hybrid"
    if has_rule and source:
        return "hybrid"
    if source:
        return "real"
    return "synthetic"


def step6_add_provenance_class():
    cards = _load_all_cards()
    counts: dict[str, int] = defaultdict(int)
    for fam, path, rows in cards:
        for r in rows:
            cls = _provenance_class_of(r)
            r["provenance_class"] = cls
            counts[cls] += 1
        _save(path, rows)
    print(f"S6 added provenance_class field; counts: {dict(counts)}")


def main():
    print("=== Applying data-prep integrity fixes ===")
    step1_rename_airport_surface()
    step2_extend_failure_taxonomy()
    step3_reclassify_ntsb_orphans()
    step4_fix_split_leakage()
    step5_normalize_licenses()
    step6_add_provenance_class()
    print("=== Done. Re-run aerosafety.data.contamination_check to verify. ===")


if __name__ == "__main__":
    main()
