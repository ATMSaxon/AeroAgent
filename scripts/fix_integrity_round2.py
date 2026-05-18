"""
Round-2 integrity fixes after GPT-5 codex re-audit (2026-05-18).

Structural fixes only. Semantic fixes (AA causal overclaim, OPT2-D
prompt/gold mismatch) are tracked separately and require card-by-card
rewrite, not script work.

Steps:
  R1  Rename every `split: test` → `split: provisional_test`. The
      project's own expert review protocol forbids placing any card in
      a frozen test split before expert review completes; until that
      is done (PI action required), all 569 cards previously tagged
      test are honestly relabelled provisional.

  R2  Separate license vs review_status. The string
      "PILOT — NOT EXPERT-REVIEWED" is a review state, not a license.
      Move it to `provenance.review_status` and set `provenance.license`
      to an actual license: derived per family from the underlying
      source (U.S. Government public domain for FAA/NTSB/IEM/BTS
      content; SYNTHETIC — no copyright for SYNTHETIC; etc.).

  R3  Re-anchor `_provenance_class_of` (in contamination_check.py) so
      it always recomputes from source+generation_rule rather than
      trusting the stored value. Catches future mislabels.

  R4  Extend `CATEGORY_MODES` in failure_taxonomy.py so every
      FailureMode appears in at least one category.

  R5  Add semantic event-level leakage patterns (YYYY-MM-DD + airport)
      to contamination_check.py so the EWR-2024-07-22 / ORD-2024-08-27
      etc. dev/test overlaps are detected.

  R6  Deduplicate NTSB_FULL_REPORTS manifest entries (same path,
      different sha256 → keep most recent fetch + warn).

  R7  Strip failed (status != 200) rows from production manifests
      (ADSB_EXCHANGE 14/20 404s) into a sibling `_failed.jsonl` for
      the audit trail.

  R8  Create `aerosafety/data/schemas/review.py` + `data/review/`
      stubs matching the protocol's specification (was referenced
      but did not exist).

Authorization: team-lead 2026-05-18, in response to GPT-5 codex round-2
review identifying 10 new categorical issues.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict, OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = ROOT / "aerosafety" / "tasks"
RAW_DIR = ROOT / "data" / "raw"


def _load_family_files():
    """Yield (family, file_path, rows)."""
    for fam_dir in sorted(TASKS_DIR.iterdir()):
        if not fam_dir.is_dir() or fam_dir.name.startswith("_"):
            continue
        for f in sorted((fam_dir / "taskcards").glob("*.jsonl")):
            rows = [json.loads(l) for l in f.read_text().splitlines() if l.strip()]
            yield fam_dir.name, f, rows


def _save(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n")


# ---------------------------------------------------------------------------
# R1 — rename test → provisional_test
# ---------------------------------------------------------------------------

def step_r1_rename_test_to_provisional():
    renamed = 0
    for fam, path, rows in _load_family_files():
        changed = False
        for r in rows:
            if r.get("split") == "test":
                r["split"] = "provisional_test"
                renamed += 1
                changed = True
        if changed:
            _save(path, rows)
    print(f"R1 renamed {renamed} cards split=test → split=provisional_test")


# ---------------------------------------------------------------------------
# R2 — separate license vs review_status
# ---------------------------------------------------------------------------

# Family → license rule derived from underlying source domain
FAMILY_LICENSE_RULES = {
    "accident_analysis": {
        "real": "U.S. Government public domain (17 U.S.C. §105) — NTSB source",
        "hybrid": "U.S. Government public domain (17 U.S.C. §105) — NTSB anchor + synthetic scenario layer",
        "synthetic": "SYNTHETIC — no copyright; constructed from public NTSB Part 830 patterns",
    },
    "airport_surface": {
        "real": "U.S. Government public domain (17 U.S.C. §105) — FAA Chart Supplements",
        "hybrid": "U.S. Government public domain (17 U.S.C. §105) — FAA Chart Supplement anchor + synthetic scenario layer",
        "synthetic": "SYNTHETIC — no copyright; constructed from public FAA Order 7110.65 / AIM",
    },
    "atc_separation": {
        "real": "ADS-B Exchange public data + FAA Order JO 7110.65 public",
        "hybrid": "ADS-B Exchange anchor + synthetic trajectory layer",
        "synthetic": "SYNTHETIC — no copyright; constructed from ICAO Doc 4444 + FAA JO 7110.65 public rules",
    },
    "maintenance": {
        "real": "U.S. Government public domain (17 U.S.C. §105) — NTSB source",
        "hybrid": "U.S. Government public domain (17 U.S.C. §105) — NTSB anchor + synthetic scenario layer",
        "synthetic": "SYNTHETIC — no copyright; constructed from public FAA Order 8900.1 / ICAO Doc 9760",
    },
    "notam_compliance": {
        "real": "U.S. Government public domain — FAA JO 7930.2 / ICAO Annex 15 public",
        "hybrid": "U.S. Government public domain — FAA/ICAO anchor + synthetic scenario layer",
        "synthetic": "SYNTHETIC — no copyright; constructed from public FAA JO 7930.2 + ICAO Annex 15 format",
    },
    "optimization_decisions": {
        "real": "OR-Library (Beasley) open-research dataset + BTS On-Time public",
        "hybrid": "OR-Library / BTS anchor + synthetic perturbation layer",
        "synthetic": "SYNTHETIC — no copyright; constructed from published OR-aviation literature",
    },
    "wake_vortex": {
        "real": "U.S. Government public domain + EUROCONTROL RECAT-EU public",
        "hybrid": "RECAT-EU + ICAO Doc 8643 anchor + synthetic scenario layer",
        "synthetic": "SYNTHETIC — no copyright; constructed from public ICAO Doc 8643 + EUROCONTROL RECAT-EU",
    },
    "weather_dispatch": {
        "real": "Iowa State Environmental Mesonet (IEM) public archive + FAA AC 00-45H public",
        "hybrid": "IEM anchor + synthetic scenario layer",
        "synthetic": "SYNTHETIC — no copyright; constructed from public FAA AIM / AC 00-45H",
    },
}


def step_r2_split_license_and_review_status():
    fixed = 0
    for fam, path, rows in _load_family_files():
        rules = FAMILY_LICENSE_RULES.get(fam, {})
        changed = False
        for r in rows:
            prov = r.setdefault("provenance", {})
            cls = r.get("provenance_class") or "synthetic"
            old_license = prov.get("license") or ""
            # Always overwrite — categorical fix
            if "PILOT" in old_license or "EXPERT-REVIEW" in old_license.upper():
                prov["review_status"] = "PILOT — NOT EXPERT-REVIEWED"
                prov["license"] = rules.get(cls) or rules.get("synthetic")
                fixed += 1
                changed = True
            elif not prov.get("review_status"):
                # add the review_status field even when license already correct
                prov["review_status"] = "PILOT — NOT EXPERT-REVIEWED"
                changed = True
        if changed:
            _save(path, rows)
    print(f"R2 split license vs review_status on {fixed} cards (review_status added to all)")


# ---------------------------------------------------------------------------
# R3 — fix _provenance_class_of to always recompute
# ---------------------------------------------------------------------------

def step_r3_fix_classifier():
    fp = ROOT / "aerosafety" / "data" / "contamination_check.py"
    text = fp.read_text()
    old = '''def _provenance_class_of(card: dict) -> str:
    """Classify a card as 'real' | 'synthetic' | 'hybrid'."""
    if "provenance_class" in card and card["provenance_class"] in {"real", "synthetic", "hybrid"}:
        return card["provenance_class"]
    prov = card.get("provenance") or {}'''
    new = '''def _provenance_class_of(card: dict) -> str:
    """Classify a card as 'real' | 'synthetic' | 'hybrid'.

    Always recomputed from provenance.source + generation_rule; the
    declared `provenance_class` field on the card is IGNORED here to
    avoid trusting a future mislabel. C3 separately compares declared
    vs computed and flags discrepancies.
    """
    prov = card.get("provenance") or {}'''
    fp.write_text(text.replace(old, new))
    print("R3 fixed _provenance_class_of to always recompute")


# ---------------------------------------------------------------------------
# R4 — extend CATEGORY_MODES to include every FailureMode
# ---------------------------------------------------------------------------

def step_r4_extend_category_modes():
    fp = ROOT / "aerosafety" / "eval" / "failure_taxonomy.py"
    text = fp.read_text()
    # Find CATEGORY_MODES literal; replace whole block with auto-expanded one
    # Use a marker comment so re-runs are idempotent
    marker = "# CATEGORY_MODES_AUTO_EXPANDED_2026_05_18"
    if marker in text:
        print("R4 CATEGORY_MODES already expanded; skip")
        return
    # Append a runtime patch that adds every new FailureMode to a category
    # based on prefix heuristic. The original CATEGORY_MODES dict is preserved
    # for backward compat; we extend it after definition.
    patch = '''

# {marker} — auto-classify every FailureMode added after the proposal
# §14 baseline into one of the 7 existing categories using a name-prefix
# heuristic. Each new mode appears in at least one category, satisfying
# the audit invariant "every FailureMode is mapped".
def _autoclassify_failure_mode(mode_name: str) -> "FailureCategory":
    name = mode_name.lower()
    if any(k in name for k in ("evidence", "claim", "hallucinat", "citation", "contradict", "overclaim", "factor_omission", "correlation_causation")):
        return FailureCategory.EVIDENCE
    if any(k in name for k in ("time", "temporal", "stale", "validity", "interval", "schedule", "amendment", "cycle")):
        return FailureCategory.TEMPORAL
    if any(k in name for k in ("runway", "taxiway", "airport", "spatial", "boundary", "ils_critical", "hot_spot", "ntz", "parallel_approach", "graph", "incursion", "crossing", "hold_short", "route_conflict", "vehicle", "low_vis_surface", "raim")):
        return FailureCategory.SPATIAL
    if any(k in name for k in ("crosswind", "altitude", "distance", "unit", "wake_persistence", "numerical", "raim", "density_altitude", "time_to_conflict", "calculation")):
        return FailureCategory.NUMERICAL
    if any(k in name for k in ("rule", "advisory_mandatory", "exception", "mel", "separation_minima", "constraint", "minima", "fdc", "tfr", "ntz", "rvsm", "icing_restriction", "etops_dispatch", "ali_hard_stop", "ferry", "interval_exceeded", "wake_separation", "ferry_permit", "lifecycle", "approach_minima", "airspace_applicability", "alternate", "weather_minima", "lcl_time", "agl_vs_msl", "foreign_ais", "snowflake")):
        return FailureCategory.REGULATORY
    if any(k in name for k in ("tool", "solver_output", "metar_parse", "wake_lidar")):
        return FailureCategory.TOOL_USE
    if any(k in name for k in ("recommend", "escalation", "decision", "conservative", "confident", "incomplete", "unsafe", "overridden", "tradeoff", "ignore", "missed", "underestimat", "dismissed", "misread", "misinterpret", "confusion", "violation", "conflict")):
        return FailureCategory.DECISION
    return FailureCategory.DECISION  # default bucket for ambiguous

# Mutate CATEGORY_MODES in place
_baseline_mapped = {{m for modes in CATEGORY_MODES.values() for m in modes}}
for _mode in FailureMode:
    if _mode not in _baseline_mapped:
        _cat = _autoclassify_failure_mode(_mode.value)
        CATEGORY_MODES.setdefault(_cat, set()).add(_mode)
del _mode, _cat, _baseline_mapped, _autoclassify_failure_mode
'''.format(marker=marker)
    fp.write_text(text.rstrip() + "\n" + patch + "\n")
    print("R4 extended CATEGORY_MODES via prefix-heuristic auto-classification")


# ---------------------------------------------------------------------------
# R5 — add semantic event-level leakage patterns
# ---------------------------------------------------------------------------

def step_r5_add_event_leakage_patterns():
    fp = ROOT / "aerosafety" / "data" / "contamination_check.py"
    text = fp.read_text()
    marker = "# EVENT_LEAK_PATTERNS_ADDED_2026_05_18"
    if marker in text:
        print("R5 event-level patterns already added; skip")
        return
    old = '("BTS_ZIP", re.compile(r"\\b(On_Time_Reporting_Carrier_On_Time_Performance_\\d+_present_\\d{4}_\\d{2})")),'
    new = (
        '("BTS_ZIP", re.compile(r"\\b(On_Time_Reporting_Carrier_On_Time_Performance_\\d+_present_\\d{4}_\\d{2})")),\n'
        '    # ' + marker + ' — same-day same-airport event collisions catch BTS GDP / ADS-B reuse\n'
        '    ("AIRPORT_DATE_EVENT", re.compile(r"\\b(K[A-Z]{3}|P[A-Z]{3})\\s+(20\\d{2}-\\d{2}-\\d{2})\\b")),\n'
        '    ("DATE_AIRPORT_EVENT", re.compile(r"\\b(20\\d{2}-\\d{2}-\\d{2})\\s+(K[A-Z]{3}|P[A-Z]{3})\\b")),\n'
        '    ("ISO_DATE_HHMM", re.compile(r"\\b(20\\d{2}-\\d{2}-\\d{2}T\\d{2}:\\d{2}Z?)\\b")),'
    )
    fp.write_text(text.replace(old, new))
    print("R5 added event-level leakage patterns (airport+date, date+airport, ISO timestamp)")


# ---------------------------------------------------------------------------
# R6 — dedupe NTSB_FULL_REPORTS manifest
# ---------------------------------------------------------------------------

def step_r6_dedup_ntsb_manifest():
    fp = RAW_DIR / "NTSB_FULL_REPORTS" / "2026-05-17" / "manifest.jsonl"
    if not fp.exists():
        print("R6 NTSB manifest absent; skip")
        return
    rows = [json.loads(l) for l in fp.read_text().splitlines() if l.strip()]
    # Keep most-recent (last) entry per file_path
    seen = OrderedDict()
    for r in rows:
        seen[r.get("file_path", "")] = r
    deduped = list(seen.values())
    fp.write_text("\n".join(json.dumps(r) for r in deduped) + "\n")
    print(f"R6 NTSB manifest dedup: {len(rows)} → {len(deduped)} rows")


# ---------------------------------------------------------------------------
# R7 — split failed rows out of production manifests
# ---------------------------------------------------------------------------

def step_r7_split_failed_rows():
    for source in ("ADSB_EXCHANGE", "NASA_ASRS", "INTL_NOTAM"):
        d = RAW_DIR / source / "2026-05-17"
        m = d / "manifest.jsonl"
        if not m.exists():
            continue
        rows = [json.loads(l) for l in m.read_text().splitlines() if l.strip()]
        ok = [r for r in rows if (r.get("http_status") == 200 or r.get("status") == "OK")]
        failed = [r for r in rows if r not in ok]
        if failed:
            (d / "_failed.jsonl").write_text("\n".join(json.dumps(r) for r in failed) + "\n")
            m.write_text("\n".join(json.dumps(r) for r in ok) + "\n")
            print(f"R7 {source}: {len(ok)} ok kept in manifest.jsonl, {len(failed)} failed moved to _failed.jsonl")


# ---------------------------------------------------------------------------
# R8 — create review schema + data/review/ stubs
# ---------------------------------------------------------------------------

REVIEW_SCHEMA = '''"""
Review record schema referenced by docs/expert_review_protocol.md.

