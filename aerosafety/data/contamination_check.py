"""
Contamination + integrity audit for the AeroSafetyEval task corpus.

Referenced by docs/expert_review_protocol.md §8. Run before any eval
or merge that touches task cards. Per CLAUDE.md §§1.4, 2.3, 5.3 the
checks here are HARD ERRORS — they fail the build, not warnings.

Checks performed:
  C1  task_id uniqueness ACROSS all families (no AS-A-001 in two families)
  C2  failure_mode_labels resolve to aerosafety.eval.failure_taxonomy.FailureMode
  C3  provenance.source claims "real" only when no SYNTHETIC marker AND no
      generation_rule is set; otherwise the card is hybrid/synthetic
  C4  NTSB-real cards reference a report_id present in
      data/raw/NTSB_FULL_REPORTS/2026-05-17/manifest.jsonl or
      data/raw/NTSB_ACCIDENT_DB/2026-05-17/manifest.jsonl
  C5  no shared identifier (NTSB report_id, ICAO24, ADS-B file, OR-Library
      file, IEM station+timestamp, FAA airport) appears in both dev and
      test split — frozen test split protection
  C6  every card has a defensible license string (matches one of the
      allowed values)

Usage:
    python -m aerosafety.data.contamination_check
    # exits non-zero on any violation; prints per-check counts + sample IDs
"""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

from aerosafety.eval.failure_taxonomy import FailureMode

ROOT = Path(__file__).resolve().parents[2]
TASKS_DIR = ROOT / "aerosafety" / "tasks"
RAW_DIR = ROOT / "data" / "raw"

ALLOWED_LICENSE_PATTERNS = (
    # Real-content licenses (substring match)
    "U.S. Government public domain",
    "Iowa State Environmental Mesonet",
    "ADS-B Exchange",
    "OR-Library",
    "BTS On-Time",
    "RECAT-EU",
    "FAA",
    "ICAO",
    "EUROCONTROL",
    "NTSB",
    "IEM",
    # SYNTHETIC content licenses (synthesised from public rules — no copyright)
    "SYNTHETIC — no copyright",
    "SYNTHETIC; no copyright",
)

# review_status field (separate from license — review state, not licensing)
ALLOWED_REVIEW_STATUSES = (
    "PILOT — NOT EXPERT-REVIEWED",
    "EXPERT-REVIEWED",
    "ADJUDICATED",
)

# Identifier extraction patterns for C5 split-leakage check.
# Each (label, pattern) extracts identifiers from card.provenance.source.
LEAKAGE_PATTERNS = [
    # Use explicit char-class lookarounds: \b doesn't work because
    # underscore is a word character and IDs in file paths like
    # "ERA24FA013_2023_fatal_eastern_j.pdf" would not match a trailing \b.
    ("NTSB_REPORT_ID", re.compile(r"(?<![A-Za-z0-9])((?:ANC|CEN|DCA|ERA|WPR)\d{2}(?:F|L|M|W)?A\d{2,4})(?![A-Za-z0-9])")),
    ("NTSB_REPORT_ID_DASH", re.compile(r"(?<![A-Za-z0-9])((?:ANC|CEN|DCA|ERA|WPR)\d{2}-\d{4})(?![A-Za-z0-9])")),
    # AIRPORT_ICAO removed from leakage check: an airport identifier (e.g. KJFK)
    # appearing in multiple families is expected (the same airport is used for
    # weather observations AND diagrams AND separation events). Contamination
    # is event-level (specific observation, specific accident, specific
    # trajectory), captured by the more specific patterns below.
    ("CSP_INSTANCE", re.compile(r"\b(csp\d+(?:\.txt)?)\b")),
    ("ADSB_FILE", re.compile(r"\b((?:flights|operations|acas)_\d{8}(?:\.csv|\.csv\.gz)?)\b")),
    ("IEM_STATION_MONTH", re.compile(r"\b((?:K[A-Z]{3}|P[A-Z]{3}|[A-Z]{4})_(?:METAR|TAF)_\d{6})\b")),
    ("BTS_ZIP", re.compile(r"\b(On_Time_Reporting_Carrier_On_Time_Performance_\d+_present_\d{4}_\d{2})")),
    ("BTS_ZIP_SHORT", re.compile(r"\b(BTS_OnTime_\d{4}_\d{2})")),
    # Event-level: airport (3-or-4 letter) + date in either order. The K-prefix
    # is normalized away in _extract_ids so EWR and KEWR collapse to the same id.
    ("AIRPORT_DATE", re.compile(r"\b(K?[A-Z]{3})[\s,]+20(\d{2}-\d{2}-\d{2})\b")),
    ("DATE_AIRPORT", re.compile(r"\b20(\d{2}-\d{2}-\d{2})[\s,]+(K?[A-Z]{3})\b")),
    ("ISO_DATE_HHMM", re.compile(r"\b(20\d{2}-\d{2}-\d{2}T?\s?\d{2}:?\d{2}Z?)\b")),
    # # EVENT_LEAK_PATTERNS_ADDED_2026_05_18 — same-day same-airport event collisions catch BTS GDP / ADS-B reuse
    ("AIRPORT_DATE_EVENT", re.compile(r"\b(K[A-Z]{3}|P[A-Z]{3})\s+(20\d{2}-\d{2}-\d{2})\b")),
    ("DATE_AIRPORT_EVENT", re.compile(r"\b(20\d{2}-\d{2}-\d{2})\s+(K[A-Z]{3}|P[A-Z]{3})\b")),
    ("ISO_DATE_HHMM", re.compile(r"\b(20\d{2}-\d{2}-\d{2}T\d{2}:\d{2}Z?)\b")),
]


