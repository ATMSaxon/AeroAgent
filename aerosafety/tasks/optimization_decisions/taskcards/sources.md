# Source Citations — Optimization-Integrated Aviation Decisions (Family 9)

All task cards in this family are SYNTHETIC, constructed from the operational
constraints, formulations, and parameter values described in the sources below.
No proprietary airline or ATC operational data was used.

---

## Primary Optimization Literature

### 1. Bertsimas, D., & Patterson, S. S. (1998). The Air Traffic Flow Management Problem with Enroute Capacities
- **Authors:** Dimitris Bertsimas, Sarah Stock Patterson
- **Venue:** Operations Research, 46(3), 406–422
- **Year:** 1998
- **DOI:** https://doi.org/10.1287/opre.46.3.406
- **Sections used:**
  - §2: Integer programming formulation for runway sequencing with time windows
  - §3: Wake turbulence separation constraints as hard constraints in MIP
  - §4: Ground delay allocation as a resource-constrained scheduling problem
- **Use in tasks:** OD-A-001 through OD-A-008 (sequencing constraint knowledge), OD-B-001 through OD-B-008 (sequencing hazard identification), OD-D-001 through OD-D-005 (agentic sequencing decisions)

### 2. Vossen, T., & Ball, M. (2006). Optimization and Mediated Bartering Models for Ground Delay Programs
- **Authors:** Thomas Vossen, Michael Ball
- **Venue:** Naval Research Logistics, 53(1), 75–90
- **Year:** 2006
- **DOI:** https://doi.org/10.1002/nav.20126
- **Sections used:**
  - §2: Gate assignment as integer linear program with buffer constraints
  - §3: Equity constraints and airline-fairness in GDP allocation
  - §4: Ground delay program as resource allocation with slot assignments
- **Use in tasks:** OD-A-009 through OD-A-014 (gate assignment knowledge), OD-B-009 through OD-B-013 (gate conflict hazard), OD-D-006 through OD-D-009 (gate assignment decisions)

### 3. Atkins, S., & Brinton, C. (1998). Concept and Subsystem Architecture for a Surface Movement Advisor
- **Authors:** Stephen Atkins, Chester Brinton
- **Venue:** Proceedings of the 2nd USA/Europe ATM R&D Seminar, 1998
- **URL:** https://www.atmseminar.org/seminarContent/seminar2/papers/p_031_CDR.pdf
- **Sections used:**
  - §3: Arrival sequencing and delay assignment under runway capacity constraints
  - §4: Integration of wake turbulence separation with throughput optimisation
- **Use in tasks:** OD-A-015 through OD-A-018 (arrival sequencing knowledge), OD-C-001 through OD-C-006 (consequence prediction for unsafe sequencing)

### 4. Psaraftis, H. N. (1980). A Dynamic Programming Approach for Sequencing Groups of Identical Jobs
- **Authors:** Harilaos N. Psaraftis
- **Venue:** Operations Research, 28(6), 1347–1359
- **Year:** 1980
- **DOI:** https://doi.org/10.1287/opre.28.6.1347
- **Sections used:**
  - §2: Sequence-dependent setup times (analogous to wake-separation times between aircraft categories)
  - §3: Dynamic programming for exact sequencing under pairwise constraints
- **Use in tasks:** OD-A-005 through OD-A-007 (optimality vs constraint trade-off knowledge)

### 5. Odoni, A. R. (1987). The Flow Management Problem in Air Traffic Control
- **Authors:** Amedeo R. Odoni
- **Venue:** In: Odoni, A. R., Bianco, L., & Szegö, G. (Eds.), Flow Control of Congested Networks, Springer-Verlag, 269–288
- **Year:** 1987
- **DOI:** https://doi.org/10.1007/978-3-642-86726-2_12
- **Sections used:**
  - §1: GDP as a problem of allocating airport capacity slots to flights
  - §2: Equity vs efficiency trade-off in ground delay allocation
- **Use in tasks:** OD-A-019 through OD-A-024 (GDP knowledge), OD-B-014 through OD-B-018 (GDP constraint violation hazard)

### 6. Hoffman, R., & Ball, M. O. (2000). A Comparison of Formulations for the Single-Airport Ground-Holding Problem with Banking Constraints
- **Authors:** Ren Hoffman, Michael O. Ball
- **Venue:** Transportation Science, 34(3), 305–318
- **Year:** 2000
- **DOI:** https://doi.org/10.1287/trsc.34.3.305.12299
- **Sections used:**
  - §2: LP relaxation and rounding for GDP with airline equity constraints
  - §3: Capacity slot representation and compression
- **Use in tasks:** OD-A-020 through OD-A-024 (GDP constraint and equity knowledge), OD-D-010 through OD-D-013 (GDP agentic decisions)

