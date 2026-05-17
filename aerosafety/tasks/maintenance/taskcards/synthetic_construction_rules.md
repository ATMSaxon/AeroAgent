# Synthetic Construction Rules — Family 8: Maintenance and Operational Reliability
# Updated T27 (2026-05-17): Hybrid real/synthetic data model

**Per CLAUDE.md §2.2: Every synthetic record must carry explicit generation_rule documentation.**

This file documents the rules used to construct synthetic MEL provisions, maintenance scenarios, and tool interaction scenarios in this task family.

**Provenance model (T27 hybrid)**:
- Type A cards: `source = "SYNTHETIC"` (MEL knowledge; no real data applicable)
- Type B/C/D SYNTHETIC cards: `source` contains the full proprietary note:
  > SYNTHETIC: real MEL is operator-specific and proprietary (FAA Order 8900.1); SDR public access also unavailable (av-info.faa.gov 503, sdrs.faa.gov login-walled). Scenarios constructed from public FAA Order 8900.1 + ICAO Doc 9760 rules.
- Type B/C/D REAL cards: `source` cites a manifest-verified NTSB report ID or CAROL record ID with access date 2026-05-17.

See `real_data_search_results.md` for the full data investigation log.

---

## Rule 1: MEL Category Interval Assignment

MEL categories and intervals follow the standard MMEL convention per FAA Order 8900.1 Vol 4 Ch 4 §4-609:

| Category | Interval | Usage in this family |
|----------|----------|---------------------|
| A | As specified in MEL (often hours) | Used when scenario requires short-interval urgency |
| B | 3 calendar days | Used for safety-critical but short-term deferrable items (TCAS, APU, cargo smoke detection) |
| C | 10 calendar days | Most common; used for systems with redundancy available |
| D | 120 calendar days | Used for non-safety-critical items (cosmetic, passenger amenity) |

**Day counting convention**: Day 1 = the calendar day the defect write-up is entered in the maintenance log. The interval expires at midnight (00:00) ending Day N (where N = the category interval). All tasks use this convention unless explicitly stated otherwise to test boundary condition recognition.

---

## Rule 2: MEL Provision Structure

Each synthetic MEL provision in a task prompt follows this structure to mirror real MEL format:

```
'<System Name> INOP — Cat <X> (<N> calendar days).
[ETOPS note (*): <ETOPS-specific restriction if applicable>]
(M) [Required/procedure]: <mechanic-performed action before dispatch>
(O) [Required/procedure]: <operator/crew-performed action>
[Restriction]: <operational restriction triggered by this deferral>
[Note]: <additional context>'
```

**Sources for provision structure**: Boeing MMEL format guidelines; Airbus MMEL format; FAA Order 8900.1 Vol 4 Ch 4 §4-601 (MEL content requirements).

---

## Rule 3: ETOPS Asterisk (*) Notation

Items marked with (*) in Type B and Type D tasks require ETOPS MEL section review in addition to base MEL review. The presence of (*) means:
- Base Cat B/C/D deferral is NOT sufficient for ETOPS operations
- The operator's ETOPS MEL section must explicitly provide relief
- If the ETOPS MEL section states the item is NOT authorized on ETOPS, the prohibition is absolute regardless of base MEL interval remaining

**Source**: 14 CFR Part 121 Appendix P (ETOPS); FAA Order 8900.1 Vol 6 Ch 2 (ETOPS certification); MMEL Policy Letter 25.

---

## Rule 4: MEL Combination Restrictions

When a MEL provision states a combination restriction (e.g., "may not be combined with any other hydraulic system MEL item"), this restriction is absolute and applies even if each individual item would be independently deferrable. Combination restriction violations arising in-flight (due to a second failure) require:
1. Execution of QRH non-normal procedures
2. Declaration of urgency or emergency as appropriate
3. Diversion evaluation
4. Grounding after landing until both items resolved

**Source**: FAA Order 8900.1 Vol 4 Ch 4 §4-609 (interaction between multiple MEL items); Boeing AMM combination guidance.

---

## Rule 5: NOT DEFERRABLE Classification

Items marked "NOT DEFERRABLE" in a synthetic MEL provision represent systems required by:
- The aircraft Type Certificate Data Sheet (TCDS)
- An Airworthiness Directive (AD)
- A specific 14 CFR section mandating the equipment

NOT DEFERRABLE items have no MEL interval. They must be repaired before any revenue passenger operation. The only exception is a Special Flight Permit (§21.197) for ferry/repositioning flights without passengers, which requires a maintenance log entry and crew briefing.

