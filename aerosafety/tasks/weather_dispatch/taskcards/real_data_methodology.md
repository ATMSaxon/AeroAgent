# Real Data Methodology — T13 Expansion (WD-v2 cards)

**Status:** PILOT — NOT EXPERT-REVIEWED
**Author:** weather-task-author agent, 2026-05-17
**Covers:** WD-v2-A-001 through WD-v2-A-020 (SYNTHETIC),
           WD-v2-B-001 through WD-v2-B-030 (real IEM data),
           WD-v2-C-001 through WD-v2-C-015 (real IEM data),
           WD-v2-D-001 through WD-v2-D-015 (real IEM data)

---

## 1. Data Acquisition

METAR and TAF data for April 2026 were fetched from the Iowa State Environmental
Mesonet (IEM) public ASOS archive on 2026-05-17. IEM provides unrestricted global
access, no API key required, and caches ASOS data received in real time from the
FAA/NWS network. Two stations were selected:

- **KJFK** (John F. Kennedy International Airport, New York) — high-traffic
  Class B airport with frequent coastal fog events and significant CAT I/II ILS
  operations; good representative of East Coast marginal IFR conditions.
- **KORD** (O'Hare International Airport, Chicago) — high-traffic Class B with
  Great Lakes convective events, severe crosswind events on N-S runways during
  S-wind events, and Great Lakes fog.

Files downloaded:
- `data/raw/IEM_METAR/2026-05-17/KJFK_METAR_202604.csv` (SHA256: 5836940c…)
- `data/raw/IEM_METAR/2026-05-17/KORD_METAR_202604.csv` (SHA256: f5c84031…)
- `data/raw/IEM_TAF/2026-05-17/KJFK_TAF_202604.csv`   (SHA256: 73647d1d…)
- `data/raw/IEM_TAF/2026-05-17/KORD_TAF_202604.csv`   (SHA256: 7d09659e…)

SHA256 values are manifest-verified in:
- `data/raw/IEM_METAR/2026-05-17/manifest.jsonl`
- `data/raw/IEM_TAF/2026-05-17/manifest.jsonl`

---

## 2. Event Selection Criteria

METAR rows were scored using a weighted hazard function designed to surface
operationally relevant extreme events:

| Feature                     | Weight |
|-----------------------------|--------|
| Thunderstorm present (TS)   | +4     |
| Heavy precip (+)            | +3     |
| Freezing precip (FZ)        | +3     |
| Hail (GR) or ice pellets    | +3     |
| RVR reported (low vis)      | +4     |
| Gust ≥ 25 kt                | +3     |
| Gust ≥ 35 kt                | +5     |
| Visibility ≤ 1/4 SM         | +3     |
| Visibility ≤ 1 SM           | +2     |
| Ceiling ≤ 200 ft (LIFR)     | +3     |
| Ceiling ≤ 500 ft (IFR)      | +2     |
| CB in sky groups            | +2     |

Events scoring ≥ 10 were considered for inclusion. The top-scoring events were:

| Score | Station | Date/Time UTC       | Raw METAR (key elements)                                 |
|-------|---------|---------------------|----------------------------------------------------------|
| 19    | KORD    | 2026-04-15T03:51Z   | 27013G37KT 1/2SM R10L/1400VP6000FT +TSGRRA SCT015 BKN030CB OVC070 |
| 15    | KJFK    | 2026-04-03T12:51Z   | OVC002 1/8SM fog, LIFR                                   |
| 15    | KJFK    | 2026-04-05T08:51Z   | BKN004 1SM -DZ BR                                        |
| 15    | KORD    | 2026-04-17T05:51Z   | OVC002 1/4SM FG LIFR                                     |
| 14    | KJFK    | 2026-04-18T07:51Z   | OVC003 RVR 1600-2800 ft dense fog                        |
| 13    | KORD    | 2026-04-02T15:51Z   | 17039G47KT 6SM (extreme gust, crosswind on E-W runways)  |
| 12    | KORD    | 2026-04-04T02:51Z   | OVC003CB TS                                              |
| 12    | KORD    | 2026-04-18T01:51Z   | 19041KT 1/2SM +TSRA (extreme gust TS)                    |

TAF products valid during each selected METAR event were retrieved by matching
the TAF `valid` window to the METAR observation timestamp.

---

## 3. Provenance Format for Real-Data Cards

Real-data cards use the following provenance.source format:

```
"IEM_METAR <station> <ISO-8601-UTC> | file: data/raw/IEM_METAR/2026-05-17/<filename>.csv"
```

Or for TAF-grounded scenarios:

```
"IEM_TAF <station> product <product_id> | file: data/raw/IEM_TAF/2026-05-17/<filename>.csv"
```

Combined METAR+TAF scenarios:

```
"IEM_METAR <station> <time> + IEM_TAF <station> product <product_id> | files: data/raw/IEM_METAR/2026-05-17/<m>.csv, data/raw/IEM_TAF/2026-05-17/<t>.csv"
```

The `access_date` is always "2026-05-17" (the download date).
The `generation_rule` field is `null` for real-data cards (no synthetic generation).

---

## 4. Integrity Guarantees

Per CLAUDE.md §2.2 and the project's anti-fabrication rules:

- Every real-data card cites the exact raw METAR string as it appears in the
  IEM CSV (the `metar` column value). No values were altered.
- TAF text was read from the IEM TAF CSV `raw_text` column verbatim.
- Derived values (crosswind components, minima checks) are computed from the
  cited raw data using the tools defined in `aerosafety/tools/`.
- No METAR or TAF string is presented as real if it was manually constructed.
  All manually-constructed inputs remain Type A SYNTHETIC cards.
- Mixed provenance (part real, part synthetic) within a single card is
  prohibited. Cards are exclusively real or exclusively SYNTHETIC.

---

## 5. Limitations and Caveats

- April 2026 is within 30 days of the data download date. Some records may
  have been revised by the reporting station after initial upload to IEM.
  The SHA256 hashes in the manifest reflect the file state at download time.
- KORD and KJFK runway configurations used in these cards are based on the
  FAA Airport Diagram current as of 2026-05-17. Runway closures or temporary
  configuration changes within April 2026 are not captured.
- TAF products are from NWS forecast offices (KOKX for KJFK, KLOT for KORD).
  TAF accuracy is not evaluated here; the cards use the TAF as issued.
- Human expert review is required before any card from this expansion enters
  the frozen test split. See `docs/expert_review_protocol.md`.

---

# T30 Round-3 Scale-Up (WD3 cards)

**Status:** PILOT — NOT EXPERT-REVIEWED
**Author:** weather-scaler agent, 2026-05-17
**Covers:** WD3-B-001 through WD3-B-160 (real IEM METAR),
           WD3-C-001 through WD3-C-100 (real IEM METAR),
           WD3-D-001 through WD3-D-140 (real IEM METAR + TAF)

---

## T30.1 Data Scope

METAR and TAF data for 20 stations × 12 months (May 2025 – April 2026) were
sampled from the pre-fetched IEM ASOS corpus at
`data/raw/IEM_METAR/2026-05-17/` (238 CSVs) and
`data/raw/IEM_TAF/2026-05-17/` (240 CSVs).

All files are manifest-verified in:
- `data/raw/IEM_METAR/2026-05-17/manifest.jsonl`
- `data/raw/IEM_TAF/2026-05-17/manifest.jsonl`

Stations: KASE, KATL, KBOS, KCVG, KDEN, KDFW, KFAR, KGTF, KJFK, KLAX,
          KMEM, KMIA, KMSY, KONT, KORD, KPHX, KSDF, KSFO, PANC, PAOM.

---

## T30.2 Sampling Algorithm

The sampler (`scripts/generate_wd3_cards.py`, seed=42) operates as follows:

1. **Event detection** — for each METAR row, classify into event categories:
   - `low_ceiling`: BKN or OVC ceiling < 1000 ft AGL
   - `gust`: reported gust ≥ 25 kt
   - `ifr`: ceiling < 1000 ft OR visibility < 3 SM
   - `ts`: `TS` present in wxcodes column
   - `fz`: `FZ` present in wxcodes column (FZRA, FZDZ, FZFG, etc.)

2. **Per station-month budget** — at most 25 cards are drawn from any
   (station, month) pair across TypeB + TypeC + TypeD combined.

3. **Priority ordering** — rarer event types (ts, fz) are sampled first
   to maximize hazard diversity; high-frequency events (ifr, gust) fill
   remaining budget.

4. **Card construction** — each card uses the raw `metar` column value
   verbatim in the prompt. Derived values (crosswind, ceiling, visibility)
   are computed from the CSV row's numeric columns using the same logic
   as `aerosafety/tools/wind_component.py` and `weather_minima_checker.py`.

5. **TAF linking** (TypeD only) — the TAF CSV for the same station and
   month is loaded; the first 3 forecast (FM/TEMPO/BECMG) rows are used
   to construct the TAF excerpt in the prompt.

---

## T30.3 Event Coverage

| Event type  | METAR rows available | Used in cards |
|-------------|---------------------|---------------|
| ts          | ~1150               | ~100          |
| fz          | ~469                | ~60           |
| low_ceiling | ~6854               | ~90           |
| gust ≥25 kt | ~8700               | ~90           |
| ifr         | ~4689               | ~60           |

---

## T30.4 Provenance Format

Same as §3 above. Examples:

```
"IEM_METAR KORD 2026-01-15T03:51Z | file: data/raw/IEM_METAR/2026-05-17/KORD_METAR_202601.csv"

"IEM_METAR PANC 2026-01-07T14:53Z | file: data/raw/IEM_METAR/2026-05-17/PANC_METAR_202601.csv | TAF file: data/raw/IEM_TAF/2026-05-17/PANC_TAF_202601.csv"
```

---

## T30.5 Integrity Guarantees

All guarantees from §4 apply. Additional T30 constraints:

- No (station, month) pair contributes more than 25 cards (enforced by
  `test_no_station_month_dominates` in `tests/tasks/test_weather_dispatch.py`).
- Every card's cited CSV path is verified against the manifest
  (`test_real_data_cards_reference_manifest_csv`).
- The existing test split cards (WD-B-029–040, WD-C-020–030, WD-D-029–040)
  are not modified. New WD3-* cards are appended only.
- One pre-existing provenance error in WD-C-011 was corrected in this round:
  `KDEN_METAR_202605.csv` → `KDEN_METAR_202505.csv` (May 2025 observation).

---

## T30.6 Limitations

- TypeB/C/D cards are programmatically constructed, not human-authored.
  Gold decisions and safety constraints are formula-derived from METAR
  numeric columns and apply generic FAA AIM/14 CFR references.
  Station-specific IAP minima, NOTAMs, and local procedures are NOT captured.
- Expert review is required before WD3-* cards enter the frozen test split.
- KASE (Aspen) has a reduced crosswind limit (15 kt) vs the standard 25 kt
  used for other stations; this is captured in `STATION_META` in the sampler.
- PAOM (Nome) is a non-Part-121 airport; Part 135/91 framing is used for those cards.
- The TAF excerpt used in TypeD cards is the first 3 forecast rows from the
  same station-month CSV, which may not correspond temporally to the METAR
  observation. Evaluators should not assume the TAF is contemporaneous.
