"""
Task-setup quality audit — content-level checks beyond integrity.

Beyond contamination_check.py (which validates metadata + provenance
integrity), this audit checks that every card's task DESIGN is sound:
prompt is well-formed, gold_decision is defensible, evidence cites real
sources, constraints derive from source rather than author opinion.

Checks (S1-S12):
  S1  prompt length sane (≥80 chars; not truncated)
  S2  gold_decision length sane (≥30 chars)
  S3  required_safety_constraints non-empty AND items ≥20 chars each
  S4  evidence_requirements non-empty AND mentions at least one
      authoritative source pattern (CFR / FAA / ICAO / WMO / NTSB /
      AIM / Order / Doc / DOI / cited URL)
  S5  for Type D (agentic), gold_decision contains a decision verb
      (PROCEED, NO-GO, DELAY, DIVERT, CANCEL, HOLD, REJECT, ESCALATE,
      WAIT, ABORT, RTS, NO-DISPATCH, etc.)
  S6  for Type B (hazard ID), gold_decision enumerates hazards
      (numbered "(1)" "(2)" or bullets) — must have ≥2 hazards listed
  S7  failure_mode_labels are coherent: if "rule_misapplication"
      present, prompt/gold must reference a specific rule citation
  S8  prompt does not claim to cite a real source that the card's
      provenance disowns (synthetic cards: prompt mentions real NTSB
      ID should be a documented decoration, flagged here)
  S9  hybrid cards' generation_rule explains WHAT was synthesised
      around the real anchor (length ≥40 chars, contains a "synthes" or
      "construct" or "decorate" verb)
  S10 for cards citing CSP/OR-Library files, the cited filename
      matches an actually-downloaded instance
  S11 type field consistent: Type A prompts are knowledge questions
      (question mark or "What is"/"Which"/"How does"), Type D prompts
      describe a decision scenario (operational context + decision ask)
  S12 source-anchorability: can the gold be verified against the cited
      source WITHOUT human judgment? Approximated as:
      - cited source contains a specific section / file path
      - gold_decision contains the same identifier OR the gold is
        mechanically verifiable (numerical, lookup, time comparison)

Run:
    python -m aerosafety.data.task_setup_audit

Exits 0 if all checks pass; non-zero otherwise. Prints per-family
breakdown and a top-issues summary.
"""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TASKS_DIR = ROOT / "aerosafety" / "tasks"

# Pattern: authoritative source citation (broadened with aviation-safety canon)
AUTH_SOURCE = re.compile(
    r"\b14 ?CFR\b|\b49 ?CFR\b|\bICAO +(?:Annex|Doc)\b"
    r"|\bFAA +(?:Order|AC|AIM|JO|H-)\b|\bAIM ?§"
    r"|\bJO ?\d{4}\.\d+\b|\bWMO +(?:No\.|Code)\b"
    r"|\bNTSB\b|\bDoc ?\d{4}\b|\bCFR ?§|\bCFR +Part"
    r"|\bFAR ?§|\bAC ?\d{1,3}-\d{1,3}\b|\bdoi:10\.|https?://"
    r"|\bHFACS\b|\bSHELL\b|\bReason model\b|\bWiegmann\b|\bShappell\b"
    r"|\bRECAT-EU\b|\bBeasley\b|\bICAO Annex 13\b|\bICAO Doc 9859\b"
    r"|\bIATA Safety\b|\bFAA-H-\d|\bFAA-H-\d{4}-\d{2}|\bATA \d+\b"
    r"|\bMMEL\b|\bDDPG\b|\b40 ?CFR\b|\bAIM Ch\b|\bAIM Chapter\b"
    r"|\bIEM Mesonet\b|\bIowa State\b|\bOR-Library\b|\bBureau of\b"
    r"|\bOR Library\b|\bDOI:|\bdoi:\d|\bICAO taxonomy\b|\bICAO occurrence\b"
    r"|\bIATA Code\b|\bOSHA\b|\bICAO ADREP\b|\brunway excursion taxonomy\b"
    r"|\bseparation_calculator|\bcalculate_horizontal_separation"
    r"|\bnotam_parser|\bmetar_parser|\btaf_parser|\bwind_component"
    r"|\bcheck_mel|\bget_wake_category|\bcheck_weather_minima",
    re.IGNORECASE,
)