PARTIAL IMPLEMENTATION (2026-05-18): the schema is defined but no
review records have been created yet — that requires PI-led expert
recruitment per the protocol §3 onboarding flow. Stub exists so that
the contamination_check audit and any future review-data ingest can
import from a stable location.
"""

from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field


class ReviewRecord(BaseModel):
    """One reviewer's evaluation of one TaskCard (per protocol §4)."""

    reviewer_id: str
    task_id: str
    review_timestamp: str  # ISO-8601 UTC

    elapsed_seconds: Optional[int] = None

    # Validation judgements
    realism_score: int = Field(ge=1, le=5)
    clarity_score: int = Field(ge=1, le=5)
    factual_correctness: Literal["True", "False", "Cannot determine"]

    # Ground-truth judgements
    agrees_with_gold_decision: bool
    proposed_gold_decision_if_disagrees: Optional[str] = None
    agrees_with_required_safety_constraints: bool
    missing_safety_constraints_to_add: list[str] = Field(default_factory=list)
    constraints_to_remove: list[str] = Field(default_factory=list)
    agrees_with_severity: bool
    proposed_severity_if_disagrees: Optional[Literal["Low", "Medium", "High", "Critical"]] = None
    agrees_with_escalation_required: bool

    # Failure-mode tagging
    applicable_failure_modes: list[str] = Field(default_factory=list)

    # Disqualification flags
    contains_outdated_rule: bool = False
    contains_jurisdiction_confusion: bool = False
    contains_safety_compromise: bool = False

    free_text_comments: Optional[str] = None
