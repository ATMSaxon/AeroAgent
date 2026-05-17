# Source Citations — NOTAM Compliance Task Family

All task cards in this family are derived from the following primary sources.
Every NOTAM presented in tasks is SYNTHETIC, constructed from format specifications
and public examples in these documents (see `synthetic_construction_rules.md`).

No live or archived NOTAM data was accessed via any API.
The FAA NOTAM API is off critical path (residency-restricted) and was NOT used.

---

## Primary Sources

### 1. FAA Order JO 7930.2S — Notices to Air Missions (NOTAMs)
- **URL:** https://www.faa.gov/regulations_policies/orders_notices/index.cfm/go/document.information/documentID/1038268
- **Sections used:**
  - §2-1-1: NOTAM definition and classification
  - §2-1-2: NOTAM type designators (D, L, FDC, SAA, GPS)
  - §2-1-3: NOTAM type codes N/R/C (New, Replacement, Cancellation)
  - §3-3-1 through §3-3-7: Field definitions (B through G fields)
  - Appendix A: Q-line field definitions (FIR, NOTAM code, traffic, purpose, scope, lower/upper, coordinates)
  - Appendix B: NOTAM contractions table (all contractions used in task E-fields: U/S, CLSD, ACT, AVBL, LGTD, DIURNAL, BTN, RWY, TWY, OBST, ELEV, AGL, APRON, LGTG, AP, TWR, ILS, GS, LOC, PAPI, ATIS, etc.)
- **Access date:** 2026-05-17 (public PDF, no registration required)
- **License:** U.S. Government public domain document

### 2. ICAO Annex 15 — Aeronautical Information Services, 16th Edition, 2018
- **URL:** https://www.icao.int/safety/information-management/Pages/Annex15.aspx
- **Sections used:**
  - §4.1: NOTAM origination timeliness requirements
  - §4.4: AIRAC cycle publication requirements
  - §6.1: NOTAM classification
  - §6.2.1 through §6.2.9: Q-line field definitions (FIR, subject/condition codes, traffic, purpose, scope, lower/upper limits, E-field character limits)
  - Appendix 6: Q-code taxonomy (all Q-codes used in task Q-lines were verified against this table or constructed from subject + condition code pairs that appear in the table)
- **Access date:** 2026-05-17 (publicly available ICAO product; free access version referenced from ICAO website)
- **License:** ICAO publication; cited under research/educational use per ICAO Annexes policy

### 3. FAA Order JO 7110.65Z — Air Traffic Control
- **URL:** https://www.faa.gov/regulations_policies/orders_notices/index.cfm/go/document.information/documentID/1038901
- **Sections used:**
  - §3-7-2: Runway use and closed runway procedures
  - §3-8-1: Noise abatement procedures
  - §3-8-4: Braking action reporting and NOTAM issuance
- **Access date:** 2026-05-17 (public PDF, no registration required)
- **License:** U.S. Government public domain document

### 4. 14 CFR Title 14 (Aeronautics and Space) — Electronic Code of Federal Regulations
- **URL:** https://www.ecfr.gov/current/title-14
- **Parts used:**
  - Part 61 §61.87: Student pilot solo requirements
  - Part 91 §91.3: PIC final authority
  - Part 91 §91.103: Preflight action (NOTAM check requirement)
  - Part 91 §91.126, §91.127, §91.129, §91.131: Airspace class operations requirements
  - Part 91 §91.133: Restricted area operations
  - Part 91 §91.137, §91.138, §91.141, §91.143, §91.145: TFR authorities
  - Part 91 §91.167: IFR fuel requirements (Part 91)
  - Part 91 §91.175: Instrument approach procedures
  - Part 121 §121.195: Landing limitations at destination
  - Part 121 §121.533: Operational control
  - Part 121 §121.601: Dispatcher responsibilities (NOTAM, weather)
  - Part 121 §121.617: Alternate airport weather minimums
  - Part 121 §121.625: Alternate airport requirements
  - Part 121 §121.639: IFR fuel requirements (Part 121)
  - Part 121 §121.651: Takeoff and landing weather minimums
  - Part 121 §121.703: Mechanical reliability reports
- **Access date:** 2026-05-17 (eCFR, public, no registration)
- **License:** U.S. Government public domain

