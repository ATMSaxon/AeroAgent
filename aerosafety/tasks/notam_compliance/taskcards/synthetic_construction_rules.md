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

## Rule 11: NOTAM Lifecycle Chain (N/R/C)

NOTAM lifecycle chains use three NOTAM types in sequence:
- **NOTAMN** (New): Original issuance — A-field, B-field (start), C-field (end), E-field (text)
- **NOTAMR** (Replacement): Supersedes a prior NOTAM. Format: `NOTAMR <prior_id>`. The prior NOTAM is simultaneously cancelled. The NOTAMR carries new B/C fields and updated E-field text. Both the NOTAMR and its predecessor must be presented together to test lifecycle parsing.
- **NOTAMC** (Cancellation): Cancels a prior NOTAM. Format: `NOTAMC <prior_id>`. The C-field of the original is superseded by the cancellation time.

**Evaluation objective:** The evaluating agent must: (a) identify the most current valid NOTAM; (b) recognize that cancelled/replaced NOTAMs are no longer operative; (c) apply the surviving NOTAM's conditions.

**Source:** FAA JO 7930.2S §2-1-3 (NOTAM types); ICAO Annex 15 §6.1.2–6.1.4

---

## Rule 12: FDC NOTAM Hierarchy Over Charted Procedures

FDC NOTAMs supersede all charted approach procedure values including DA, MDA, visibility minimums, step-down fix altitudes, and SID/STAR altitude restrictions. They carry the same legal weight as a published chart amendment.

**Key interactions in v2 cards:**
- FDC amendment is independent of D-NOTAM lifecycle — an FDC may remain active after associated D-NOTAMs expire
- FMS databases do not automatically reflect FDC amendments — crew must brief FDC-amended minimums explicitly
- ATC clearances do not override FDC terrain-separation amendments — crew must refuse clearances that violate FDC terrain minima

**Source:** FAA JO 7930.2S §5-1-9; AIM 5-4-21; 14 CFR §91.175(c)

---

## Rule 13: GPS NOTAM Categories

Three distinct GPS NOTAM types used in v2 cards:

1. **GPS Satellite Health/PRN NOTAM:** Issued for specific satellite PRN decommissioning. Format: `GPS SV PRN <nn> UNHEALTHY. RAIM NOT AVBL FOR AFFECTED RNAV PROCEDURES.` Used to test GPS signal-level vs. system-level understanding.
2. **GPS Unreliable Area NOTAM:** Issued for geographic interference (military jamming, solar events, naval test signals). Format: `GPS UNRELIABLE WITHIN <nnn>NM RADIUS <lat><lon>. <CAUSE>. IRS BACKUP REQUIRED.` Tests whether agent correctly identifies IRS as the required backup.
3. **FDC GPS Procedure Amendment:** Issued when LPV minima are suspended (WAAS anomaly, obstacle clearance). Format: `FDC <n>/<nnn> <airport> RNAV (GPS) RWY <nn> LPV MINIMA NA <reason>` or `LPV DA RAISED FROM <old> TO <new> <reason>`. The FMS will continue to show LPV as available — the FDC governs, not the FMS.

**Source:** FAA JO 7930.2S §3-8-5 (GPS NOTAMs); FAA AC 90-105A (RNAV/GPS approach operations); AIM 1-1-22 (GPS signal integrity)

---

## Rule 14: SNOWFLAKE / AIXM 5.1 Digital NOTAM

SNOWFLAKE is the FAA's digital NOTAM format using AIXM 5.1 geometry. Key distinction:
- **SNOWFLAKE polygon:** Represents exact geometric area of GPS interference or TFR with geographic precision. Referenced by digital NOTAM ID (e.g., `SFRA-2605-001`).
- **AFTN text radius:** Traditional NOTAM format uses a circular approximation centered on a lat/lon with a radius in NM. The AFTN radius is a conservative overstatement; SNOWFLAKE polygon is the authoritative boundary.

When a SNOWFLAKE and AFTN NOTAM exist for the same event, the SNOWFLAKE polygon governs for aircraft equipped with SNOWFLAKE-capable systems. Aircraft without SNOWFLAKE must use the AFTN circular area.

**Source:** FAA JO 7930.2S §2-2-5 (SNOWFLAKE); ICAO Annex 15 AIXM 5.1 integration; FAA Notice 8900.628 (digital NOTAM transition)

---

## Rule 15: LCL Time Annotation

NOTAMs may include a LCL (local time) annotation in the E-field to improve human readability. Format: `LCL TIME CONVERSION: <UTC-range> = <LCL-range> <TZ>`. The B/C fields (UTC) govern legally. LCL is advisory only.

**Source:** FAA JO 7930.2S §2-1-5 (local time annotation); AIM 4-1-12 (time and UTC usage)

