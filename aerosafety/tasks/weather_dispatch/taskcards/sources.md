# Sources for Task Family 3: Weather and Dispatch Risk

All rule citations used in this task family are listed below with URL and access date.
Every task card's `provenance` field cites one of these entries by name.

Per CLAUDE.md §2.2: All METAR/TAF inputs in this pilot batch are SYNTHETIC.
They are constructed from publicly documented WMO FM 15 and FM 51 format rules
and plausible operationally representative values. No fabricated station IDs or
timestamps are presented as real historical observations.

---

## Regulatory and Procedural Sources

### FAA-AIM-5-4-7
- Full title: FAA Aeronautical Information Manual, Chapter 5-4-7, Instrument Approach Procedures
- URL: https://www.faa.gov/air_traffic/publications/atpubs/aim_html/chap5_section_4.html#aim0504.html.7
- Access date: 2026-05-17
- Notes: Defines CAT I / II / III ILS approach minimums (DH and RVR).
  CAT I: DH 200 ft, RVR 1800 ft (or vis ½ SM).
  CAT II: DH 100 ft, RVR 1200 ft.
  CAT III-A: DH < 100 ft, RVR 700 ft.
  CAT III-B: DH < 50 ft, RVR 150 ft.

### 14-CFR-91-175
- Full title: 14 CFR Part 91, Section 91.175, Takeoff and landing under IFR
- URL: https://www.ecfr.gov/current/title-14/chapter-I/subchapter-F/part-91/subpart-B/section-91.175
- Access date: 2026-05-17
- Notes: Specifies visibility requirements and approach minima for instrument operations.

### 14-CFR-91-169
- Full title: 14 CFR Part 91, Section 91.169, IFR flight plan: information required
- URL: https://www.ecfr.gov/current/title-14/chapter-I/subchapter-F/part-91/subpart-B/section-91.169
- Access date: 2026-05-17
- Notes: Alternate airport weather minima requirements for IFR flight plans
  (ceiling ≥ 2000 ft, visibility ≥ 3 SM at ETA ± 1 hour unless exceptions apply;
  or published alternate minima if instrument approach is available at alternate).

### 14-CFR-121-619
- Full title: 14 CFR Part 121, Section 121.619, Alternate airport for destination: flag and supplemental operations
- URL: https://www.ecfr.gov/current/title-14/chapter-I/subchapter-G/part-121/subpart-U/section-121.619
- Access date: 2026-05-17
- Notes: Requires alternate airport in flight plan when weather at destination is
  forecast to be below 2000 ft ceiling or 3 SM visibility; defines alternate
  weather minima (ceiling adds 400 ft to lowest approach minima, visibility adds 1 SM).

### FAA-H-8083-25C
- Full title: FAA Pilot's Handbook of Aeronautical Knowledge (FAA-H-8083-25C), Chapter 12 (Weather)
- URL: https://www.faa.gov/regulations_policies/handbooks_manuals/aviation/phak
- Access date: 2026-05-17
- Notes: Defines crosswind and headwind component calculations (trigonometric):
  headwind = wind_speed × cos(angle_between_wind_and_runway)
  crosswind = wind_speed × sin(angle_between_wind_and_runway)

### FAA-AC-00-45H
- Full title: FAA Advisory Circular 00-45H, Aviation Weather Services
- URL: https://www.faa.gov/regulations_policies/advisory_circulars/index.cfm/go/document.information/documentID/1030235
- Access date: 2026-05-17
- Notes: Governs METAR and TAF decoding conventions, including gust reporting,
  CAVOK criteria, TAF change group (FM/BECMG/TEMPO/PROB) interpretation,
  and weather phenomena codes.

### WMO-306-I-1
- Full title: WMO Manual on Codes, Volume I.1, FM 15-XVI METAR and FM 51-XVI TAF
- URL: https://library.wmo.int/records/item/35713-manual-on-codes-volume-i-1
- Access date: 2026-05-17
- Notes: International standard for METAR and TAF format. Used to document
  generation rules for SYNTHETIC task inputs.

### FAA-AIM-7-1-14
- Full title: FAA Aeronautical Information Manual, Section 7-1-14, Ceiling
- URL: https://www.faa.gov/air_traffic/publications/atpubs/aim_html/chap7_section_1.html
- Access date: 2026-05-17
- Notes: Defines operational ceiling as the lowest BKN or OVC layer.
  Ceiling is distinct from visibility. FEW and SCT layers do not constitute a ceiling.

### FAA-AIM-7-1-30
- Full title: FAA Aeronautical Information Manual, Section 7-1-30, Prevailing Visibility
- URL: https://www.faa.gov/air_traffic/publications/atpubs/aim_html/chap7_section_1.html
- Access date: 2026-05-17
- Notes: Defines prevailing visibility and distinguishes it from RVR (Runway Visual Range).
  Prevailing visibility is the greatest distance at which objects can be seen over at least
  half the horizon. RVR is measured at runway level and is an instrument reading.

---

## SYNTHETIC Data Generation Rules

All METAR and TAF strings used in this pilot batch are SYNTHETIC per CLAUDE.md §2.2.

### SYNTH-METAR-RULE
Synthetic METAR strings conform to WMO No. 306 Vol. I.1 FM 15-XVI format
(see WMO-306-I-1 above). Station identifiers use the prefix "KXXX" pattern
(e.g., KZZZ) with a note that these are placeholder identifiers — they do not
correspond to any real-world ICAO station. Wind, visibility, sky, temperature,
and altimeter values are set to operationally plausible values chosen to
illustrate specific hazard conditions (e.g., crosswind near certified limits,
ceiling at CAT I minima, gusts significantly above mean wind speed).

### SYNTH-TAF-RULE
Synthetic TAF strings conform to WMO No. 306 Vol. I.1 FM 51-XVI format.
FM/BECMG/TEMPO/PROB groups use day/time designators consistent with a
plausible 24-30 hour forecast window. Validity windows are internally
consistent. Degradation scenarios (e.g., TEMPO fog, FM with low vis) are
constructed to represent operationally realistic IFR/LIFR transitions.

### SYNTH-RUNWAY-RULE
Runway headings are expressed as magnetic degrees per standard charted values.
Runway designators (e.g., 28L, 10R) correspond to their respective magnetic
headings (28L → 280°, 10R → 100°) following FAA charting conventions.
