# Sources — Family 8: Maintenance and Operational Reliability
# Updated T27 (2026-05-17): Hybrid real/synthetic data model

## Overview

Family 8 task cards use a **hybrid provenance model** introduced in T27:

- **Type A (30 cards)**: Fully SYNTHETIC — MEL/MMEL/CDL regulatory knowledge; no real operator MEL data used or available (operator MELs are proprietary).
- **Type B (22 cards)**: Hybrid — 11 REAL cards grounded in NTSB accident reports or NTSB CAROL commercial aviation records; 11 SYNTHETIC fillers with explicit proprietary provenance note.
- **Type C (15 cards)**: Hybrid — 5 REAL cards grounded in NTSB accident reports or CAROL records; 10 SYNTHETIC fillers with explicit proprietary provenance note.
- **Type D (15 cards)**: Hybrid — 2 cards use CAROL records as hazard context anchors; 13 fully SYNTHETIC MEL dispatch scenarios with explicit proprietary provenance note.

See `real_data_search_results.md` for the full data investigation log explaining why public SDR data and NTSB full-report MEL/dispatch content were not available.

---

## Real Data Sources

### NTSB Accident Reports (Final/Factual)

| Report ID | Aircraft | Event | Cards |
|-----------|----------|-------|-------|
| ERA24FA013 | Beech A23-24 N6945Q, Part 91 | Oil starvation, oil filler cap unsecured post-annual inspection | MX-B-001, MX-C-001 |
| WPR24FA056 | Vans RV-8 N6948L, Part 91 | Fuel sealant contamination following fuel system overhaul | MX-B-002, MX-C-002 |
| ERA24FA078 | Piper PA46R-350T N539MA, Part 91 | Missing induction clamp following scheduled maintenance | MX-B-003, MX-C-003 |
| WPR24FA054 | Beech A36 N4171S, Part 91 | Connecting rod failure from improper torque during top overhaul | MX-B-004 |

Report access URL pattern: `https://data.ntsb.gov/carol-repgen/api/Aviation/ReportMain/GenerateNewestReport/<ID>/pdf`
Access date: 2026-05-17

### NTSB CAROL Records (Commercial Aviation Records)

| CAROL ID | Aircraft | Operator | Regulation | Event | Cards |
|----------|----------|----------|------------|-------|-------|
| DCA26WA168 | A330-323 N813NW | Delta Air Lines | Part 121 | Uncontained engine failure | MX-B-005, MX-C-004, MX-D-014 |
| DCA26WA147 | B737-823 N907NN | American Airlines | Part 121 | Powerplant failure (investigation closed) | MX-B-006 |
| DCA26LA184 | B787-9 N24972 | (Part 121) | Part 121 | Powerplant failure with in-flight fire | MX-B-007 |
| WPR26FA141 | Hughes 369D N715KV | (Part 135) | Part 135 | Flight control failure, fatal | MX-B-008, MX-C-005, MX-D-003 |
| DCA26WA169 | A350-941 N513DZ | Delta Air Lines | Part 121 | Powerplant failure enroute | MX-B-009 |
| ERA26LA137 | BN-2B-27 N865VL | (Part 135) | Part 135 | Non-powerplant failure during taxi | MX-B-010 |
| ERA26FA179 | Cessna 401B N122AT | Part 91 | Part 91 | Fatal partial power loss post-powerplant servicing | MX-B-022 |

CAROL database source: NTSB CAROL case records, `data/raw/NTSB_ACCIDENT_DB/2026-05-17/ntsb_accidents_20260215_20260517.zip`
Access date: 2026-05-17

---

## Unavailable Real Data Sources

| Source | Status | Reason |
|--------|--------|--------|
| FAA SDR exports (av-info.faa.gov) | Empty | Both XLS files contain only headers, zero data rows; server returned HTTP 503 |
| FAA SDR API (sdrs.faa.gov) | Unavailable | Login-walled; requires authenticated FAA access |
| NTSB PDFs — Part 121 MEL/dispatch content | None found | All 42 PDFs in the dataset contain only GA Part 91 accidents; no Part 121 MEL/dispatch scenarios |
| Operator MELs | Proprietary | Operator MELs are approved under 14 CFR §121.628 / §135.179 and not publicly available |

---

## Regulatory Sources