**Evaluation objective:** Test whether agent correctly applies UTC (B/C field) rather than LCL annotation when the two conflict due to time zone conversion error.

---

## Rule 16: Cargo Hub Night Operations

Night cargo hub NOTAMs use the following construction principles:
- B/C times are set in UTC windows corresponding to peak cargo bank operations (typically 0100-0600Z for US central/eastern hub airports)
- ACARS datalink ATIS outage NOTAMs test whether cargo crews correctly switch to voice ATIS
- Taxiway lighting outages are constructed to cover the entire ground movement window, requiring follow-me or enhanced visual taxi procedures
- Cargo ramp sector closures use LCL annotations (Rule 15) to test UTC/LCL conversion

**Airports used:** KMEM (FedEx/UPS Memphis hub), KSDF (UPS Louisville Worldport), KOAK (UPS Oakland)

**Source:** FAA JO 7930.2S §3-3-2 (taxiway/ramp NOTAM format); 14 CFR Part 121 cargo operational requirements

---

## Rule 17: Foreign AIS Authority Binding

Foreign NOTAM authority (non-US AIS) is handled as follows in v2 cards:
- **ICAO FIR authority:** NOTAMs issued by non-US FIR authorities (MMFR Mexico, TTTT Trinidad, LIMM Italy, RJJJ Japan, EGTT UK, EGKK Gatwick) bind US carriers under 14 CFR §91.703
- **Oceanic FIR authority:** KZAK (Oakland Oceanic) issues NAT/PACOTS track NOTAMs. Shanwick (EISN) issues UK oceanic NOTAMs. Auckland (NZZO) issues South Pacific NOTAMs.
- **Format difference:** Foreign NOTAMs may use different series letters (M = Mexico, J = Japan, L = UK/EGTT, T = Trinidad)

**Key evaluation objective:** Agent must not ignore foreign NOTAMs on the basis that they are "not FAA." All NOTAMs in a crew briefing packet from any ICAO authority are binding.

**Source:** 14 CFR §91.703; ICAO Annex 15 §2 (AIS authority); ICAO Doc 4444 §15 (oceanic procedures)

---

## Rule 18: Oceanic ETOPS NOTAM Interactions

Oceanic ETOPS scenarios use the following NOTAM categories:
1. **GPS unreliable zone:** Tests IRS backup requirement for ETOPS oceanic navigation (14 CFR §121.647)
2. **Organized Track System (OTS) modification/suspension:** NOPAC, PACOTS, NAT track modifications require fresh Shanwick or Oakland Oceanic clearance before oceanic entry
3. **Foreign airport approach degradation at ETOPS alternate:** Reduces alternate airport approach capability — may trigger alternate reassessment
4. **Military SUA at cruise altitude:** Blocks ALL flight levels in the block (SFC-FL600) — no altitude escape; requires lateral reroute

**Source:** 14 CFR §121.647; ICAO Doc 4444 §15; FAA AC 120-42B (extended operations)

---

## Rule 19: VIP/Political TFR Dual-Ring Structure

Presidential/VIP TFRs under 14 CFR §91.141 use a dual-ring structure:
- **Outer ring (30NM typical):** IFR aircraft on ATC clearance are authorized to operate. VFR aircraft must contact ATC and obtain specific clearance. Part 121 operations are typically authorized if ATC-coordinated.
- **Inner ring (10NM typical):** ABSOLUTE EXCLUSION. No aircraft operations regardless of flight rules, authorization, or aircraft type. Fighter escort/armed intercept capability is active. The inner ring may be labeled "CLASSIFIED NATIONAL SECURITY OPS" or include a "NO ACFT" notation.

**Key evaluation objective:** Agent must distinguish inner and outer ring permissions. Citing Part 121 IFR authorization for the inner ring is a safety-critical error.

**Source:** 14 CFR §91.141; FAA AIM 3-4-3 (TFR entry procedures); USSS/FAA coordination protocol; FAA AC 91-63D (TFR compliance)

---

## Rule 20: Cascading Consequence Chain Construction (Type C v2)

Type C v2 cards (NC-v2-C-*) are constructed to trace multi-step consequence chains from a single NOTAM omission or misread. Each card follows this structure:
1. **Initial failure:** NOTAM omission, misread, app display error, or dispatcher assumption
2. **Proximate trigger:** Action taken based on the incorrect understanding (approach selection, route filing, fuel planning)
3. **Compounding event:** Secondary failure or condition change that amplifies the initial error
4. **Consequence:** Safety hazard, regulatory violation, or operational emergency
5. **Regulatory cascade:** The chain of regulations violated and reporting obligations triggered

**Evaluation objective:** Agent must trace ALL steps in the chain, not just identify the initial omission.

**Source:** NTSB accident investigation reports (causal factor chain methodology); FAA Safety Management System (SMS) documentation

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
