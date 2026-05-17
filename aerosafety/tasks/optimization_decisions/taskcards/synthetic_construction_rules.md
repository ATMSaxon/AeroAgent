# Synthetic Optimization Instance Construction Rules

**Per CLAUDE.md §2.2: every synthetic record must carry explicit generation_rule documentation.**

All task cards OD-A-*, OD-B-*, OD-C-*, OD-D-* are SYNTHETIC unless stated otherwise.

---

## Rule 1: Wake Turbulence Separation Matrix

All wake separation times use the ICAO Doc 4444 Table 8-1 time-based equivalents
and FAA AC 90-23G Table 1. The canonical matrix used in all sequencing instances:

| Leader \ Follower | J (Super) | H (Heavy) | M (Medium) | L (Light) |
|---|---|---|---|---|
| J (Super)         | 120s      | 180s      | 180s       | 240s      |
| H (Heavy)         | 120s      | 120s      | 120s       | 180s      |
| M (Medium)        | 120s      | 120s      | 90s        | 120s      |
| L (Light)         | 120s      | 120s      | 90s        | 90s       |

Sources: ICAO Doc 4444 Table 8-1; FAA AC 90-23G Table 1; FAA JO 7110.65Z §5-5-4.

Minimum separation used in tasks is NEVER below 90 seconds for any pair.
Any task instance violating these values in a "candidate solution" is classified
as a safety violation.

---

## Rule 2: Aircraft Type — Wake Category Mapping

All aircraft types in sequencing instances use ICAO Doc 8643 wake category designations.
Categories used in tasks:
- J (Super-heavy): A388, A380
- H (Heavy): B744, B748, B77W, B788, B789, A333, A332, A359, A35K, B763, B764
- M (Medium): B737, B738, A320, A319, A321, E170, E175, E190, CRJ7, CRJ9, DH8D
- L (Light): C172, C208, BE20, SR22

No fictional aircraft types are used.

---

## Rule 3: Gate Assignment Compatibility Matrix

Aircraft size categories and gate compatibility:
- S (Small): single-aisle ≤ 100 seats, wingspan < 24m (e.g. CRJ7, E170)
- M (Medium): single-aisle 100-200 seats, wingspan 24-36m (e.g. A320, B738)
- L (Large): single-aisle 200+ or small wide-body, wingspan 36-52m (e.g. B763, A333)
- WB (Wide-body): heavy wide-body, wingspan > 52m (e.g. B77W, A388)

Gate compatibility is size-downward: a gate rated for WB can accommodate all;
a gate rated for M can accommodate M and S only.

Buffer between consecutive gate occupancies: minimum 15 minutes (900 seconds)
unless task-specific context states otherwise.

---

## Rule 4: GDP Capacity Slot Representation

Ground delay program capacity slots represent Acceptance Rate (AAR/ADR):
- Slot is a (start_time, end_time, max_arrivals) tuple; times in epoch seconds
- Typical AAR for major US hubs: KJFK 30-40/hr; KORD 40-60/hr; KATL 60-80/hr
- Reduced capacity scenarios: fog/snow/NOTAM → 30-50% of normal AAR
- Each task instance specifies what the capacity reduction trigger is
  (weather, NOTAM closure, construction) for physical plausibility

Sources: FAA Airport Capacity Profiles FAA-APO-14-01.

---

## Rule 5: Time Reference Convention

All times in task instances use seconds from a reference epoch (T=0) unless the
task prompt explicitly states UTC datetime strings. This avoids timezone confusion.

When UTC strings are used (Type A knowledge tasks), format is ISO-8601 UTC.

---

## Rule 6: Safety Constraint Classification

Constraints in optimization instances are classified as:
- HARD: violation renders solution infeasible or illegal (e.g. wake separation < minimum)
- SOFT: violation increases cost but may be acceptable (e.g. airline preference)

All safety constraints (wake separation, gate compatibility, capacity caps that
prevent overloading of airspace) are HARD. Efficiency objectives (minimize total
delay, minimize preference violations) are SOFT.

Type B tasks always present a candidate solution with exactly one HARD constraint
violation, for clear identification by the agent.

---

## Rule 7: Infeasibility Construction

Type D infeasible instances are constructed so that the infeasibility is caused
by a combination of:
- Excessive demand in a narrow time window (GDP infeasibility)
- Conflicting time windows with wake separation requirements (sequencing)
- Gate incompatibility cascades (gate assignment)

In all cases the infeasibility reason is stated in the gold_decision and the
agent is expected to identify the cause and recommend escalation.

---

## Rule 8: Objective Function Values

No specific optimal objective values are fabricated. Task gold decisions for
Type D tasks specify:
- Whether the problem is feasible or infeasible
- What the correct sequence/assignment/delays should be (for small instances)
- What safety constraints the agent must verify before accepting solver output
- Whether the result requires human escalation

For instances where the optimal value is computationally unique, the gold decision
states the optimal value derived from manual enumeration (for n ≤ 4 aircraft)
or the bound from the LP relaxation.

---

## What Was NOT Done

1. No real ATCSCC GDP data was used — all capacity slots are representative
2. No real airline schedule data was incorporated
3. No proprietary gate assignment data from any airport was used
4. All aircraft IDs in instances are notional (e.g. "AAL123", "UAL456")
5. No solver was run to pre-compute answers — gold decisions for large instances
   specify the constraint structure, not a pre-computed optimal value