| Source | Title | Applicability |
|--------|-------|--------------|
| 14 CFR §91.213 | Inoperative instruments and equipment — Part 91 | Type A, Type C (MX-C-006) |
| 14 CFR §91.7 | Civil aircraft airworthiness | Type C (MX-C-006, MX-C-011) |
| 14 CFR §91.409(f) | Aircraft inspections — ALIs | Type C (MX-C-011) |
| 14 CFR §21.197 | Special flight permits (ferry permits) | Type A, Type C |
| 14 CFR §25.854 | Lavatory fire protection — Type Certificate | Type D (MX-D-004) |
| 14 CFR §39.19 | Alternative Methods of Compliance (AMOC) | Type A, Type C |
| 14 CFR §43.9 | Maintenance record requirements | Type B (MX-B-001 to MX-B-004), Type C (MX-C-001 to MX-C-003) |
| 14 CFR §43.13 | Maintenance methods and techniques | Type B (MX-B-002, MX-B-003, MX-B-008), Type C (MX-C-002, MX-C-003, MX-C-005) |
| 14 CFR §121.263 | Cargo compartment fire protection | Type B (MX-B-021) |
| 14 CFR §121.308 | Lavatory fire protection | Type B (MX-B-016) |
| 14 CFR §121.333 | Supplemental oxygen requirements | Type B (MX-B-017) |
| 14 CFR §121.339 | Emergency equipment for extended overwater operations | Type D (MX-D-009) |
| 14 CFR §121.343 | Flight recorders | Type B (MX-B-020) |
| 14 CFR §121.356 | TCAS equipment | Type D (MX-D-008) |
| 14 CFR §121.359 | Cockpit voice recorders | Type B (MX-B-021) |
| 14 CFR §121.374 | ETOPS requirements | Type B, Type D |
| 14 CFR §121.628 | Inoperative instruments and equipment — Part 121 | All cards (primary MEL authority) |
| 14 CFR §121.701 | Maintenance log requirements | Type C |
| 14 CFR §121.703 | Service Difficulty Reports | Type A, Type B (MX-B-005, MX-B-006, MX-B-007), Type C |
| 14 CFR §121.1109 | Supplemental structural inspection (aging aircraft) | Type C (MX-C-011) |
| 14 CFR §135.25 | Aircraft airworthiness — Part 135 | Type C (MX-C-005) |
| 14 CFR §135.177 | Emergency equipment — Part 135 | Type D (MX-D-011) |
| 14 CFR §135.179 | Inoperative instruments and equipment — Part 135 | Type C (MX-C-008) |
| 49 CFR §830 | NTSB notification requirements | Type B (MX-B-005, MX-B-007, MX-B-009), Type C (MX-C-004) |

## FAA Advisory Circulars and Orders

| Source | Title | Applicability |
|--------|-------|--------------|
| FAA Order 8900.1 Vol 4 Ch 4 §4-601 | MEL Administration — MMEL vs operator MEL | Type C (MX-C-008) |
| FAA Order 8900.1 Vol 4 Ch 4 §4-609 | MEL interval administration | Type A, Type C (MX-C-006, MX-C-007) |
| FAA Order 8900.1 Vol 4 Ch 4 §4-614 | CDL administration | Type A |
| FAA Order 8900.1 Vol 3 Ch 55 | Reliability programs and repeat defect analysis | Type C (MX-C-013) |
| FAA Order 8900.1 Vol 6 Ch 2 | ETOPS MEL restrictions | Type B (MX-B-011, MX-B-014) |
| FAA Order 2150.3C | Compliance and enforcement — voluntary disclosure | Type C |
| FAA AC 91-67 | MEL and CDL — Part 91 operations | Type C |
| FAA AC 120-78B | Airworthiness Assurance | Type C (MX-C-013) |
| FAA AC 120-101 | Aging Aircraft Inspections | Type C (MX-C-011) |
| FAA AC 25-23 | TAWS airworthiness standards | Type C (MX-C-014) |

## ICAO Standards

| Source | Title | Applicability |
|--------|-------|--------------|
| ICAO Doc 9760 | Airworthiness Manual — CAMO requirements | Type A |
| ICAO Annex 6 §6.15 | TAWS/GPWS requirements | Type C (MX-C-014) |

---

## MEL Category Reference

| Category | Maximum Deferral Interval | Notes |
|----------|--------------------------|-------|
| A | As specified in MEL | Short, often hours to 1 day; custom per item |
| B | 3 calendar days | Day 1 = day write-up entered in maintenance log |
| C | 10 calendar days | Day 1 = day write-up entered |
| D | 120 calendar days | Low safety impact items |

Source: FAA Order 8900.1 Vol 4 Ch 4 §4-609; MMEL Policy Letter 25.

## ETOPS MEL Asterisk (*) Notation

Items marked with asterisk (*) in the MMEL/MEL require a separate ETOPS MEL section review.
Base MEL deferral does not automatically apply on ETOPS operations.
Source: FAA ETOPS CPI guidance; 14 CFR Part 121 Appendix P.

---

## Tool Reference

`aerosafety.tools.mel_checker`: MOCK implementation. Returns `MELCheckResult(mock=True, status=UNKNOWN)` for all inputs. All Type D task cards require this tool to be called as the first step, with the understanding that the MOCK result must be supplemented by reasoning over the synthetic MEL provision provided in the prompt. The mel_checker tool is marked `mock=True` in the tool registry. See `aerosafety/tools/mel_checker.py`.
