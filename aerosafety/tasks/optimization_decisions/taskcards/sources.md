# Source Citations — Optimization-Integrated Aviation Decisions (Family 9)

Type A task cards are SYNTHETIC, constructed from operational constraints and
formulations described in the primary OR literature below.

Type B and Type D task cards are grounded in real OR-Library benchmark instances
(Beasley 1990 doi:10.2307/2582903) downloaded to `data/raw/OR_LIBRARY/2026-05-17/`.

Type C task cards are grounded in real US carrier on-time performance data from
BTS Transtats, downloaded to `data/raw/BTS_ONTIME/2026-05-17/`.

---

## Primary Optimization Literature

### 1. Beasley, J. E. (1990). OR-Library: distributing test problems by electronic mail
- **Authors:** John E. Beasley
- **Venue:** Journal of the Operational Research Society, 41(11), 1069–1072
- **Year:** 1990
- **DOI:** https://doi.org/10.2307/2582903
- **Notes:** Source of the 20 crew scheduling benchmark instances (csp1–csp24) used
  in Type B and Type D task cards. Each instance is a Set Covering Problem encoding
  m candidate crew pairings over n required flight legs. Instance files are at
  `data/raw/OR_LIBRARY/2026-05-17/cspN.txt`.
- **Instance dimensions used:**
  - csp1.txt / csp2.txt: m=100 pairings, n=955 flight legs (~13 KB each)
  - csp3.txt / csp4.txt: m=100 pairings, n=959 flight legs (~12 KB each)
  - csp6.txt: m=100 pairings, n=990 flight legs (~38 KB)
  - csp7.txt / csp8.txt: m=100 pairings, n=999 flight legs (~32 KB each)
  - csp9.txt: m=200 pairings, n=2040 flight legs (~31 KB)
  - csp11.txt / csp12.txt: m=200 pairings, n=1971 flight legs (~26 KB each)
  - csp13.txt / csp14.txt: m=200 pairings, n=2080 flight legs (~82 KB each)

### 2. Bertsimas, D., & Patterson, S. S. (1998). The Air Traffic Flow Management Problem with Enroute Capacities
- **Authors:** Dimitris Bertsimas, Sarah Stock Patterson
- **Venue:** Operations Research, 46(3), 406–422
- **Year:** 1998
- **DOI:** https://doi.org/10.1287/opre.46.3.406
- **Sections used:**
  - §2: Integer programming formulation for runway sequencing with time windows
  - §3: Wake turbulence separation constraints as hard constraints in MIP
  - §4: Ground delay allocation as a resource-constrained scheduling problem
- **Use in tasks:** OD-A-001 through OD-A-008 (sequencing constraint knowledge),
  OD-B-001 through OD-B-004 (sequencing hazard), OD-D-001 through OD-D-005

### 3. Vossen, T., & Ball, M. (2006). Optimization and Mediated Bartering Models for Ground Delay Programs
- **Authors:** Thomas Vossen, Michael Ball
- **Venue:** Naval Research Logistics, 53(1), 75–90
- **Year:** 2006
- **DOI:** https://doi.org/10.1002/nav.20126

### 4. Atkins, S., & Brinton, C. (1998). Concept and Subsystem Architecture for a Surface Movement Advisor
- **Authors:** Stephen Atkins, Chester Brinton
- **Venue:** Proceedings of the 2nd USA/Europe ATM R&D Seminar, 1998

### 5. Psaraftis, H. N. (1980). A Dynamic Programming Approach for Sequencing Groups of Identical Jobs
- **Authors:** Harilaos N. Psaraftis
- **Venue:** Operations Research, 28(6), 1347–1359
- **DOI:** https://doi.org/10.1287/opre.28.6.1347

### 6. Odoni, A. R. (1987). The Flow Management Problem in Air Traffic Control
- **Authors:** Amedeo R. Odoni
- **Venue:** In: Odoni et al. (Eds.), Flow Control of Congested Networks, Springer, 269–288
- **DOI:** https://doi.org/10.1007/978-3-642-86726-2_12

### 7. Hoffman, R., & Ball, M. O. (2000). A Comparison of Formulations for the Single-Airport Ground-Holding Problem with Banking Constraints
- **Authors:** Ren Hoffman, Michael O. Ball
- **Venue:** Transportation Science, 34(3), 305–318
- **DOI:** https://doi.org/10.1287/trsc.34.3.305.12299

### 8. Yan, S., & Huo, C.-M. (1996). Optimization of Multiple Objective Gate Assignments
- **Authors:** Shangyao Yan, Cheng-Min Huo
- **Venue:** Transportation Research Part A, 30(5), 369–383
- **DOI:** https://doi.org/10.1016/0965-8564(95)00028-3

---

## Real Operational Data Sources

### 9. BTS Transtats — On-Time Performance (Reporting Carrier)
- **Source:** U.S. Bureau of Transportation Statistics
- **URL:** https://transtats.bts.gov/PREZIP/
- **Files downloaded:**
  - `data/raw/BTS_ONTIME/2026-05-17/BTS_OnTime_2024_07.zip` (July 2024, 34.4 MB)
  - `data/raw/BTS_ONTIME/2026-05-17/BTS_OnTime_2024_08.zip` (Aug 2024, 30.9 MB)
  - `data/raw/BTS_ONTIME/2026-05-17/BTS_OnTime_2024_09.zip` (Sep 2024, 28.4 MB)
  - `data/raw/BTS_ONTIME/2026-05-17/BTS_OnTime_2024_10.zip` (Oct 2024, 29.4 MB)
- **Access date:** 2026-05-17
- **License:** U.S. Government public domain (BTS Transtats open data)
- **Use in tasks:** Type C consequence chain cards — real EWR GDP events on
  2024-07-22 (avg NAS delay 39 min, 61 cancellations) and 2024-09-02
  (avg NAS delay 32 min, 20 cancellations); ORD 2024-08-27 GDP event.

---

## Aviation Regulatory Sources

### 10. ICAO Doc 4444 PANS-ATM, 16th Edition, 2018
- **Sections used:** §8.7.3, Table 8-1 (wake turbulence separation), §6.8 (GDP slots)
- **License:** ICAO publication, cited under research/educational use

### 11. FAA Order JO 7110.65Z — Air Traffic Control
- **Sections used:** §5-5-4 (wake separation), §3-10-3 (EDCT)
- **License:** U.S. Government public domain

### 12. FAA Order JO 7210.3 — Traffic Flow Management
- **Sections used:** §17-1 through §17-3 (GDP initiation, CDT, EDCT)
- **License:** U.S. Government public domain

### 13. FAA Advisory Circular AC 90-23G — Aircraft Wake Turbulence
- **Sections used:** §4, §7, Table 1 (time-based separation intervals)
- **License:** U.S. Government public domain

### 14. ICAO Doc 8643 — Aircraft Type Designators
- **Use:** Wake turbulence category (L/M/H/J) for all ICAO type designators
- **License:** ICAO public data

---

## Expert Review Requirement

Per `docs/expert_review_protocol.md` §2 Family 9:
- OR/aviation researcher co-review required for task formulation correctness
- ATC/dispatcher co-review required for operational realism and gold decisions
- All task cards carry `provenance.license = "PILOT — NOT EXPERT-REVIEWED"` until reviewed