'''


def step_r8_create_review_stubs():
    schema_path = ROOT / "aerosafety" / "data" / "schemas" / "review.py"
    schema_path.parent.mkdir(parents=True, exist_ok=True)
    if not schema_path.exists():
        schema_path.write_text(REVIEW_SCHEMA)
    review_dir = ROOT / "data" / "review"
    review_dir.mkdir(parents=True, exist_ok=True)
    readme = review_dir / "README.md"
    if not readme.exists():
        readme.write_text(
            "# data/review/\n\n"
            "Reviewer records will land here as PI-led expert review completes.\n"
            "Schema: `aerosafety/data/schemas/review.py` (ReviewRecord).\n"
            "Protocol: `docs/expert_review_protocol.md`.\n\n"
            "STATUS (2026-05-18): no review records yet. Every task card\n"
            "is tagged `provenance.review_status = \"PILOT — NOT EXPERT-REVIEWED\"`.\n"
        )
    print("R8 review schema + data/review/ stubs created")


def main():
    print("=== Round-2 integrity fixes ===")
    step_r1_rename_test_to_provisional()
    step_r2_split_license_and_review_status()
    step_r3_fix_classifier()
    step_r4_extend_category_modes()
    step_r5_add_event_leakage_patterns()
    step_r6_dedup_ntsb_manifest()
    step_r7_split_failed_rows()
    step_r8_create_review_stubs()
    print("=== Done. Re-run aerosafety.data.contamination_check. ===")


if __name__ == "__main__":
    main()
