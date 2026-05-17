# Synthetic NOTAM Construction Rules

**Per CLAUDE.md §2.2: Every synthetic record must carry explicit generation_rule documentation.**

This file documents the rules used to construct all synthetic NOTAMs in this task family.
All NOTAMs in tasks NC-A-*, NC-B-*, NC-C-*, NC-D-* are SYNTHETIC unless explicitly stated otherwise.
No live NOTAM data was used.

---

## Rule 1: NOTAM Series and Number Format

**Format:** `<Series><Number>/<YY> NOTAM<Type>`
- Series: single letter A-Z (typically A for US domestic, B for international sub-series)
- Number: 4-digit zero-padded integer
- YY: 2-digit year
- Type: N (New), R (Replacement), C (Cancellation)

**Source:** FAA JO 7930.2S §2-1-3; ICAO Annex 15 §6.1

**Example constructed:** `A1234/26 NOTAMN` = New NOTAM, Series A, number 1234, year 2026

---

## Rule 2: Q-Line Field Construction

**Format:** `Q) FIR/QCODE/TRAFFIC/PURPOSE/SCOPE/LOWER/UPPER/COORDINATES`

Fields sourced from:
- **FIR:** Real ICAO FIR identifiers only (KZAU, KZNY, EGTT, LFFF, etc.)
- **NOTAM code:** Constructed from ICAO Annex 15 Appendix 6 Q-code table. Pattern: Q + 2-char subject + 2-char condition.
  - Subject codes used: MR (Movement area/Runway), IG (ILS/Glideslope), NV (Navigation/ATIS), IL (ILS), NL (Lighting/Apron), OB (Obstacle), QO (Obstacle subject prefix), SA (Safety area/Parachute), NF (ATIS), NW (Weather service), NTA (TWR), RT (Restricted area), QR (Restricted prefix), HF (HF communications), GP (GPS), PI (Instrument procedure)
  - Condition codes used: LC (Line/Closed), AS (unserviceable), CE (crane erected), CA (active), XX (placeholder for unspecified condition in educational context)
- **Traffic:** IV (IFR+VFR), I (IFR), V (VFR), M (Military) — per ICAO Annex 15 Appendix 6 §6.2.4
- **Purpose:** NBO (Normal/Briefing/Ops), N, M (Military) — per ICAO Annex 15 Appendix 6 §6.2.5
- **Scope:** A (Aerodrome), E (En-route), W (Warning/airspace), AE (Aerodrome+En-route) — per §6.2.6
- **Lower/Upper:** 3-digit flight level (000-999). 000 = ground. 999 = unlimited.
- **Coordinates:** Approximate lat/lon of the relevant airport or area, formatted as DDDDNdddddErrr (latitude 4 digits + N/S, longitude 5 digits + E/W, radius 3 digits in NM). Values are representative, not precision-surveyed.

---

## Rule 3: A-Field (Location Indicator)

Real ICAO location indicators only. No fictional airport codes.
Multi-location A-fields (e.g. `A) KJFK KEWR`) use real co-located airports.

**Source:** FAA JO 7930.2S §3-3-3; ICAO Annex 15 §6.2.7

---

## Rule 4: B and C Field Date/Time Format

**Format:** YYMMDDHHmm (10 digits, UTC)
- YY: 2-digit year (26 = 2026)
- MM: 2-digit month
- DD: 2-digit day
- HH: 2-digit hour (00-23)
- mm: 2-digit minute (00-59)

All times are UTC per ICAO Annex 15 §6.2.2.

C-field suffixes:
- No suffix: firm end time
- EST suffix: estimated end time per FAA JO 7930.2S §3-3-2
- PERM: no planned end date per §3-3-2

**Construction rule:** B and C field times are constructed to either overlap or not overlap the scenario flight time window, to test whether the evaluating agent correctly applies the time_window_checker tool or equivalent temporal reasoning.

---

## Rule 5: D-Field (Schedule) Format

**Format:** `D) <days> <HHmm>-<HHmm>` (UTC)
- Example: `D) MON-FRI 0600-2200`
- Times are UTC unless explicitly stated otherwise (FAA JO 7930.2S §3-3-4)
- Used in Type A task NC-A-003 and Type D task NC-D-010

**Source:** FAA JO 7930.2S §3-3-4; ICAO Annex 15 §6.2.4

---

## Rule 6: E-Field (Plain Language Text) Contractions

All abbreviations in E-fields are drawn from FAA JO 7930.2S Appendix B (NOTAM contractions).
Full English is used when no standard contraction exists.

