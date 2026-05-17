# Real ADS-B Exchange Sampling Methodology — Family 6: ATC Separation

## Data Sources

| File | Source URL | Fetched | SHA-256 (partial) |
|---|---|---|---|
| `acas_20241201.csv.gz` | adsbexchange.com ACAS 2024-12-01 | 2026-05-17 | `7abcab31...` |
| `acas_20240101.csv.gz` | adsbexchange.com ACAS 2024-01-01 | 2026-05-17 | `626ca3e4...` |
| `operations_20241201.csv.gz` | adsbexchange.com operations 2024-12-01 | 2026-05-17 | `26147ca2...` |
| `operations_20250101.csv.gz` | adsbexchange.com operations 2025-01-01 | 2026-05-17 | `29723591...` |
| `ax_arrivals_20241201.csv` | adsbexchange.com arrivals 2024-12-01 | 2026-05-17 | `2a18bef9...` |
| `ax_arrivals_20250101.csv` | adsbexchange.com arrivals 2025-01-01 | 2026-05-17 | `2ffd2676...` |

All files confirmed HTTP 200 in `manifest.jsonl`. License: ADS-B Exchange public sample data.

## ACAS Event Extraction

### Parsing

Each row of `acas_20241201.csv.gz` and `acas_20240101.csv.gz` is space/comma-delimited with fields:
`date, time, hex, DF, 17, bytes, bytes_hex, lat, lon, altitude_ft, ft, vrate_fpm, fpm, ARA, ara_code, RAT, rat_val, MTE, mte_val, RAC, rac_code, empty, ra_description`

We extracted: `date`, `time`, `hex` (ICAO 24-bit address), `lat`, `lon`, `alt_ft`, `vrate_fpm`, `ra_description`.

### Coordinated RA Pair Identification

Rows with `TIDh: <hex>` in the `ra_description` field represent coordinated TCAS Resolution Advisories where the reporting aircraft's TCAS was actively coordinating with the identified traffic (`TIDh` = Traffic ID hex). We grouped all events by the sorted pair `(own_hex, intruder_hex)`.

**Dec 2024 (acas_20241201.csv.gz):** 11,031 events → 27 coordinated RA pairs.
**Jan 2024 (acas_20240101.csv.gz):** 3,703 events → 9 coordinated RA pairs.
**Total: 36 unique aircraft pairs with real coordinated TCAS RAs.**

### Nearest-In-Time Snapshot Selection

For each pair, we selected the **first recorded event per aircraft** within the coordinated event window as the representative snapshot (nearest-in-time record). This represents the position at or near the start of the TCAS RA resolution sequence.

### Haversine Verification

Every distance claim was verified using `aerosafety.tools.separation_calculator.calculate_horizontal_separation()` (haversine formula, EARTH_RADIUS_NM = 3440.065). No approximation (e.g., flat-earth cos) is used in the final card values.

### Pairs Selected for Cards

| Pair (hex1/hex2) | Source File | Timestamp | Horiz NM | Vert ft | RA Types | Cards |
|---|---|---|---|---|---|---|
| a5a2cc/406c39 | acas_20241201.csv.gz | 2024-12-01T22:57:15Z | 0.232 | 600 | Monitor vSpeed, Clear of Conflict | B-001, C-001, D-001 |
| a149c1/abdd63 | acas_20241201.csv.gz | 2024-12-01T04:23:03Z | 0.330 | 75 | Climb, Descend | B-002, C-002, D-002 |
| a88335/abd932 | acas_20240101.csv.gz | 2024-01-01T15:23:28Z | 0.422 | 150 | Descend | B-003, C-005, D-007 |
| a6e4e8/ad5269 | acas_20241201.csv.gz | 2024-12-01T05:52:34Z | 0.446 | 575 | Descend, Level Off | B-004, D-012 |
| a28eb7/acf5bb | acas_20241201.csv.gz | 2024-12-01T20:10:34Z | 0.445 | 100 | Maintain vSpeed | B-005 |
| a7178c/abe77a | acas_20241201.csv.gz | 2024-12-01T03:20:07Z | 1.053 | 50 | Descend, Level Off | B-006 |
| a5427b/a95d96 | acas_20241201.csv.gz | 2024-12-01T21:12:07Z | 1.408 | 0 | Descend | B-007, C-004, D-004 |
| a7def8/c05e72 | acas_20241201.csv.gz | 2024-12-01T17:09:36Z | 3.079 | 0 | Climb, Descend | B-008, C-003, D-003 |
| a71f24/abfdaf | acas_20240101.csv.gz | 2024-01-01T13:46:20Z | 1.170 | 1650 | Descend | B-009, D-009 |
| a16b24/a5130a | acas_20241201.csv.gz | 2024-12-01T13:49:42Z | 2.507 | 1600 | Climb | B-010, C-007, D-005 |
| a0a522/aa1e68 | acas_20241201.csv.gz | 2024-12-01T01:05:43Z | 3.127 | 1250 | Level Off | B-011, D-013 |
| a2b416/a81f83 | acas_20241201.csv.gz | 2024-12-01T00:42:41Z | 1.376 | 225 | Level Off, Descend | B-016, C-006, D-008 |
| a29680/ad0725 | acas_20241201.csv.gz | 2024-12-01T21:25:00Z | 1.548 | 225 | Climb, Descend | B-014, C-008, D-006 |
| a63612/aa3579 | acas_20241201.csv.gz | 2024-12-01T15:27:35Z | 2.198 | 550 | Monitor vSpeed | B-015, C-013, D-015 |
| 3007ef/3d602e | acas_20240101.csv.gz | 2024-01-01T15:20:18Z | 0.966 | 550 | Monitor vSpeed, Level Off | B-017 |
| a23fe5/a3b4c8 | acas_20240101.csv.gz | 2024-01-01T23:03:13Z | 0.789 | 575 | Descend | B-018 |
| a7f096/aa56b8 | acas_20240101.csv.gz | 2024-01-01T23:06:24Z | 0.530 | 200 | Descend | D-010 |
| 06a36b/06a384 | acas_20240101.csv.gz | 2024-01-01T04:43:24Z | 0.839 | 500 | Monitor vSpeed | B-020, C-010, D-011 |

## Operations Data Extraction

For same-runway in-trail hazard scenarios (Type B cards B-012, B-013, B-014, B-019; Type C card C-009):

- Loaded `operations_20241201.csv.gz` and `operations_20250101.csv.gz`
- Filtered: `operation == 'landing'`, airport in major US airports, runway field non-empty
- Grouped by airport + runway; sorted by timestamp
- Identified pairs landing within 3 minutes on the same runway
- **7,133 same-runway pairs within 3 minutes** found across 9 major airports
- Selected representative pairs at KATL (highest traffic), KORD, and KDFW for card construction
- In-trail distance calculated as: `approach_speed_kts × interval_seconds / 3600`
- Wake turbulence minima verified against FAA JO 7110.65Z §3-9-6

## Data Integrity

- No positions were modified, interpolated, or fabricated
- All coordinates are taken directly from raw ADS-B Exchange file rows
- All distances reported in task cards are haversine-verified values
- Vertical separations are simple arithmetic differences of recorded altitudes
- Source file + timestamp cited in every `provenance.source` field

## Limitations

- ADS-B Exchange sample files contain one day per month — not continuous coverage
- Aircraft call signs are not present in ACAS files; only ICAO 24-bit hex codes are available
- Some aircraft types are inferred from the operations files by matching hex codes; not all pairs could be cross-referenced
- ACAS data represents aircraft equipped with Mode-S transponders with ADS-B — general aviation without ADS-B is not captured