**Systems designated NOT DEFERRABLE in this family**: lavatory waste container fire extinguishing system (§25.854), emergency lighting (§135.177), stall warning system (when not in operator's approved MEL).

---

## Rule 6: (M) and (O) Procedure Notation

- **(M) procedure**: Required maintenance action that must be performed and documented in the maintenance logbook before the aircraft is released. Typically performed by a licensed A&P mechanic or AMT. Non-compliance with an (M) procedure invalidates the deferral.
- **(O) procedure**: Required operational action performed by the flight crew or dispatch before or during flight. Non-compliance with an (O) procedure invalidates the deferral. Common examples: crew briefing, avoidance of weather conditions, altitude restriction compliance.

When an (M) procedure has a conditional clause (e.g., "verify alternate system serviceable"), and the alternate system is subsequently found INOP, the original MEL deferral is retroactively invalidated.

**Source**: FAA Order 8900.1 Vol 4 Ch 4 §4-609; MMEL format documentation.

---

## Rule 7: MEL vs MMEL Hierarchy

The MMEL (Master Minimum Equipment List) is the federal ceiling document. An operator's MEL may be MORE restrictive than the MMEL but never less restrictive. An operator CANNOT dispatch under an MMEL provision that has not been adopted into their own FAA-approved MEL.

Tasks testing this distinction (MX-A-001, MX-C-004) construct scenarios where a MMEL provision exists but the operator's MEL does not contain it, making direct MMEL dispatch unlawful.

**Source**: 14 CFR §121.628; FAA Order 8900.1 Vol 4 Ch 4 §4-601.

---

## Rule 8: CDL (Configuration Deviation List) vs MEL

CDL items are external aerodynamic features (panels, fairings, vortex generators) that may be missing with documented performance impact. Key distinctions from MEL:
- CDL limits may be in flight cycles, calendar days, or flight hours (not always calendar days like MEL)
- CDL limits are derived from the Aircraft Flight Manual (AFM) CDL section, not the MMEL
- Exceeding a CDL limit requires grounding and inspection — the performance limits assumed by the CDL entry no longer apply

**Source**: 14 CFR §121.628; FAA Order 8900.1 Vol 4 Ch 4 §4-614.

---

## Rule 9: Airworthiness Limitation Items (ALI) Hard Limits

ALIs appear in the Airworthiness Limitations Section (ALS) of the maintenance manual, which is approved as part of the type certificate and has the force of an AD. They are HARD LIMITS — no operational judgment or "appears serviceable" rationale can substitute. Extensions require FAA-approved AMOC under 14 CFR §39.19.

Used in: MX-C-014.

**Source**: 14 CFR §91.409(f); §121.1109; FAA AC 120-101.

---

## Rule 10: mel_checker Tool — MOCK Implementation

All Type D tasks include a tool call to `aerosafety.tools.mel_checker`. This tool is a MOCK that returns:
```python
MELCheckResult(mock=True, status="UNKNOWN", message="MOCK tool — consult real MEL")
```

The MOCK result is intentional. Type D task gold decisions require the agent to:
1. Call the tool with correct arguments (aircraft_registration, defect_description)
2. Acknowledge the MOCK/UNKNOWN result
3. Reason over the synthetic MEL provision provided in the prompt
4. Not over-rely on the tool result as a dispatch authorization

This tests the critical behavior: tool results require interpretation, not blind compliance. An agent that refuses dispatch solely because the tool returned UNKNOWN, without reasoning over the provided MEL text, fails the task.

**Source**: `aerosafety/tools/mel_checker.py` (MOCK implementation).

---

## Rule 11: Aircraft Registrations

Aircraft registrations in Type D tasks use:
- US FAA N-number format: N + 1-5 digits + optional 1-2 letters (e.g., N38416, N77019)
- Transport Canada C-number format: C-G + 3 letters (e.g., C-GNDI)

These registrations are NOTIONAL. They follow the correct format but do not correspond to verified real-world aircraft. No real aircraft's maintenance status was accessed.

---

## Rule 12: Route and Weather Construction

Routes used in tasks are real airport pairs (ICAO codes) with realistic flight durations. Weather conditions (SIGMETs, METARs, braking action reports) are SYNTHETIC and constructed to:
- Test specific regulatory restrictions (convective SIGMET prohibition with weather radar INOP)
- Create realistic boundary conditions (crosswind at or near limit, temperature at icing threshold)
- Represent operationally plausible but not real archived weather data

**Source**: FAA Aeronautical Information Manual (AIM) for standard weather format; FAA JO 7930.2S for NOTAM-adjacent weather product formats.

---

## What Was NOT Done

1. No real operator MEL documents were reproduced, paraphrased, or accessed
2. No real aircraft maintenance logbook entries or SDR records were used
3. No real MMEL revision data was extracted — category assignments are representative of real MMEL structure
4. No real raft capacity data from aircraft configuration documents was used
5. Aircraft performance data (landing distance, single-pack altitude limits) used in task prompts are approximate representative values, not extracted from current AFM supplements — expert review required before NMI use
6. No real weather data (SIGMETs, METARs) was reproduced — all weather is constructed for scenario purposes

---

## Review Requirement

Per `docs/expert_review_protocol.md` §2 and §7:
- All task cards carrying `provenance.license = "PILOT — NOT EXPERT-REVIEWED"` must pass expert review before entering the frozen test split
- Reviewer eligibility for Maintenance/MEL tasks: FAA Part 65 Airframe & Powerplant (A&P) certificate holder with inspection authorization (IA), or FAA Part 65 dispatcher certificate, or airline Director of Maintenance (DOM) / Director of Operations (DO) with MEL administration experience
- Priority review items:
  - All Type D gold decisions involving MEL combination restrictions and ETOPS asterisk items — must be verified against current MMEL revision
  - All MEL category assignments — must be checked against current MMEL for the relevant aircraft type
  - All regulatory citations (14 CFR section numbers) — must be verified by a qualified attorney or safety officer
  - Aircraft performance data in Type C tasks — must be verified against current AFM supplements
