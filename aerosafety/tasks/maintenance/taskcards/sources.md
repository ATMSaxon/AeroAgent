# Sources — Family 8: Maintenance / MEL / Service Difficulty

All task cards in this family are **SYNTHETIC**. No real operator MEL data, real aircraft maintenance logs, or real SDR records were accessed or reproduced. All MEL provisions in task prompts are clearly labelled "synthetic" and are constructed to be representative of real MEL structure and regulatory basis without reproducing any proprietary operator document.

## Regulatory Sources

| Source | Title | Applicability |
|--------|-------|--------------|
| 14 CFR §91.213 | Inoperative instruments and equipment — Part 91 operations | Type A (MX-A-016, MX-A-024), Type C (MX-C-006) |
| 14 CFR §121.628 | Inoperative instruments and equipment — Part 121 operations | All task cards (primary MEL authority) |
| 14 CFR §121.701 | Maintenance log requirements — Part 121 | Type C (MX-C-012) |
| 14 CFR §121.703 | Service Difficulty Reports — Part 121 | Type A (MX-A-007), Type B (MX-B-022), Type C (MX-C-007) |
| 14 CFR §121.339 | Emergency equipment for extended overwater operations | Type D (MX-D-008) |
| 14 CFR §121.356 | TCAS equipment — Part 121 | Type D (MX-D-007) |
| 14 CFR §121.380 | Maintenance recording requirements | Type A (MX-A-019) |
| 14 CFR §121.1109 | Supplemental structural inspection requirements (aging aircraft) | Type C (MX-C-014) |
| 14 CFR §135.177 | Emergency equipment — Part 135 | Type D (MX-D-011) |
| 14 CFR §135.179 | Inoperative instruments and equipment — Part 135 | Type C (MX-C-004) |
| 14 CFR §25.854 | Lavatory fire protection — Type Certificate requirement | Type D (MX-D-003) |
| 14 CFR §39.19 | Alternative Methods of Compliance (AMOC) — Airworthiness Directives | Type A (MX-A-029), Type C (MX-C-014) |
| 14 CFR §43.9 | Maintenance record requirements | Type C (MX-C-012) |
| 14 CFR §91.7 | Civil aircraft airworthiness | Type C (MX-C-006, MX-C-010) |
| 14 CFR §91.409(f) | Aircraft inspections — Airworthiness Limitation Items | Type C (MX-C-014) |
| 14 CFR §21.197 | Special flight permits (ferry permits) | Type A (MX-A-015), Type C (MX-C-006) |

## FAA Advisory Circulars and Orders

| Source | Title | Applicability |
|--------|-------|--------------|
| FAA Order 8900.1 Vol 4 Ch 4 §4-601 | MEL Administration — MMEL vs operator MEL | Type C (MX-C-004) |
| FAA Order 8900.1 Vol 4 Ch 4 §4-609 | MEL interval administration, deferral requirements | Type A (MX-A-002, MX-A-003), Type C (MX-C-001, MX-C-012) |
| FAA Order 8900.1 Vol 4 Ch 4 §4-614 | CDL administration | Type A (MX-A-004), Type C (MX-C-010) |
| FAA Order 8900.1 Vol 3 Ch 55 | Reliability programs and repeat defect analysis | Type C (MX-C-007) |
| FAA Order 2150.3C | Compliance and enforcement — voluntary disclosure | Type C (MX-C-002, MX-C-010) |
| FAA AC 91-67 | MEL and CDL — Part 91 Operations | Type C (MX-C-006) |
| FAA AC 120-78B | Airworthiness Assurance — Maintenance quality | Type C (MX-C-007) |
| FAA AC 120-101 | Parts 91, 121, 125, 135 — Aging Aircraft Inspections | Type C (MX-C-014) |
| FAA AC 25-23 | TAWS airworthiness standards | Type C (MX-C-011) |

## ICAO Standards

| Source | Title | Applicability |
|--------|-------|--------------|
| ICAO Doc 9760 | Airworthiness Manual — CAMO requirements | Type A (MX-A-009) |
| ICAO Annex 6 §6.15 | TAWS/GPWS requirements for large aircraft | Type C (MX-C-011) |

## MEL Category Reference

All MEL categories in this task family follow the standard MMEL category definitions:

| Category | Maximum Deferral Interval | Notes |
|----------|--------------------------|-------|
| A | As specified in MEL | Short, often hours to 1 day; custom per item |
| B | 3 calendar days | Day 1 = day write-up entered in maintenance log |
| C | 10 calendar days | Day 1 = day write-up entered |
| D | 120 calendar days | Low safety impact items |

Source: FAA Order 8900.1 Vol 4 Ch 4 §4-609; MMEL Policy Letter 25 (Master MEL revision basis)

## ETOPS MEL Asterisk (*) Notation

Items marked with asterisk (*) in the MMEL/MEL require a separate ETOPS MEL section review. Base MEL deferral does not automatically apply on ETOPS operations. Source: FAA ETOPS CPI (Continuing Performance Indicator) guidance; 14 CFR Part 121 Appendix P.

## Tool Reference

`aerosafety.tools.mel_checker`: MOCK implementation. Returns `MELCheckResult(mock=True, status=UNKNOWN)` for all inputs. All Type D task cards require this tool to be called as the first step, with the understanding that the MOCK result must be supplemented by reasoning over the synthetic MEL provision provided in the prompt. See `aerosafety/tools/mel_checker.py`.

## What Was NOT Done

1. No real operator MEL documents (from any airline) were reproduced or paraphrased
2. No real SDR records from the FAA SDR database were accessed
3. No real aircraft maintenance logbook entries were used
4. MEL provisions in task prompts are clearly labelled "synthetic" — they represent realistic MEL structure but are not from any real approved document
5. Aircraft registrations used in Type D tasks are plausible US registration formats (N-numbers) or Transport Canada C-numbers but do not correspond to verified real aircraft
6. All scenario details (routes, dates, defect descriptions, weather) are constructed for educational/evaluation purposes