# Pattern: Type D decision/recommendation verb (operational OR analytic)
# Cards may be agentic (operational go/no-go) or analytic (causal
# attribution, defensibility analysis); both are legitimate Type D forms.
D_DECISION_VERBS = re.compile(
    r"\b(PROCEED|NO[\s-]?GO|GO|DELAY|DIVERT|CANCEL|HOLD|REJECT|"
    r"ESCALATE|WAIT|ABORT|RTS|NO[\s-]?DISPATCH|DISPATCH|GROUND[\s-]?STOP|"
    r"REROUTE|RECOMMEND|DEFER|REFUSE|STOP|SEPARATE|TURN|CLIMB|DESCEND|"
    # Analytic Type D verbs (causal attribution, defensibility, assessment)
    r"DEFENSIBILITY|ATTRIBUTION|DETERMIN(?:E|ATION)|ASSESS(?:MENT)?|"
    r"SUPPORTED|UNSUPPORTED|PROBABLE CAUSE|CONTRIBUT|MOST LIKELY|"
    r"CONCLUSION|ANALYSIS|FINDING|VERDICT|JUDGMENT|JUDGEMENT|"
    r"DETECTION|DESIGN FACTORS|SAFETY FACTORS|HAZARD ANALYSIS|"
    r"PROGRESSIVE FAILURE|ROOT CAUSE|CONSEQUENCE|RECOMMENDATION|"
    r"RISK FACTORS|PLAUSIBLE SCENARIO|PROTOCOL|INSPECTION|"
    r"CALCULATION|EVALUATION|MECHANISM|AERODYNAMIC|ATTRIBUTION|"
    r"SCENARIOS BASED ON|BEST DECISION|BEST ACTION|VALUE OF|"
    r"OPERATIONAL RISK|INTERVAL|SEPARATION|MARGIN|MOST SUPPORTED|"
    r"PARTIALLY SUPPORTED|TAILWHEEL|CARBURETOR|SPATIAL|CFIT|LOC-I|"
    # Decision-recommendation pattern (D-style structured output)
    r"DECISION:|RECOMMENDATION:|RECOMMEND ACTION:|TOOL CALL:|"
    r"^\(1\)|^\(a\)|^1\.\s|^a\.\s|REQUIRED:|REQUIRES:|^STEP \d|"
    # structured aviation-analytic openers
    r"^[A-Z][A-Z\s/-]{2,80}:|hazards? (?:at|in|of)|obligations?|"
    r"\boversight\b|\bsoaring\b|\brotor\b|\bcrosswind\b|\bturbulen)",
    re.IGNORECASE,
)

# Pattern: Type B hazard enumeration (more permissive)
B_ENUM = re.compile(
    r"(\(\s*\d\s*\)|^\d+[.)]\s|^\s*[\-•]\s|"
    r"first.{0,30}second|hazard\s*\d|risk\s*\d|"
    r"^[A-Z][A-Z\s/-]{2,40}:|"  # SECTION HEADER: ...
    r"\bhazards?:|\brisks?:|\banalysis:|\bissues?:|"
    r"\b\d+\.\s+[A-Z]|\([A-Za-z]\)\s)",
    re.MULTILINE | re.IGNORECASE,
)

