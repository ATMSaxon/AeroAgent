"""
Round-3 integrity fixes (2026-05-18) responding to GPT-5 codex round-3
re-audit. Round-2 fixed structural issues; round-3 attacks the semantic
honesty issues codex found AND audit-tool bugs that allowed them
through.

Audit-tool fixes (changes to contamination_check.py):
  T1  C8 substring bug: "EXPERT-REVIEWED" matches "NOT EXPERT-REVIEWED"
      → use word-boundary regex
  T2  C4 NTSB regex missed GAA* / WAA* / non-canonical prefixes → broaden
  T3  Add C9: duplicate failure_mode_labels within a card's list
  T4  Add C10: identical gold_decision across dev and (provisional_)test

Data fixes:
  D1  Reclassify cards as `hybrid` if they cite a real source AND have a
      generation_rule indicating a synthetic scenario layer. Codex
      identified 518 "real" cards with synthetic scenario decoration —
      these should be hybrid by definition.
  D2  Dedupe duplicate failure_mode_labels within each card's list
      (211 cards affected per codex).
  D3  For every set of cards with identical gold_decision in dev AND
      (provisional_)test, move ALL such cards to dev — eliminates
      answer leakage even when prompts differ.
  D4  Reclassify orphan-citing cards detected by the broadened C4:
      cards citing NTSB IDs not in local manifest → SYNTHETIC narrative.
  D5  Manifest cleanup pass 2: move ALL non-200 rows out of every
      production manifest into _failed.jsonl (NTSB still had 403/404,
      IEM had 429).

Authorization: team-lead 2026-05-18 in response to GPT-5 round-3 review.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = ROOT / "aerosafety" / "tasks"
RAW_DIR = ROOT / "data" / "raw"


def _walk():
    for fam_dir in sorted(TASKS_DIR.iterdir()):
        if not fam_dir.is_dir() or fam_dir.name.startswith("_"):
            continue
        for f in sorted((fam_dir / "taskcards").glob("*.jsonl")):
            yield fam_dir.name, f, [json.loads(l) for l in f.read_text().splitlines() if l.strip()]


def _save(p, rows):
    p.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n")


# ---------------------------------------------------------------------------
# T1 — fix C8 substring bug (use word boundary)
# T2 — broaden C4 NTSB regex to include GAA / WAA / other prefixes
# T3 — add C9 (duplicate failure_mode_labels within card)
# T4 — add C10 (duplicate gold_decision across splits)
# ---------------------------------------------------------------------------

def patch_contamination_check():
    fp = ROOT / "aerosafety" / "data" / "contamination_check.py"
    s = fp.read_text()

    # T1: C8 EXPERT-REVIEWED must NOT match "NOT EXPERT-REVIEWED"
    old_c8 = '''            if "EXPERT-REVIEWED" not in rs and "ADJUDICATED" not in rs:
                bad_split.append(f"{c['task_id']} in frozen test without expert review")'''
    new_c8 = '''            # Substring bug fix (round-3): "EXPERT-REVIEWED" appears inside
            # "NOT EXPERT-REVIEWED"; use word-boundary match to detect actual
            # expert review state.
            rs_norm = re.sub(r"NOT\\s+EXPERT-REVIEWED", "", rs)
            if "EXPERT-REVIEWED" not in rs_norm and "ADJUDICATED" not in rs_norm:
                bad_split.append(f"{c['task_id']} in frozen test without expert review")'''
    s = s.replace(old_c8, new_c8)

    # T2: broaden NTSB ID prefix list
    s = s.replace(
        '"((?:ANC|CEN|DCA|ERA|WPR)\\d{2}(?:F|L|M|W)?A\\d{2,4})"',
        '"((?:ANC|CEN|DCA|ERA|WPR|GAA|WAA|MIA|LAX|FTW|ATL|CHI|NYC|MKC|SEA)\\d{2}(?:F|L|M|W)?A\\d{2,4})"',
    )
    s = s.replace(
        '"((?:ANC|CEN|DCA|ERA|WPR)\\d{2}-\\d{4})"',
        '"((?:ANC|CEN|DCA|ERA|WPR|GAA|WAA|MIA|LAX|FTW|ATL|CHI|NYC|MKC|SEA)\\d{2}-\\d{4})"',
    )

    # T3 + T4: add C9 + C10 after C8 block
    # Find the print block to insert before it
    insert_marker = '    print("=" * 70)\n    print("Contamination audit report")'
    new_checks = '''    # C9 — duplicate failure_mode_labels within a single card's list
    dup_labels: list[str] = []
    for fam, c, f, i in cards:
        lbls = c.get("failure_mode_labels", []) or []
        if len(lbls) != len(set(lbls)):
            dups = [x for x in lbls if lbls.count(x) > 1]
            dup_labels.append(f"{c['task_id']} dup={sorted(set(dups))}")
    if dup_labels:
        failures.append(
            f"C9 duplicate failure_mode_labels within card: {len(dup_labels)} cards, "
            f"sample: {dup_labels[:5]}"
        )

    # C10 — identical gold_decision across dev and (provisional_)test
    by_gold: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for fam, c, f, i in cards:
        sp = c.get("split")
        if sp not in ("dev", "test", "provisional_test"):
            continue
        canon = "test" if sp in ("test", "provisional_test") else "dev"
        gold = (c.get("gold_decision") or "").strip()
        if len(gold) < 30:  # ignore trivial 1-word golds
            continue
        by_gold[gold][canon].append(c["task_id"])
    dup_gold: list[str] = []
    for gold, splits in by_gold.items():
        if "dev" in splits and "test" in splits:
            dup_gold.append(f"dev={splits['dev'][:2]} test={splits['test'][:2]} (gold {gold[:60]!r})")
    if dup_gold:
        failures.append(
            f"C10 identical gold_decision across dev and (provisional_)test: "
            f"{len(dup_gold)} duplicate gold groups, sample: {dup_gold[:5]}"
        )

''' + insert_marker
    s = s.replace(insert_marker, new_checks)

    fp.write_text(s)
    print("T1-T4 patched contamination_check.py (C8 word-bound, C4 prefixes, C9 dup-labels, C10 dup-gold)")


# ---------------------------------------------------------------------------
# D1 — reclassify "real + generation_rule" cards as hybrid
# D2 — dedupe failure_mode_labels within each card
# D3 — move dup-gold cards to dev to eliminate cross-split answer leakage
# D4 — reclassify orphans found by broadened C4
# ---------------------------------------------------------------------------

NTSB_BROAD = re.compile(
    r"(?<![A-Za-z0-9])((?:ANC|CEN|DCA|ERA|WPR|GAA|WAA|MIA|LAX|FTW|ATL|CHI|NYC|MKC|SEA)\d{2}(?:F|L|M|W)?A\d{2,4})(?![A-Za-z0-9])"
)


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


def step_d1_d4_d2():
    known = _load_known_ntsb()
    n_d1 = n_d2 = n_d4 = 0
    for fam, path, rows in _walk():
        changed = False
        for r in rows:
            prov = r.setdefault("provenance", {})

            # D2: dedupe failure_mode_labels
            lbls = r.get("failure_mode_labels", []) or []
            if len(lbls) != len(set(lbls)):
                seen = []
                for x in lbls:
                    if x not in seen:
                        seen.append(x)
                r["failure_mode_labels"] = seen
                n_d2 += 1
                changed = True

            # D4: orphan NTSB IDs in real cards (broadened detection)
            src = prov.get("source", "") or ""
            if r.get("provenance_class") in (None, "real") and "NTSB" in src.upper() and not src.upper().startswith("SYNTHETIC"):
                ids = set(NTSB_BROAD.findall(src))
                unresolved = ids - known
                if unresolved:
                    prov["source"] = (
                        "SYNTHETIC: NTSB-style narrative; original IDs "
                        f"{sorted(unresolved)} not in local manifest (broadened "
                        "C4 round-3 detection). Educational scenario only."
                    )
                    prov["generation_rule"] = (
                        "Synthesised NTSB-style narrative; unverifiable IDs "
                        "removed from real-citation claim."
                    )
                    r["provenance_class"] = "synthetic"
                    n_d4 += 1
                    changed = True

            # D1: if provenance_class=real but generation_rule is set, that's
            # the codex round-3 "scenario layer" indicator — reclassify as hybrid
            cls = r.get("provenance_class")
            gen = prov.get("generation_rule")
            if cls == "real" and gen:
                r["provenance_class"] = "hybrid"
                n_d1 += 1
                changed = True

        if changed:
            _save(path, rows)
    print(f"D1 reclassified {n_d1} real-with-generation_rule cards → hybrid")
    print(f"D2 deduped failure_mode_labels in {n_d2} cards")
    print(f"D4 reclassified {n_d4} broadened-orphan cards → synthetic")


def step_d3_dedup_gold():
    by_gold: dict[str, list[tuple[Path, dict]]] = defaultdict(list)
    files: dict[Path, list[dict]] = {}
    for fam, path, rows in _walk():
        files[path] = rows
        for r in rows:
            sp = r.get("split")
            if sp not in ("dev", "test", "provisional_test"):
                continue
            gold = (r.get("gold_decision") or "").strip()
            if len(gold) < 30:
                continue
            by_gold[gold].append((path, r))
    moved = 0
    for gold, lst in by_gold.items():
        splits = {r.get("split") for _, r in lst}
        # If duplicate gold appears across dev and provisional_test (or test):
        if "dev" in splits and (splits & {"test", "provisional_test"}):
            for _, r in lst:
                if r.get("split") in ("test", "provisional_test"):
                    r["split"] = "dev"
                    moved += 1
    for p, rows in files.items():
        _save(p, rows)
    print(f"D3 moved {moved} dup-gold test cards → dev (no more cross-split answer leakage)")


# ---------------------------------------------------------------------------
# D5 — manifest cleanup pass 2
# ---------------------------------------------------------------------------

def step_d5_manifest_cleanup():
    for source in ("NTSB_FULL_REPORTS", "IEM_METAR", "IEM_TAF", "FAA_CHART_SUPPL",
                   "ADSB_EXCHANGE", "BTS_ONTIME", "OR_LIBRARY", "FAA_SDR",
                   "NTSB_ACCIDENT_DB"):
        m = RAW_DIR / source / "2026-05-17" / "manifest.jsonl"
        if not m.exists():
            continue
        rows = [json.loads(l) for l in m.read_text().splitlines() if l.strip()]
        ok = [r for r in rows if r.get("http_status") in (200, None) and not r.get("error")]
        failed = [r for r in rows if r not in ok]
        if failed:
            failed_path = m.parent / "_failed.jsonl"
            existing = []
            if failed_path.exists():
                existing = [json.loads(l) for l in failed_path.read_text().splitlines() if l.strip()]
            failed_path.write_text("\n".join(json.dumps(r) for r in existing + failed) + "\n")
            m.write_text("\n".join(json.dumps(r) for r in ok) + "\n")
            print(f"D5 {source}: kept {len(ok)} OK, moved {len(failed)} failed to _failed.jsonl")


def main():
    print("=== Round-3 integrity fixes ===")
    patch_contamination_check()
    step_d1_d4_d2()
    step_d3_dedup_gold()
    step_d5_manifest_cleanup()
    print("=== Done. Re-run aerosafety.data.contamination_check. ===")


if __name__ == "__main__":
    main()
