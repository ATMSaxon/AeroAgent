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