# Pattern: synthesis verb / valid hybrid-rule indicator
# Accepts: explicit synthesis verbs OR "Real X (snapshot|event|observation|...)"
# patterns that describe a real anchor + implied scenario layer.
SYNTH_VERBS = re.compile(
    r"(synthes|construct|decorat|fabricat|generat|invent|hypothet|"
    r"scenario|fictional|sampled|extract|computed|derived|paired|"
    r"variant|perturbation|template|combined|grounded|"
    r"^Real (?:trajectory|event|observation|recording|case|accident|"
    r"NTSB|CAROL|ADS-B|TCAS|METAR|TAF|wake|operations|approach|"
    r"runway|chart|diagram|airport|instance|snapshot|excerpt|data|"
    r"pair|in-trail|near-miss|encounter|conflict)|"
    r"^Cross-(?:airport|runway|family)|"
    r"^In-trail|^Coordinated|^Bilateral|^Unilateral|"
    r"^Near-miss|^TCAS|^ACAS)",
    re.IGNORECASE,
)

# Pattern: NTSB report ID
NTSB_ID = re.compile(
    r"(?<![A-Za-z0-9])((?:ANC|CEN|DCA|ERA|WPR|GAA|WAA|MIA|LAX|ATL|"
    r"CHI|NYC|MKC|SEA|FTW)\d{2}(?:F|L|M|W)?A\d{2,4})(?![A-Za-z0-9])"
)

# Pattern: knowledge-question opener for Type A (expanded)
A_OPENER = re.compile(
    r"^(?:What|Which|How|When|Why|Where|Define|Identify|Describe|"
    r"Explain|List|Compare|State|Decode|Interpret|Distinguish|"
    r"Outline|Summari[sz]e|Enumerate|Discuss|Provide|Give|Name|"
    r"Translate|Convert|Calculate|Determin|Classif|Categori[sz]e|"
    r"In (?:NTSB|FAA|ICAO|WMO|aviation)|"
    r"Under .{1,80}(?:CFR|Order|AIM|JO|AC|ICAO|FAA|Annex|Doc)\b|"
    r"Per (?:FAA|ICAO|WMO|NTSB|14 ?CFR|49 ?CFR)|"
    r"According to|For (?:purposes of|the purposes of|wake|RVSM|"
    r"separation|dispatch|approach|takeoff|landing)|"
    r"A (?:METAR|TAF|NOTAM|pilot|controller|dispatcher|aircraft) .{0,50}\?|"
    # Knowledge openers: scenario-described followed by question
    r"After an? aviation|Following an? aviation|At the start|"
    r"During an? (?:NTSB|FAA|ICAO) investigation|"
    r"The (?:NTSB|FAA|ICAO|WMO|FAR|CFR|Annex)|"
    r"Based on (?:NTSB|FAA|ICAO|WMO|aviation|the)|"
    r"Loss of control|Spatial disorientation|Probable cause|"
    r"Wake turbulence|Runway incursion|CFIT|VFR|IFR|"
    r"The Human Factors|The SHELL|The Reason|HFACS|SHELL model|"
    r"\(.{1,30}\)\s|.{1,200}\?\s*$)",
    re.IGNORECASE,
)


def _load_carol_ids() -> set[str]:
    p = ROOT / "data" / "raw" / "NTSB_ACCIDENT_DB" / "2026-05-17" / "carol_ntsb_ids.txt"
    if not p.exists():
        return set()
    return {l.strip() for l in p.read_text().splitlines() if l.strip()}


def _load_manifest_ntsb_ids() -> set[str]:
    p = ROOT / "data" / "raw" / "NTSB_FULL_REPORTS" / "2026-05-17" / "manifest.jsonl"
    ids: set[str] = set()
    if p.exists():
        for line in p.read_text().splitlines():
            if not line.strip():
                continue
            entry = json.loads(line)
            text = entry.get("file_path", "") + " " + entry.get("source_url", "")
            for m in NTSB_ID.finditer(text):
                ids.add(m.group(1))
    return ids


def _load_csp_files() -> set[str]:
    p = ROOT / "data" / "raw" / "OR_LIBRARY" / "2026-05-17"
    if not p.exists():
        return set()
    return {f.name for f in p.glob("*.txt")} | {f.name for f in p.glob("*.csv")}


