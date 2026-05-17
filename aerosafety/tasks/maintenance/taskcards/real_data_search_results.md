# Real Data Search Results — Family 8: Maintenance / MEL / Service Difficulty
# T27 Data Investigation Log
# Investigator: automated (agent), 2026-05-17

## Summary

Three data source categories were investigated for T27 (Rebuild F8 Maintenance with real data).
Two were unavailable; one (NTSB CAROL records) yielded usable real maintenance event data.
The hybrid approach (Option C) was approved by team-lead.

---

## 1. FAA SDR (Service Difficulty Report) Exports

### Files examined
- `data/raw/FAA_SDR/2026-05-17/SDR_export_202505_202510.xls`
- `data/raw/FAA_SDR/2026-05-17/SDR_export_202511_202605.xls`

### Findings
Both XLS files are empty HTML-table exports. Each file contains only the column header row
and zero data rows. The files have identical SHA256 checksums:
```
1c2083ff... (both files identical)
```

The SDR export system (`av-info.faa.gov`) returned HTTP 503 (Service Unavailable) when
accessed during the download run. The SDR query API (`sdrs.faa.gov`) is login-walled
and requires authenticated FAA access.

The FAA SDR manifest (`data/raw/FAA_SDR/2026-05-17/manifest.jsonl`) documents:
- Two XLS entries with note: "XLS is HTML table — empty export, zero data rows"
- One entry for `av-info.faa.gov` with HTTP status: 503

### Decision
SDR data is unavailable for this dataset run. All SDR-dependent task card content
is explicitly marked SYNTHETIC with the following provenance note:

> SYNTHETIC: real MEL is operator-specific and proprietary (FAA Order 8900.1);
> SDR public access also unavailable (av-info.faa.gov 503, sdrs.faa.gov login-walled).
> Scenarios constructed from public FAA Order 8900.1 + ICAO Doc 9760 rules.

---

## 2. NTSB Full Reports — Maintenance/MEL/Dispatch Content Search

### Files examined
42 PDFs in `data/raw/NTSB_FULL_REPORTS/2026-05-17/`

### Search methodology
PDF text extraction with keyword search for: `maintenance`, `deferred`, `MEL`,
`discrepancy`, `inoperative`, `write-up`, `dispatch`.

### Findings — False Positives
12 keyword hits were false positives:
- "melted" matching "MEL" — heat/fire narratives
- Logbook references in GA accident narratives (not Part 121 dispatch decisions)
- "inoperative" in weather sensor descriptions unrelated to maintenance deferrals
- "maintenance" in generic context (maintenance of flight path, altitude maintenance)

### Findings — Real Maintenance Failure Content (no MEL/dispatch content, but genuine maintenance failure narratives)

The following 4 NTSB final reports contain genuine maintenance failure findings suitable
for Type B hazard identification and Type C consequence reasoning task cards:

| Report ID | Aircraft | Event | Maintenance Finding | Used in Cards |
|-----------|----------|-------|---------------------|---------------|
| ERA24FA013 | Beech A23-24, N6945Q | Fatal, oil starvation | Oil filler cap not secured post-annual inspection | MX-B-001, MX-C-001 |
| WPR24FA056 | Vans RV-8, N6948L | Partial power loss | Fuel sealant contamination, cure time not observed | MX-B-002, MX-C-002 |
| ERA24FA078 | Piper PA46R-350T, N539MA | Vibration at cruise | Missing induction clamp post-scheduled maintenance | MX-B-003, MX-C-003 |
| WPR24FA054 | Beech A36, N4171S | Fatal, engine failure | Improper connecting rod torque during top overhaul | MX-B-004 |

Note: All 4 reports are Part 91 GA accidents, not Part 121 commercial operations.
They provide genuine maintenance failure narratives (sign-off deficiencies, return-to-service
omissions) that are applicable to the task family's maintenance error analysis objectives.

### NTSB PDF source URLs (from manifest)
All accessible via: `https://data.ntsb.gov/carol-repgen/api/Aviation/ReportMain/GenerateNewestReport/<REPORT_ID>/pdf`

---

## 3. NTSB CAROL Database — Commercial Aviation Records

### File examined
`data/raw/NTSB_ACCIDENT_DB/2026-05-17/ntsb_accidents_20260215_20260517.zip`
Contains: `cases2026-05-17_01-24.json` — 327 CAROL records (2026-02-15 to 2026-05-17)

### Filter methodology
Filtered for cases with `cm_events` tier1Name or tier2Name matching:
- System/Component Failure
- Powerplant
- Flight Controls
- Ground Operations (non-weather events)

75 unique cases with relevant events identified.

### Findings — Usable Part 121/135 Commercial Records

| CAROL ID | Aircraft | Operator | Regulation | Event Type | mkey | Used in Cards |
|----------|----------|----------|------------|------------|------|---------------|
| DCA26WA168 | A330-323 N813NW | Delta Air Lines | Part 121 | Uncontained engine failure | DCA26WA168 | MX-B-005, MX-C-004, MX-D-014 |
| DCA26WA147 | B737-823 N907NN | American Airlines | Part 121 | Powerplant failure (closed) | DCA26WA147 | MX-B-006 |
| DCA26LA184 | B787-9 N24972 | (Part 121) | Part 121 | Powerplant + in-flight fire | DCA26LA184 | MX-B-007 |
| WPR26FA141 | Hughes 369D N715KV | (Part 135) | Part 135 | Flight control failure, fatal | WPR26FA141 | MX-B-008, MX-C-005, MX-D-003 |
| DCA26WA169 | A350-941 N513DZ | Delta Air Lines | Part 121 | Powerplant enroute failure | DCA26WA169 | MX-B-009 |
| ERA26LA137 | BN-2B-27 N865VL | (Part 135) | Part 135 | Non-powerplant taxi failure | ERA26LA137 | MX-B-010 |
| ERA26FA179 | Cessna 401B N122AT | (Part 91) | Part 91 | Fatal partial power loss post-maintenance | ERA26FA179 | MX-B-022 |

### CAROL data access note
CAROL records do not include full final reports. The event type and aircraft/operator
information are available from the JSON case records. Full investigation findings
are only available once NTSB closes a case and publishes a final report or factual report.
For open cases (DCA26WA168, DCA26LA184, WPR26FA141, DCA26WA169, ERA26LA137), the event
type and context are used for task card framing; the specific findings are not stated
as confirmed facts but as plausible scenarios consistent with the event type.

---

## 4. Real Data Yield Summary

| Type | Real Cards | Source |
|------|-----------|--------|
| Type A | 0 of 30 | SYNTHETIC (MEL knowledge, no real data source applicable) |
| Type B | 11 of 22 | 4 NTSB PDFs + 7 CAROL records |
| Type C | 5 of 15 | 4 NTSB PDFs + 1 CAROL record |
| Type D | 2 of 15 | 2 CAROL records (as hazard context anchors) |
| **Total** | **18 of 82** | **~22% real-data-grounded** |

### Why 22% is the maximum achievable from available data

1. FAA SDR exports were empty — intended source for 40-50% of Type B/C/D real data
2. NTSB PDFs yielded no Part 121 MEL/dispatch content (all maintenance hits were GA Part 91)
3. CAROL records for recent events contain event context but not final investigation findings
4. Operator MELs are proprietary — no public repository exists

The hybrid approach (SYNTHETIC for Type A and SYNTHETIC fillers for Type B/C/D with
explicit provenance notes) is the maximum fidelity achievable from available public data.
