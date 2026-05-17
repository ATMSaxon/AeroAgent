# Real-Data Search Results — Family 7: Wake Vortex / Separation Safety

**Search conducted:** 2026-05-17  
**Searcher:** tools-builder agent (T26)  
**Corpus:** `data/raw/NTSB_FULL_REPORTS/2026-05-17/` — 42 NTSB full-report PDFs

---

## 1. Methodology

Text extraction was performed using `pdftotext` on each of the 42 PDFs. The
extracted plain-text was searched (case-insensitive) for the following keywords:

| Keyword group | Terms searched |
|---|---|
| Primary wake terms | `wake`, `vortex`, `wake turbulence` |
| Upset/encounter terms | `upset`, `preceding aircraft`, `lead aircraft`, `leading aircraft` |
| Broadened fallback | `turbulence`, `separation`, `preceding`, `following aircraft`, `loss of control` |

Two search passes were run:
1. **Strict pass** — exact terms `wake`, `vortex`, `wake turbulence`, `upset`, `preceding aircraft`
2. **Broadened pass** — added `turbulence`, `separation`, `preceding`, `loss of control`

For every hit, the surrounding ±300-character context was extracted and manually
inspected to determine whether the hit related to wake turbulence as an accident
cause or contributing factor.

---

## 2. Results

### Strict pass

| Metric | Value |
|---|---|
| PDFs searched | 42 |
| PDFs with any hit | 1 |
| Wake turbulence hits (confirmed causal) | **0** |

**One hit found:** `ERA24FA078_2023_fatal_eastern_a.pdf` — the word "wake" appeared
once in the phrase "Wake Forest Baptist Medical Center" (the autopsy facility).
This is not a wake turbulence event.

### Broadened pass (turbulence, separation, preceding, loss of control)

| Keyword | PDFs with hits | Wake-turbulence causal? |
|---|---|---|
| `turbulence` | 30 | **0** — all hits were in boilerplate sections (e.g., "weather conditions included light turbulence") or checklist text; none identified a preceding aircraft as the turbulence source |
| `separation` | 6 | **0** — all hits referred to structural part separation from the accident aircraft, not ATC wake-turbulence separation |
| `preceding` | 1 | **0** — context was "records were located for any recent time preceding the accident" (temporal use, not aircraft sequencing) |
| `loss of control` | 7 | **0** — all attributed to stall/spin, spatial disorientation, mechanical failure, or unknown; none attributed to wake encounter |

### Defining events across all 42 PDFs

The NTSB "Defining Event" field was extracted for each report:

| Event type | Count |
|---|---|
| Loss of engine power (total or partial) | 4 |
| Aerodynamic stall/spin | 3 |
| Loss of control in flight | 2 |
| Powerplant sys/comp malf/fail | 3 |
| Unknown or undetermined | 5 |
| Part(s) separation from AC | 3 |
| Loss of control on ground | 2 |
| VFR encounter with IMC | 1 |
| Fuel contamination | 1 |
| Hard landing | 1 |
| Collision with terr/obj | 2 |
| Wildlife encounter | 1 |
| Landing gear issues | 2 |
| Other | 12 |
| **Wake turbulence / vortex encounter** | **0** |

---

## 3. Conclusion

**The 42-PDF NTSB corpus contains zero wake turbulence encounter events.**

This finding is consistent with the statistical rarity of wake turbulence accidents:
- Wake turbulence encounters serious enough to appear in NTSB fatal accident reports
  occur in roughly 1-3% of fatal GA accidents in any given year (NTSB data).
- A random 42-report sample skewed toward GA fatal accidents is unlikely to include
  any wake encounter events.
- The corpus contains predominantly: engine failures, stall/spin events, CFIT,
  and mechanical failures — typical of GA fatal accident distribution.

---

## 4. Implications for Task Cards

Per T26 brief: "If the corpus yields fewer than 8-10 real wake cases (likely —
wake encounters are rare in any 42-PDF sample), document this honestly and keep
most cards SYNTHETIC."

**Decision: All 75 task cards remain SYNTHETIC.**

Type B, C, and D cards (which the T26 brief intended to anchor with REAL cases)
carry the following provenance note:

```
"license": "PILOT — NOT EXPERT-REVIEWED",
"real_data_search": "NTSB 42-PDF corpus searched 2026-05-17; 0 wake turbulence events found. Card is SYNTHETIC — no comparable real public NTSB report available in this corpus."
```

The existing SYNTHETIC cards (built under T16) are retained with this additional
provenance annotation. No card content was changed — only provenance metadata
was updated to document the negative search result.

---

## 5. Search Reproducibility

The following Python command reproduces the strict search:

```python
import subprocess, os, re

PDF_DIR = "data/raw/NTSB_FULL_REPORTS/2026-05-17"
KEYWORDS = ["wake", "vortex", "wake turbulence", "upset",
            "preceding aircraft", "lead aircraft", "leading aircraft"]

for pdf in sorted(f for f in os.listdir(PDF_DIR) if f.endswith(".pdf")):
    result = subprocess.run(
        ["pdftotext", os.path.join(PDF_DIR, pdf), "-"],
        capture_output=True, text=True
    )
    text = result.stdout.lower()
    hits = {kw: text.count(kw) for kw in KEYWORDS if text.count(kw) > 0}
    if hits:
        print(f"{pdf}: {hits}")
```

**Expected output (as of 2026-05-17 corpus):**
```
ERA24FA078_2023_fatal_eastern_a.pdf: {'wake': 1}
```
(The single "wake" hit is the medical center name — not a wake turbulence event.)