Contractions used in this family:
| Contraction | Meaning | Source |
|---|---|---|
| RWY | Runway | JO 7930.2S App B |
| TWY | Taxiway | JO 7930.2S App B |
| CLSD | Closed | JO 7930.2S App B |
| U/S | Unserviceable | JO 7930.2S App B |
| ACT | Active | JO 7930.2S App B |
| AVBL | Available | JO 7930.2S App B |
| LGTD | Lighted | JO 7930.2S App B |
| DIURNAL | Daylight-activated lighting | JO 7930.2S App B |
| BTN | Between | JO 7930.2S App B |
| OBST | Obstacle | JO 7930.2S App B |
| ELEV | Elevation (MSL) | JO 7930.2S App B |
| AGL | Above Ground Level | JO 7930.2S App B |
| AP | Airport | JO 7930.2S App B |
| ILS | Instrument Landing System | JO 7930.2S App B |
| GS | Glideslope | JO 7930.2S App B |
| LOC | Localizer | JO 7930.2S App B |
| PAPI | Precision Approach Path Indicator | JO 7930.2S App B |
| ATIS | Automatic Terminal Information Service | JO 7930.2S App B |
| TWR | Tower | JO 7930.2S App B |
| FREQ | Frequency | JO 7930.2S App B |
| APRON | Apron (ramp area) | JO 7930.2S App B |
| LGTG | Lighting | JO 7930.2S App B |

---

## Rule 7: FDC NOTAM Format

FDC (Flight Data Center) NOTAMs use the format: `FDC <serial>/<YY>`
FDC NOTAMs are used for:
- Instrument procedure amendments (raising minimums, suspending procedures)
- Regulatory/procedural changes

E-field uses the same contractions as D-NOTAMs.
FDC NOTAMs include the mandatory phrase `SEE NOTAM EFFECTIVE UNTIL CHART REVISION` when procedure changes await chart update.

**Source:** FAA JO 7930.2S §2-1-2 (FDC NOTAM type); FAA AIM §5-1-3

---

## Rule 8: TFR (Temporary Flight Restriction) NOTAM Format

TFRs are issued as FDC NOTAMs in the US.
E-field must include: restriction type, geographic center (lat/lon), radius, altitude band, and applicable CFR authority.

**Authorities used in tasks:**
- 14 CFR §91.137: Disaster/hazard TFR
- 14 CFR §91.141: Presidential/VIP TFR
- 14 CFR §91.145: Major events TFR

TFR coordinates are constructed to be geographically plausible for the named city but are not exact real TFR coordinates.

---

## Rule 9: Obstacle NOTAM Format

Format: `OBST <type> (ASN <year>-<region>-<num>-OE) <distance> <bearing> <airport> ELEV <nnnn>FT (<nnn>FT AGL) <lighting status>`

- ASN (Airspace Safety Number) is the FAA airspace determination number from FAA 7460-1 filings
- ASN numbers in tasks are NOTIONAL — they follow the format but do not reference real filings
- Elevation values are constructed to be consistent with the area's terrain elevation (airport MSL elevation + stated AGL height)
- Lighting status: LGTD = lighted; LGTD DIURNAL = daylight-activated

**Source:** FAA JO 7930.2S Appendix B (OBST, ELEV, AGL contractions); 14 CFR Part 77 (obstacle marking/lighting requirements)

---

## Rule 10: Braking Action NOTAM Format

Format: `BRAKING ACTION <level> <runway designator> <conditions>`
- Braking action levels: GOOD, GOOD TO MEDIUM, MEDIUM, MEDIUM TO POOR, POOR, NIL
- Level impacts landing distance calculations per FAA AC 91-6A
- Poor/nil braking requires significant landing distance additives (typically 40-100% of dry-runway stopping distance)

**Source:** FAA JO 7930.2S §3-8-4 (braking action NOTAM issuance); FAA AC 91-6A (performance factors)

---

## What Was NOT Done

1. **No real NOTAM data was extracted** from any API, database, or NOTAM management system
2. **No NOTAM series numbers are real** — all numbers (e.g., A1234/26) are notional and do not correspond to actual issued NOTAMs
3. **No ASN numbers are real** — all obstacle ASN numbers are constructed for format compliance only
4. **Airport coordinates** in Q-lines are approximate center-point representations, not precision obstruction survey data
5. **Instrument approach minima** used in Type D tasks are representative values for planning purposes — not extracted from current Jeppesen/NOS approach plates. Expert review must verify these values against current approach charts before NMI use.

---

## Review Requirement

Per `docs/expert_review_protocol.md` §2 and §7:
- All task cards carrying `provenance.license = "PILOT — NOT EXPERT-REVIEWED"` must pass expert review before entering the frozen test split
- Reviewer eligibility: For NOTAM compliance tasks, reviewers must hold FAA Part 65 dispatcher certificate, ATP certificate, or equivalent ICAO qualification (§2, Family 4)
- Specific items requiring priority expert review:
  - All Type D (agentic) gold decisions involving approach minimums — DA/MDA values must be verified against current charts
  - All Q-code assignments — subject/condition code accuracy requires dispatcher or ATC review
  - All regulatory citations — 14 CFR section numbers must be verified by a licensed attorney or qualified safety officer
