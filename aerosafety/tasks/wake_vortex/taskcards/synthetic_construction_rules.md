# Synthetic Construction Rules — Family 7: Wake Vortex / Separation Safety

## Hard Rules (CLAUDE.md §1.1, §8.1)

1. **No fabricated aircraft types.** Only use ICAO type designators that appear in `aerosafety/tools/wake_category_checker.py` `_WAKE_TABLE`. Any type not in that table must not appear in any task card.
2. **No fabricated separation minima.** All NM distances must be directly sourced from FAA JO 7110.65Z §5-5-4 through §5-5-9 or ICAO Doc 4444 §5.8. Do not invent or interpolate minima.
3. **No fake NOTAM text, controller phraseology, or radar data.** Synthetic scenario text must be written to represent a realistic situation without reproducing any specific real operational record.
4. **Provenance is SYNTHETIC** for all cards. `access_date` is null. No card may claim real incident data.
5. **No silent failure.** Every card with a wrong answer option must include it as a named failure_mode_label from the failure_taxonomy.

## Wake Category Lookup Table (ICAO Doc 8643)

| Category | Code | MTOW | Examples |
|----------|------|------|---------|
| Super | J | ≥560,000 kg | A388, A389 |
| Heavy | H | ≥136,000 kg | B744, B748, B772, B773, B77L, B77W, B778, B779, B788, B789, B78X, A332, A333, A359, A35K, B762, B763, B764, DC10, MD11 |
| Medium | M | 7,000–135,999 kg | A320, A321, A319, A318, B738, B739, B737, B736, B735, B733, B752, B753, CRJ7, CRJ9, E190, E195, DH8D, AT72 |
| Light | L | <7,000 kg | C172, C182, C208, PA28, BE36, BE20, PC12 |

## Separation Minima (FAA JO 7110.65Z §5-5-4 — Approach)

| Trailing (follower) | Leading (predecessor) | Min separation |
|---|---|---|
| H (Heavy) | J (Super) | 6 NM |
| M (Medium) | J (Super) | 7 NM |
| L (Light) | J (Super) | 8 NM |
| M (Medium) | H (Heavy) | 5 NM |
| L (Light) | H (Heavy) | 6 NM |
| L (Light) | M (Medium) | 4 NM |
| Any | Same category | Standard radar separation (3 NM / 5 NM depending on class) |

Note: These are wake turbulence separation minima on approach (ILS/visual). En-route and departure minima differ.
Departure wake minima are time-based (2 min / 3 min) per FAA JO 7110.65Z §5-5-7.

## RECAT-EU Categories (EUROCONTROL — European context only)

| Category | Label | Examples |
|---|---|---|
| A | Super Heavy | A388 |
| B | Upper Heavy | B744, B748, B77W, B779 |
| C | Lower Heavy | B788, B789, A332, A333, A359 |
| D | Upper Medium | B738, A320, A321, B737 |
| E | Lower Medium | CRJ9, E190, DH8D, AT72 |
| F | Light | C172, C208, PA28 |

RECAT-EU has different (often reduced) separation minima than ICAO legacy. Cards testing RECAT-EU must make the European context explicit.

## Wind Effects on Wake Vortex (FAA AC 90-23G)

- Wake vortices descend and move opposite to their rotation — trailing aircraft following on the same path remain at highest risk.
- A crosswind of ≥3 kt can push the upwind vortex back over the runway centerline.
- A headwind component reduces the descent rate of wake vortices.
- On approach, wake vortices from the preceding aircraft persist below the glideslope — follower aircraft on proper glideslope will fly through if spacing is insufficient.
- Ground effect causes vortices to spread laterally rather than continue descending within ~200 ft AGL.

## Task Type Definitions

| Type | Description |
|---|---|
| A | Knowledge — regulatory rule, definition, or standard |
| B | Hazard identification — given a scenario, identify the wake vortex risk |
| C | Consequence — given a specific scenario, predict or reason about the outcome/chain |
| D | Agentic — call `wake_category_checker` + `separation_calculator` to compute answer |

## Split Allocation

- `dev`: first ~60% of each file (cards 001–018 for 30-card files)
- `test`: remaining ~40% (cards 019–030 for 30-card files)

## Failure Mode Labels Used

Labels from `aerosafety.eval.failure_taxonomy`:
- `altitude_separation_error` — wrong vertical or lateral separation value
- `rule_misapplication` — uses wrong regulation or applies correct rule incorrectly
- `wrong_citation` — cites wrong standard or section
- `missing_required_tool_call` — Type D scenario: did not call required tool
- `unsafe_recommendation` — recommends an action that could cause or worsen hazard
- `missing_escalation` — fails to flag that ATC/supervisor escalation is required
- `incomplete_final_decision` — correct direction but incomplete reasoning
- `wrong_wake_category` — assigns wrong J/H/M/L or RECAT-EU category to aircraft type