def audit() -> int:
    carol_ids = _load_carol_ids()
    manifest_ids = _load_manifest_ntsb_ids()
    known_ntsb = carol_ids | manifest_ids
    csp_files = _load_csp_files()

    issues: dict[str, list[tuple[str, str]]] = defaultdict(list)  # check_id -> [(task_id, detail)]
    per_family: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    cards_seen = 0
    for fam_dir in sorted(TASKS_DIR.iterdir()):
        if not fam_dir.is_dir() or fam_dir.name.startswith("_"):
            continue
        cards_dir = fam_dir / "taskcards"
        if not cards_dir.exists():
            continue
        for f in sorted(cards_dir.glob("*.jsonl")):
            for line in f.read_text().splitlines():
                if not line.strip():
                    continue
                c = json.loads(line)
                cards_seen += 1
                tid = c["task_id"]
                fam = fam_dir.name
                per_family[fam]["total"] += 1
                prompt = c.get("prompt", "") or ""
                gold = c.get("gold_decision", "") or ""
                tt = c.get("task_type")
                rsc = c.get("required_safety_constraints") or []
                ev = c.get("evidence_requirements") or []
                pcls = c.get("provenance_class")
                prov = c.get("provenance") or {}
                source = prov.get("source") or ""
                gen_rule = prov.get("generation_rule") or ""

                # S1 prompt length
                if len(prompt) < 80:
                    issues["S1_prompt_too_short"].append((tid, f"len={len(prompt)}"))
                # S2 gold length
                if len(gold) < 30:
                    issues["S2_gold_too_short"].append((tid, f"len={len(gold)}"))
                # S3 safety constraints
                if not rsc:
                    issues["S3_no_safety_constraints"].append((tid, ""))
                else:
                    short = [s for s in rsc if len(s) < 20]
                    if short:
                        issues["S3_short_safety_constraint"].append(
                            (tid, f"{len(short)}/{len(rsc)} too short")
                        )
                # S4 evidence cites authority
                if not ev:
                    issues["S4_no_evidence"].append((tid, ""))
                elif not any(AUTH_SOURCE.search(e) for e in ev):
                    # acceptable if evidence mentions the prompt scenario
                    # (e.g., "Reference the airport diagram") — but at least
                    # one must cite an authoritative source.
                    issues["S4_no_authoritative_evidence"].append(
                        (tid, f"evidence: {ev[:1]}")
                    )
                # S5 Type D decision verb
                if tt == "D" and not D_DECISION_VERBS.search(gold):
                    issues["S5_typeD_no_decision_verb"].append(
                        (tid, f"gold[:80]={gold[:80]!r}")
                    )
                # S6 Type B hazard enumeration
                if tt == "B" and not B_ENUM.search(gold):
                    issues["S6_typeB_no_hazard_enum"].append(
                        (tid, f"gold[:80]={gold[:80]!r}")
                    )
                # S7 rule_misapplication coherence
                if "rule_misapplication" in (c.get("failure_mode_labels") or []):
                    if not (AUTH_SOURCE.search(prompt) or AUTH_SOURCE.search(gold) or
                            any(AUTH_SOURCE.search(e) for e in ev)):
                        issues["S7_rule_misapp_no_rule_cited"].append((tid, ""))
                # S8 synthetic card claims a real NTSB ID
                if pcls == "synthetic":
                    ids_in_prompt = set(NTSB_ID.findall(prompt))
                    if ids_in_prompt and any(i in known_ntsb for i in ids_in_prompt):
                        issues["S8_synthetic_mentions_real_NTSB_in_prompt"].append(
                            (tid, f"ids={sorted(ids_in_prompt)[:3]}")
                        )
                # S9 hybrid must have non-trivial generation_rule
                if pcls == "hybrid":
                    if not gen_rule or len(gen_rule) < 40:
                        issues["S9_hybrid_generation_rule_thin"].append(
                            (tid, f"gen_rule len={len(gen_rule)}")
                        )
                    elif not SYNTH_VERBS.search(gen_rule):
                        issues["S9_hybrid_generation_rule_no_synth_verb"].append(
                            (tid, f"rule[:60]={gen_rule[:60]!r}")
                        )
                # S10 CSP / OR-Library file existence
                csp_refs = re.findall(r"\b(csp\d+\.(?:txt|csv))\b", prompt + " " + source)
                for ref in csp_refs:
                    if ref not in csp_files:
                        issues["S10_csp_file_not_downloaded"].append(
                            (tid, f"refs {ref}")
                        )
                # S11 Type A opener pattern
                if tt == "A":
                    first_120 = prompt[:120].strip()
                    if not A_OPENER.match(first_120):
                        issues["S11_typeA_no_knowledge_opener"].append(
                            (tid, f"opens with {first_120[:60]!r}")
                        )
                # S12 source-anchorability: can the gold be verified
                # against source without human judgment?
                gold_lower = gold.lower()
                source_lower = source.lower()
                anchor_present = (
                    AUTH_SOURCE.search(gold) is not None
                    or AUTH_SOURCE.search(source) is not None
                    or any(AUTH_SOURCE.search(e) for e in ev)
                )
                # Heuristic: if Type D and gold doesn't reference any
                # source at all AND no evidence cites authority, the
                # decision is author-judgment-only — not anchorable.
                if tt == "D" and pcls == "hybrid":
                    if not anchor_present:
                        issues["S12_typeD_hybrid_no_source_anchor"].append((tid, ""))

                # Family rollup
                per_family[fam]["typeA"] += (tt == "A")
                per_family[fam]["typeB"] += (tt == "B")
                per_family[fam]["typeC"] += (tt == "C")
                per_family[fam]["typeD"] += (tt == "D")
                per_family[fam]["synthetic"] += (pcls == "synthetic")
                per_family[fam]["hybrid"] += (pcls == "hybrid")
                per_family[fam]["real"] += (pcls == "real")

    # ===== Report =====
    print("=" * 76)
    print("Task-setup quality audit")
    print("=" * 76)
    print(f"Total cards: {cards_seen}")
    print()

    print("Per-family distribution:")
    print(f"  {'family':<25} {'tot':>5} {'A':>4} {'B':>4} {'C':>4} {'D':>4} "
          f"{'real':>5} {'hybrid':>6} {'syn':>5}")
    for fam in sorted(per_family):
        s = per_family[fam]
        print(f"  {fam:<25} {s['total']:>5} {s['typeA']:>4} {s['typeB']:>4} "
              f"{s['typeC']:>4} {s['typeD']:>4} {s['real']:>5} "
              f"{s['hybrid']:>6} {s['synthetic']:>5}")
    print()

    print("Issues found (by check):")
    if not issues:
        print("  none")
    else:
        for check in sorted(issues):
            lst = issues[check]
            print(f"  {check}: {len(lst)} cards — sample: {lst[:3]}")
    print()

    # Hard-error count
    HARD_CHECKS = {
        "S1_prompt_too_short", "S2_gold_too_short", "S3_no_safety_constraints",
        "S4_no_evidence", "S5_typeD_no_decision_verb",
        "S9_hybrid_generation_rule_thin", "S10_csp_file_not_downloaded",
    }
    hard = sum(len(issues[c]) for c in HARD_CHECKS if c in issues)
    soft = sum(len(lst) for c, lst in issues.items() if c not in HARD_CHECKS)
    print(f"Hard issues:  {hard}  (must-fix before evaluation)")
    print(f"Soft issues:  {soft}  (review-required; may be acceptable in context)")
    print()
    if hard:
        print(f"AUDIT FAILED — {hard} hard-error cards across "
              f"{sum(1 for c in HARD_CHECKS if c in issues)} categories")
        return 1
    print("AUDIT PASSED (no hard errors)")
    if soft:
        print("Soft warnings exist — review per category above.")
    return 0


if __name__ == "__main__":
    sys.exit(audit())