### 5. FAA Aeronautical Information Manual (AIM)
- **URL:** https://www.faa.gov/air_traffic/publications/atpubs/aim_html/
- **Sections used:**
  - §1-1-13: GPS RAIM availability
  - §1-1-14: Laser and ultralight activity NOTAMs
  - §2-1-2: PAPI description
  - §3-2-4: Class D airspace entry requirements
  - §3-5-3: Temporary Flight Restrictions
  - §4-1-9: UNICOM and CTAF operations
  - §4-1-13: ATIS information
  - §5-1-3: NOTAM information (pilot briefing)
  - §5-4-5: ILS approach components
  - §5-6-2: Military intercept procedures
- **Access date:** 2026-05-17 (public HTML, no registration)
- **License:** U.S. Government public domain

### 6. FAA Advisory Circulars
- **AC 90-100A** — U.S. Terminal and En-route Area Navigation (RNAV) Operations (RAIM requirements)
  URL: https://rgl.faa.gov/Regulatory_and_Guidance_Library/rgAdvisoryCircular.nsf/0/4a0b585a0f3a4a60862573b40069d6a3/$FILE/AC90-100A.pdf
- **AC 90-105A** — Approval of RNAV and RNP Operations
  URL: https://rgl.faa.gov/Regulatory_and_Guidance_Library/rgAdvisoryCircular.nsf/0/9073aad8f15eb07086257cff006b0f31/$FILE/AC90-105A.pdf
- **AC 91-6A** — Water, Slush, Snow, and Ice on the Runway
  URL: https://rgl.faa.gov/Regulatory_and_Guidance_Library/rgAdvisoryCircular.nsf/0/24d02d04c94fad07852572500067b065/$FILE/AC91-6A.PDF
- **AC 120-28D** — Criteria for Approval of Category III Weather Minima for Takeoff, Landing, and Rollout
  URL: https://rgl.faa.gov/Regulatory_and_Guidance_Library/rgAdvisoryCircular.nsf/0/9f99bcf27aff14bf862577b8004ee0ac/$FILE/AC120-28D.pdf
- **AC 150/5220-22B** — Engineered Materials Arresting System (EMAS)
  URL: https://www.faa.gov/airports/resources/advisory_circulars/index.cfm/go/document.information/documentID/22497
- **Access date:** 2026-05-17 (public PDFs, no registration)
- **License:** U.S. Government public domain

### 7. FAA Order 7400.2 — Procedures for Handling Airspace Matters (Laser Strike Reporting)
- **URL:** https://www.faa.gov/regulations_policies/orders_notices/index.cfm/go/document.information/documentID/1038907
- **Access date:** 2026-05-17 (public, no registration)
- **License:** U.S. Government public domain

### 8. ICAO Doc 8126 — Aeronautical Information Services Manual
- **URL:** https://store.icao.int/products/aeronautical-information-services-manual-doc-8126 (purchase required for full text; cited sections from public ICAO summaries)
- **Section used:** §4.5 — AFTN message format constraints (character limits)
- **Residency restriction:** None (ICAO public catalogue)

### 9. ICAO Doc 10066 — NOTAM Format (Digital NOTAM / SNOWFLAKE Specification)
- **URL:** https://www.icao.int/airnavigation/informationmanagement/Pages/DigitalNOTAM.aspx
- **Access date:** 2026-05-17 (ICAO public information page)
- **License:** ICAO publication, cited under research use

---

## Airport and Airspace Identifiers Used

All airport ICAO identifiers (KORD, KMEM, KDEN, KCOS, KBOS, KLGA, PANC, VHHH, YSSY, EGLL, LFPG, LEMD, LSZH, EDDF, KLAS, KSJC, KSEA, KPHX, KSLC, KBWI, KATL, GMMN, etc.) refer to real airports. No fictional airport identifiers are used.

All ARTCC/FIR identifiers (KZAU, KZNY, KZBW, KZME, KZDV, KZAB, KZID, KZLA, KZSE, PAZA, EGTT, LFFF, LECM, EDWW, LSAS, RJJJ) refer to real control regions.

Coordinate values in Q-lines are approximate geographic coordinates consistent with the stated location but are not precision-surveyed values. They are constructed for parsability, not for navigation use.

---

## What is NOT cited here

- Live NOTAM data from any operational NOTAM API (FAA NOTAM system, ICAO SNOWFLAKE, Eurocontrol NM) — NOT used
- Any airport-specific chart minimums beyond what is stated in the task prompt (e.g., exact DA/MDA values used in Type D tasks were constructed to be representative of typical values; real instrument approach chart data was not systematically extracted)
- ATC separation data or real radar tracks