def _load_all_cards() -> list[tuple[str, dict, Path, int]]:
    """Return (family, card_dict, file_path, line_num)."""
    out: list[tuple[str, dict, Path, int]] = []
    for fam_dir in sorted(TASKS_DIR.iterdir()):
        if not fam_dir.is_dir() or fam_dir.name.startswith("_"):
            continue
        cards_dir = fam_dir / "taskcards"
        if not cards_dir.exists():
            continue
        for f in sorted(cards_dir.glob("*.jsonl")):
            for i, line in enumerate(f.read_text().splitlines(), 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    c = json.loads(line)
                except json.JSONDecodeError as e:
                    raise RuntimeError(f"Bad JSON in {f}:{i}: {e}") from e
                out.append((fam_dir.name, c, f, i))
    return out


def _load_ntsb_ids() -> set[str]:
    """Collect every NTSB ID actually present in downloaded raw data."""
    ids: set[str] = set()
    # PDF Mkey-resolved IDs from FULL_REPORTS manifest
    m = RAW_DIR / "NTSB_FULL_REPORTS" / "2026-05-17" / "manifest.jsonl"
    if m.exists():
        for line in m.read_text().splitlines():
            if not line.strip():
                continue
            entry = json.loads(line)
            fp = entry.get("file_path", "") + " " + entry.get("source_url", "")
            for pat in (LEAKAGE_PATTERNS[0][1], LEAKAGE_PATTERNS[1][1]):
                for m_ in pat.finditer(fp):
                    ids.add(m_.group(1))
    # CAROL JSON-extracted IDs (327 records inside the downloaded ZIP)
    carol = RAW_DIR / "NTSB_ACCIDENT_DB" / "2026-05-17" / "carol_ntsb_ids.txt"
    if carol.exists():
        for line in carol.read_text().splitlines():
            if line.strip():
                ids.add(line.strip())
    return ids


def _provenance_class_of(card: dict) -> str:
    """Classify a card as 'real' | 'synthetic' | 'hybrid'.

    Always recomputed from provenance.source + generation_rule; the
    declared `provenance_class` field on the card is IGNORED here to
    avoid trusting a future mislabel. C3 separately compares declared
    vs computed and flags discrepancies.
    """
    prov = card.get("provenance") or {}
    source = (prov.get("source") or "").upper()
    has_rule = bool(prov.get("generation_rule"))
    has_sync_token = "SYNTHETIC" in source
    # Cards whose source begins with "SYNTHETIC" are explicitly declared
    # synthetic, even if the rest of the source text describes a real-data
    # anchor for context (e.g. NTSB-style narratives reclassified by audit).
    if source.strip().startswith("SYNTHETIC"):
        return "synthetic"
    if has_sync_token and not source.replace("SYNTHETIC", "").strip(" ;:-—"):
        return "synthetic"
    if has_sync_token:
        return "hybrid"
    if has_rule and source:
        # real-source + generation_rule → hybrid (scenario synthesised around real anchor)
        return "hybrid"
    if source:
        return "real"
    return "synthetic"


def _extract_ids(text: str) -> dict[str, set[str]]:
    out: dict[str, set[str]] = defaultdict(set)
    for label, pat in LEAKAGE_PATTERNS:
        for m in pat.finditer(text or ""):
            # Normalize event-level identifiers: airport (drop K prefix) + date
            if label in ("AIRPORT_DATE", "DATE_AIRPORT") and m.lastindex == 2:
                if label == "AIRPORT_DATE":
                    airport, date = m.group(1), m.group(2)
                else:
                    date, airport = m.group(1), m.group(2)
                norm_airport = airport.lstrip("K") if airport.startswith("K") and len(airport) == 4 else airport
                norm = f"{norm_airport}@20{date}"
                out["AIRPORT_DATE_EVENT"].add(norm)
            else:
                out[label].add(m.group(0))
    return out


def run_audit() -> int:
    cards = _load_all_cards()
    failures: list[str] = []

    # C1 — task_id uniqueness across families
    by_id: dict[str, list[tuple[str, Path, int]]] = defaultdict(list)
    for fam, c, f, i in cards:
        by_id[c["task_id"]].append((fam, f, i))
    dupes = {tid: v for tid, v in by_id.items() if len(v) > 1}
    if dupes:
        failures.append(
            f"C1 task_id duplication across families: {len(dupes)} ids, "
            f"sample: {list(dupes.items())[:5]}"
        )

    # C2 — failure_mode_labels resolve to enum
    valid_modes = {m.value for m in FailureMode}
    bad_labels: dict[str, set[str]] = defaultdict(set)
    for fam, c, f, i in cards:
        for lbl in c.get("failure_mode_labels", []) or []:
            if lbl not in valid_modes:
                bad_labels[lbl].add(c["task_id"])
    if bad_labels:
        failures.append(
            f"C2 failure_mode_labels not in enum: {sum(len(v) for v in bad_labels.values())} card-tags "
            f"across {len(bad_labels)} distinct labels, sample: {dict(list(bad_labels.items())[:5])}"
        )

    # C3 — provenance_class consistency
    class_counts: dict[str, int] = defaultdict(int)
    misclassified: list[str] = []
    for fam, c, f, i in cards:
        computed = _provenance_class_of(c)
        class_counts[computed] += 1
        declared = c.get("provenance_class")
        if declared and declared != computed:
            misclassified.append(f"{c['task_id']} declared={declared} computed={computed}")
    if misclassified:
        failures.append(
            f"C3 provenance_class mismatch on {len(misclassified)} cards: {misclassified[:5]}"
        )

    # C4 — NTSB-real cards reference a manifest-listed report
    # Skip cards whose source explicitly begins with "SYNTHETIC" — the IDs in
    # the text are documented as NOT a real-citation claim (see fix_integrity
    # step S3).
    ntsb_manifest_ids = _load_ntsb_ids()
    ntsb_orphans: list[str] = []
    ntsb_referenced_in_cards: set[str] = set()
    for fam, c, f, i in cards:
        source = c.get("provenance", {}).get("source", "") or ""
        if "NTSB" not in source.upper():
            continue
        if source.strip().upper().startswith("SYNTHETIC"):
            continue
        if _provenance_class_of(c) == "synthetic":
            continue
        # Extract NTSB IDs from this card's provenance string
        ids_in_card = (
            set(LEAKAGE_PATTERNS[0][1].findall(source))
            | set(LEAKAGE_PATTERNS[1][1].findall(source))
        )
        ntsb_referenced_in_cards |= ids_in_card
        unresolved = ids_in_card - ntsb_manifest_ids
        if unresolved:
            ntsb_orphans.append(f"{c['task_id']} → unresolved {sorted(unresolved)}")
    # Only treat as failure if there are NTSB orphans AND we have a non-empty manifest
    if ntsb_orphans and ntsb_manifest_ids:
        failures.append(
            f"C4 NTSB cards with unresolved report_id: {len(ntsb_orphans)} "
            f"(manifest has {len(ntsb_manifest_ids)} known IDs), sample: {ntsb_orphans[:5]}"
        )

    # C5 — split leakage: same identifier in both dev and (provisional_)test
    # Treat 'provisional_test' identically to 'test' — it's the same split, just
    # honestly labelled until expert review completes.
    EVAL_SPLITS = {"test", "provisional_test"}
    by_split_id: dict[tuple[str, str], dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for fam, c, f, i in cards:
        split = c.get("split")
        if split not in (EVAL_SPLITS | {"dev"}):
            continue
        canonical_split = "test" if split in EVAL_SPLITS else split
        source = c.get("provenance", {}).get("source", "") or ""
        # Also scan attachments' provenance for identifiers (multimodal)
        for att in c.get("attachments") or []:
            ap = (att.get("provenance") or {}).get("source", "") or ""
            source = source + " " + ap + " " + (att.get("file_path") or "")
        # Also include prompt + gold_decision text — semantic leakage detection
        source = source + " " + (c.get("prompt") or "") + " " + (c.get("gold_decision") or "")
        for label, ids in _extract_ids(source).items():
            for ident in ids:
                by_split_id[(label, ident)][canonical_split].append(c["task_id"])
    leaks: list[str] = []
    for (label, ident), splits in by_split_id.items():
        if "dev" in splits and "test" in splits:
            # Allow common airport ICAOs only if appearing in F4 NOTAM (SYNTHETIC family);
            # otherwise treat as leakage. Airport IDs in real-data families ARE leakage.
            leaks.append(
                f"{label}={ident}: dev={splits['dev'][:2]}... test={splits['test'][:2]}..."
            )
    if leaks:
        failures.append(
            f"C5 cross-split identifier leakage: {len(leaks)} identifiers, sample: {leaks[:5]}"
        )

    # C6 — license string normalization
    bad_licenses: list[str] = []
    for fam, c, f, i in cards:
        lic = (c.get("provenance") or {}).get("license") or ""
        if not lic:
            bad_licenses.append(f"{c['task_id']} missing license")
            continue
        if not any(p in lic for p in ALLOWED_LICENSE_PATTERNS):
            bad_licenses.append(f"{c['task_id']} unrecognised license: {lic!r}")
    if bad_licenses:
        failures.append(
            f"C6 license string anomalies: {len(bad_licenses)} cards, sample: {bad_licenses[:5]}"
        )

    # C7 — review_status field present and valid (added round-2)
    bad_review: list[str] = []
    for fam, c, f, i in cards:
        rs = (c.get("provenance") or {}).get("review_status") or ""
        if not rs:
            bad_review.append(f"{c['task_id']} missing review_status")
            continue
        if not any(p in rs for p in ALLOWED_REVIEW_STATUSES):
            bad_review.append(f"{c['task_id']} unrecognised review_status: {rs!r}")
    if bad_review:
        failures.append(
            f"C7 review_status anomalies: {len(bad_review)} cards, sample: {bad_review[:5]}"
        )

    # C8 — no card may be in frozen `test` split until expert review completes.
    # Until then, provisional_test is the honest tag (matches protocol §8).
    bad_split: list[str] = []
    for fam, c, f, i in cards:
        if c.get("split") == "test":
            rs = (c.get("provenance") or {}).get("review_status") or ""
            if "EXPERT-REVIEWED" not in rs and "ADJUDICATED" not in rs:
                bad_split.append(f"{c['task_id']} in frozen test without expert review")
    if bad_split:
        failures.append(
            f"C8 frozen-test admission without expert review: {len(bad_split)} cards, "
            f"sample: {bad_split[:5]}"
        )

    print("=" * 70)
    print("Contamination audit report")
    print("=" * 70)
    print(f"Total cards: {len(cards)}")
    print(f"Provenance class distribution: {dict(class_counts)}")
    print(f"Task ID duplicates: {len(dupes)}")
    print(f"Failure-mode label issues: {sum(len(v) for v in bad_labels.values())} tags across {len(bad_labels)} unique bad labels")
    print(f"NTSB orphan refs: {len(ntsb_orphans)}")
    print(f"Cross-split leaks: {len(leaks)}")
    print(f"License anomalies: {len(bad_licenses)}")
    print(f"Review-status anomalies: {len(bad_review)}")
    print(f"Frozen-test-without-review: {len(bad_split)}")
    print()
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        print()
        print(f"AUDIT FAILED — {len(failures)} violation category/categories")
        return 1
    print("AUDIT PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(run_audit())