### 7. Yan, S., & Huo, C.-M. (1996). Optimization of Multiple Objective Gate Assignments
- **Authors:** Shangyao Yan, Cheng-Min Huo
- **Venue:** Transportation Research Part A: Policy and Practice, 30(5), 369–383
- **Year:** 1996
- **DOI:** https://doi.org/10.1016/0965-8564(95)00028-3
- **Sections used:**
  - §2: Gate assignment as 0-1 integer program with compatibility and overlap constraints
  - §3: Aircraft size compatibility matrix (S/M/L/WB) for gate assignments
- **Use in tasks:** OD-A-010 through OD-A-014 (gate assignment knowledge), OD-B-009 through OD-B-013 (gate conflict identification)

---

## Aviation Regulatory Sources

### 8. ICAO Doc 4444 PANS-ATM, 16th Edition, 2018 — Procedures for Air Navigation Services: Air Traffic Management
- **URL:** https://www.icao.int/safety/airnavigation/Pages/pans-atm.aspx
- **Sections used:**
  - §8.7.3: Wake turbulence separation minima on approach (Heavy/Medium/Light categories)
  - Table 8-1: ILS approach wake turbulence separation distances (nm) and time-based equivalents (seconds)
  - §6.8: Ground delay and slot allocation procedures
- **Access date:** 2026-05-17 (ICAO public catalogue)
- **License:** ICAO publication, cited under research/educational use

### 9. FAA Order JO 7110.65Z — Air Traffic Control
- **URL:** https://www.faa.gov/air_traffic/publications/atpubs/atc_html/
- **Sections used:**
  - §5-5-4: Wake turbulence separation minima (Heavy/Large/Small aircraft categories)
  - §7-4-3: Runway separation — simultaneous operations
  - §3-10-3: Ground delay program procedures (EDCT)
- **Access date:** 2026-05-17 (public HTML, no registration)
- **License:** U.S. Government public domain

### 10. FAA Order JO 7210.3 — Facility Operation and Administration (Traffic Flow Management)
- **URL:** https://www.faa.gov/regulations_policies/orders_notices
- **Sections used:**
  - §17-1: ATCSCC Ground Delay Program (GDP) initiation criteria
  - §17-2: Controlled Departure Time (CDT) assignment
  - §17-3: EDCT message format and interpretation
- **Access date:** 2026-05-17 (public, no registration)
- **License:** U.S. Government public domain

### 11. FAA Advisory Circular AC 90-23G — Aircraft Wake Turbulence
- **URL:** https://rgl.faa.gov/Regulatory_and_Guidance_Library/rgAdvisoryCircular.nsf/0/f1d08474c0d0e7e8862578ae005dff2c/$FILE/AC90-23G.pdf
- **Sections used:**
  - §4: Wake vortex generation and characteristics by aircraft category
  - §7: Operational procedures — minimum separation by aircraft pair (Heavy behind Heavy, Large behind Heavy, etc.)
  - Table 1: Time-based wake turbulence separation intervals
- **Access date:** 2026-05-17 (public PDF, no registration)
- **License:** U.S. Government public domain

### 12. EUROCONTROL — Common Occurrence Reporting (COR) Wake Turbulence Encounter Database
- **URL:** https://www.eurocontrol.int/publication/wake-turbulence-encounter-database
- **Sections used:**
  - Operational context for wake turbulence near-miss scenarios used in Type C tasks
- **Access date:** 2026-05-17 (EUROCONTROL public publication)
- **License:** EUROCONTROL, cited under research use

### 13. FAA Airport Capacity Profiles (FAA-APO-14-01)
- **URL:** https://www.faa.gov/airports/planning_capacity/profiles
- **Sections used:**
  - Typical airport arrival/departure capacities used to construct GDP instances
  - Representative acceptance rate values for major U.S. hub airports
- **Access date:** 2026-05-17 (public, no registration)
- **License:** U.S. Government public domain

---

## Aircraft Type Data

### 14. ICAO Doc 8643 — Aircraft Type Designators
- **URL:** https://www.icao.int/safety/vleap/Pages/Doc-8643.aspx
- **Sections used:**
  - Wake turbulence category (L/M/H/J) for all aircraft type designators used in tasks
- **Access date:** 2026-05-17 (ICAO public online database)
- **License:** ICAO public data

---

## What Is NOT Cited Here

- Real airline schedule data or operational CDTs from any ATCSCC GDP
- Proprietary MEL, gate assignment, or slot allocation data from any airline
- Any real-time or archived ETMS/TFMS data
- Jeppesen or NOS approach chart data
- Any solver output from a real operational traffic management system

All optimization instances are SYNTHETIC, constructed to be physically plausible
and operationally realistic per the sources above, but they do not represent any
actual historical or live traffic management decision.

---

## Expert Review Requirement

Per `docs/expert_review_protocol.md` §2 Family 9:
- OR/aviation researcher co-review required for task formulation correctness
- ATC/dispatcher co-review required for operational realism and gold decisions
- All task cards carry `provenance.license = "PILOT — NOT EXPERT-REVIEWED"` until reviewed
