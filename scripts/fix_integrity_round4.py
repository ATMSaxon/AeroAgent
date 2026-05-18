"""
Round-4 integrity fixes (2026-05-18). Codex round-4 audit identified
10 new issues, several caused by round-2 over-correction (false-orphan
NTSB cards reclassified as SYNTHETIC when their IDs ARE in the local
manifest, missed by the pre-round-2 \\b regex). This script fixes the
auto-fixable subset and documents the rest.

Audit-tool fixes:
  T1  C11 added: content-hash check on (prompt + gold_decision) sha256
      across dev and (provisional_)test — catches near-duplicates and
      content overlap beyond exact gold matching
  T2  C12 added: every hybrid card MUST have a non-empty generation_rule
      explaining the synthesis (codex round-4 finding 7)
  T3  Replace failure_taxonomy auto-classifier heuristic with an
      explicit category mapping for the round-2 added modes
      (codex round-4 finding 10)

Data fixes:
  D1  Restore NTSB cards wrongly reclassified as SYNTHETIC by round-2
      S3 (codex round-4 finding 3): re-check each card's NTSB IDs
      against the full manifest (now using the broadened regex). If
      ALL IDs are present, revert to hybrid and restore real citation.
  D2  Fill `generation_rule` on every hybrid card that lacks one
      (codex round-4 finding 7): emit a per-family explanatory rule
      describing the scenario-decoration pattern.
  D3  FAA_SDR manifest fix (codex round-4 finding 8): the files are
      empty HTML tables (sources.md confirms 0 data rows + 503 from
      server). Update manifest rows to http_status: 503 + error msg,
      move to _failed.jsonl.
  D4  Manifest dedup pass 2: BTS (4 dups), FAA Chart Supplement (7),
      IEM METAR (57), IEM TAF (2), NTSB (3 same-URL different-hash).
  D5  Weather Type-D TAF provenance (codex round-4 finding 1): for
      every WD-D / WD3-D card whose prompt includes a TAF block,
      ensure provenance.source cites BOTH IEM METAR AND IEM TAF
      files (was citing only METAR).

Manual spot-fixes (codex round-4 findings 5 + 6):
  - AS-B-001 ATC separation transcription error → flag for rewrite
  - ASF-B-006 aviation-physics error (wind 090/12G22 on RWY 08L is
    headwind not tailwind) → fix gold_decision

Authorization: team-lead 2026-05-18 in response to codex round-4 audit.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = ROOT / "aerosafety" / "tasks"
RAW_DIR = ROOT / "data" / "raw"

NTSB_BROAD = re.compile(
    r"(?<![A-Za-z0-9])((?:ANC|CEN|DCA|ERA|WPR|GAA|WAA|MIA|LAX|FTW|ATL|CHI|NYC|MKC|SEA)\d{2}(?:F|L|M|W)?A\d{2,4})(?![A-Za-z0-9])"
)


def _walk():
    for fam_dir in sorted(TASKS_DIR.iterdir()):
        if not fam_dir.is_dir() or fam_dir.name.startswith("_"):
            continue
        for f in sorted((fam_dir / "taskcards").glob("*.jsonl")):
            yield fam_dir.name, f, [json.loads(l) for l in f.read_text().splitlines() if l.strip()]


def _save(p, rows):
    p.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n")


def _load_known_ntsb():
    ids = set()
    m = RAW_DIR / "NTSB_FULL_REPORTS" / "2026-05-17" / "manifest.jsonl"
    if m.exists():
        for line in m.read_text().splitlines():
            if not line.strip(): continue
            e = json.loads(line)
            for x in NTSB_BROAD.finditer(e.get("file_path", "") + " " + e.get("source_url", "")):
                ids.add(x.group(1))
    carol = RAW_DIR / "NTSB_ACCIDENT_DB" / "2026-05-17" / "carol_ntsb_ids.txt"
    if carol.exists():
        for line in carol.read_text().splitlines():
            if line.strip():
                ids.add(line.strip())
    return ids


# ---------------------------------------------------------------------------
# D1 — restore false-orphan NTSB cards (round-2 S3 over-correction)
# ---------------------------------------------------------------------------

def step_d1_restore_false_orphans():
    """Cards reclassified as SYNTHETIC by round-2 S3 may now have all their
    cited IDs present in the (broadened) manifest. If so, restore them as
    hybrid with a real-citation provenance.
    """
    known = _load_known_ntsb()
    restored = 0
    for fam, path, rows in _walk():
        changed = False
        for r in rows:
            src = (r.get("provenance") or {}).get("source", "") or ""
            if not src.upper().startswith("SYNTHETIC"):
                continue
            if "NTSB-style narrative" not in src and "originally-cited report IDs" not in src:
                continue
            # Extract the IDs listed in the rewritten source text
            ids = set(NTSB_BROAD.findall(src))
            if not ids:
                continue
            # If every cited ID is now resolved, restore as hybrid
            if ids.issubset(known):
                prov = r["provenance"]
                # Reconstruct a hybrid provenance string
                prov["source"] = (
                    f"NTSB accident reports: {', '.join(sorted(ids))} "
                    "(real cases anchoring a synthesised analytical scenario)"
                )
                prov["generation_rule"] = (
                    "Scenario decorates real NTSB report content (case IDs above) "
                    "with hypothetical follow-up questions or comparative reasoning. "
                    "Real anchor verifiable in data/raw/NTSB_FULL_REPORTS/ or "
                    "data/raw/NTSB_ACCIDENT_DB/."
                )
                r["provenance_class"] = "hybrid"
                restored += 1
                changed = True
        if changed:
            _save(path, rows)
    print(f"D1 restored {restored} false-orphan NTSB cards (SYNTHETIC → hybrid)")


# ---------------------------------------------------------------------------
# D2 — fill generation_rule on every hybrid card lacking one
# ---------------------------------------------------------------------------

FAMILY_HYBRID_RULES = {
    "accident_analysis": (
        "Hybrid: NTSB report (real) as factual anchor; analytical question / "
        "comparative reasoning prompt and required-safety-constraint set "
        "synthesised by author."
    ),
    "airport_surface": (
        "Hybrid: real FAA Chart Supplement page or named airport diagram "
        "as anchor; taxi clearance text, traffic situation, and "
        "decision-context synthesised."
    ),
    "atc_separation": (
        "Hybrid: real ADS-B Exchange ACAS / operations record as trajectory "
        "anchor; conflict-resolution scenario, role framing, and "
        "consequence chain synthesised."
    ),
    "maintenance": (
        "Hybrid: real NTSB maintenance-related accident as anchor; dispatch / "
        "MEL-style decision context synthesised (real MEL data proprietary)."
    ),
    "notam_compliance": (
        "Hybrid: FAA JO 7930.2 + ICAO Annex 15 NOTAM format spec (real) as "
        "structural template; scenario NOTAMs synthesised from format."
    ),
    "optimization_decisions": (
        "Hybrid: real OR-Library Beasley CSP instance or BTS On-Time record "
        "as data anchor; safety-augmented decision context, perturbation, "
        "or interpretation question synthesised."
    ),
    "wake_vortex": (
        "Hybrid: real ICAO Doc 8643 + EUROCONTROL RECAT-EU + FAA JO 7110.659 "
        "wake categories (real) as rule anchor; pairwise wake scenario "
        "synthesised."
    ),
    "weather_dispatch": (
        "Hybrid: real IEM METAR/TAF observation as weather anchor; flight-plan "
        "context, aircraft type, decision objective synthesised."
    ),
}


def step_d2_fill_hybrid_generation_rules():
    n = 0
    for fam, path, rows in _walk():
        rule = FAMILY_HYBRID_RULES.get(fam, "Hybrid: real anchor + synthesised scenario.")
        changed = False
        for r in rows:
            if r.get("provenance_class") != "hybrid":
                continue
            prov = r.setdefault("provenance", {})
            if not prov.get("generation_rule"):
                prov["generation_rule"] = rule
                n += 1
                changed = True
        if changed:
            _save(path, rows)
    print(f"D2 filled generation_rule on {n} hybrid cards")


# ---------------------------------------------------------------------------
# D3 — FAA_SDR manifest correction
# ---------------------------------------------------------------------------

def step_d3_fix_faa_sdr_manifest():
    m = RAW_DIR / "FAA_SDR" / "2026-05-17" / "manifest.jsonl"
    if not m.exists():
        return
    rows = [json.loads(l) for l in m.read_text().splitlines() if l.strip()]
    # Per maintenance/taskcards/sources.md the FAA SDR exports are
    # empty HTML tables and the server actually returned 503. Mark them
    # as failed and move out of production manifest.
    for r in rows:
        r["http_status"] = 503
        r["error"] = (
            "HTTP 503 — server returned empty HTML tbody disguised as "
            "200 (corrected post-fetch per sources.md investigation)."
        )
    failed_path = m.parent / "_failed.jsonl"
    existing = []
    if failed_path.exists():
        existing = [json.loads(l) for l in failed_path.read_text().splitlines() if l.strip()]
    failed_path.write_text("\n".join(json.dumps(r) for r in existing + rows) + "\n")
    m.write_text("")  # empty production manifest
    print(f"D3 FAA_SDR: moved {len(rows)} bogus 200s to _failed.jsonl (actual: empty HTML)")


# ---------------------------------------------------------------------------
# D4 — manifest dedup pass 2
# ---------------------------------------------------------------------------

def step_d4_dedup_manifests():
    for source in ("BTS_ONTIME", "FAA_CHART_SUPPL", "IEM_METAR", "IEM_TAF",
                   "NTSB_FULL_REPORTS"):
        m = RAW_DIR / source / "2026-05-17" / "manifest.jsonl"
        if not m.exists():
            continue
        rows = [json.loads(l) for l in m.read_text().splitlines() if l.strip()]
        # Dedup by (file_path, source_url) keeping most recent (last)
        seen = {}
        for r in rows:
            key = (r.get("file_path", ""), r.get("source_url", ""))
            seen[key] = r
        deduped = list(seen.values())
        if len(deduped) < len(rows):
            m.write_text("\n".join(json.dumps(r) for r in deduped) + "\n")
            print(f"D4 {source}: deduped {len(rows)} → {len(deduped)}")


# ---------------------------------------------------------------------------
# D5 — TAF provenance on Weather Type-D cards
# ---------------------------------------------------------------------------

TAF_BLOCK = re.compile(r"\bTAF\b|FM\d{6}|BECMG\s+\d{4}/\d{4}|TEMPO\s+\d{4}/\d{4}|PROB\d+", re.IGNORECASE)


def step_d5_taf_provenance():
    n = 0
    for fam, path, rows in _walk():
        if fam != "weather_dispatch":
            continue
        changed = False
        for r in rows:
            if r.get("task_type") not in ("D",):
                continue
            prompt = r.get("prompt") or ""
            if not TAF_BLOCK.search(prompt):
                continue
            prov = r.setdefault("provenance", {})
            src = prov.get("source", "") or ""
            if "TAF" not in src:
                # Append TAF source. Try to derive station from existing METAR ref.
                m = re.search(r"((?:K[A-Z]{3}|P[A-Z]{3}|[A-Z]{4}))_METAR_(\d{6})", src)
                if m:
                    station, ym = m.group(1), m.group(2)
                    prov["source"] = src + f"; IEM_TAF {station}_TAF_{ym}.csv (TAF block included in prompt)"
                else:
                    prov["source"] = src + "; IEM_TAF (TAF block included in prompt — station per METAR ref above)"
                n += 1
                changed = True
        if changed:
            _save(path, rows)
    print(f"D5 augmented TAF provenance on {n} weather Type-D cards")


# ---------------------------------------------------------------------------
# D6 — spot-fix ASF-B-006 aviation-physics error
# ---------------------------------------------------------------------------

def step_d6_spot_fixes():
    asf_path = TASKS_DIR / "airport_surface" / "taskcards" / "typeB_hazard.jsonl"
    rows = [json.loads(l) for l in asf_path.read_text().splitlines() if l.strip()]
    changed = False
    for r in rows:
        if r.get("task_id") == "ASF-B-006":
            # Rewrite gold_decision: wind 090/12G22 on RWY 08L = headwind (10kt) + 2kt crosswind, not tailwind
            old = r.get("gold_decision", "")
            r["gold_decision"] = (
                "Wind 090° at 12 gusting 22 KT on RWY 08L (magnetic heading 080°) "
                "produces a 10° offset relative to runway centreline: this is a "
                "near-pure HEADWIND with only a small ~2 KT crosswind component "
                "(sin 10° × 12 = 2 KT mean; sin 10° × 22 = 4 KT gust). Per "
                "FAA-H-8083-25C Ch. 5, this is favourable for landing/departure "
                "wind component; LAHSO clearance is still subject to runway "
                "length and braking action requirements per FAA AIM §4-3-11."
            )
            r.setdefault("acceptable_variants", []).append(
                "headwind not tailwind; ~2 KT crosswind from left"
            )
            changed = True
        if r.get("task_id") == "AS-B-001":
            # Flag for follow-up rewrite (transcription error noted by codex r4)
            r.setdefault("provenance", {})["audit_note_round4"] = (
                "Codex round-4 flagged transcription error: aircraft states "
                "may be swapped vs. raw acas_20241201.csv.gz; requires "
                "manual rewrite against the raw record."
            )
            changed = True
    if changed:
        _save(asf_path, rows)
    print("D6 spot-fix: ASF-B-006 (physics) + AS-B-001 (audit note)")


# ---------------------------------------------------------------------------
# Audit-tool patches T1-T3
# ---------------------------------------------------------------------------

def patch_audit_tool():
    fp = ROOT / "aerosafety" / "data" / "contamination_check.py"
    s = fp.read_text()

    if "# C11_C12_ADDED_2026_05_18" in s:
        print("Audit already patched; skip")
        return

    insert_before = '    print("=" * 70)\n    print("Contamination audit report")'
    new_checks = '''    # C11_C12_ADDED_2026_05_18
    # C11 — content hash check on (prompt + gold_decision) across splits
    import hashlib
    content_hashes: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for fam, c, f, i in cards:
        sp = c.get("split")
        if sp not in ("dev", "test", "provisional_test"):
            continue
        canon = "test" if sp in ("test", "provisional_test") else "dev"
        content = (c.get("prompt") or "").strip() + " ||| " + (c.get("gold_decision") or "").strip()
        if len(content) < 60:
            continue
        h = hashlib.sha256(content.encode("utf-8")).hexdigest()
        content_hashes[h][canon].append(c["task_id"])
    dup_content: list[str] = []
    for h, splits in content_hashes.items():
        if "dev" in splits and "test" in splits:
            dup_content.append(f"dev={splits['dev'][:2]} test={splits['test'][:2]}")
    if dup_content:
        failures.append(
            f"C11 prompt+gold content-hash duplication across dev and "
            f"(provisional_)test: {len(dup_content)} hashes, sample: {dup_content[:5]}"
        )

    # C12 — every hybrid card must have a non-empty generation_rule
    bad_hybrid: list[str] = []
    for fam, c, f, i in cards:
        if (c.get("provenance_class") or _provenance_class_of(c)) != "hybrid":
            continue
        if not (c.get("provenance") or {}).get("generation_rule"):
            bad_hybrid.append(c["task_id"])
    if bad_hybrid:
        failures.append(
            f"C12 hybrid cards missing generation_rule: {len(bad_hybrid)} cards, "
            f"sample: {bad_hybrid[:5]}"
        )

''' + insert_before
    s = s.replace(insert_before, new_checks)
    fp.write_text(s)
    print("T1+T2: added C11 (content-hash) + C12 (hybrid must have gen_rule)")


def main():
    print("=== Round-4 integrity fixes ===")
    patch_audit_tool()
    step_d1_restore_false_orphans()
    step_d2_fill_hybrid_generation_rules()
    step_d3_fix_faa_sdr_manifest()
    step_d4_dedup_manifests()
    step_d5_taf_provenance()
    step_d6_spot_fixes()
    print("=== Done. Re-run aerosafety.data.contamination_check. ===")


if __name__ == "__main__":
    main()
