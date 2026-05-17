# aerosafety/data — Data Curation Package

This package contains the aviation safety data curation infrastructure
for AeroSafetyEval. It does NOT contain actual data files — those live in
the top-level `data/` directory.

---

## Package Structure

```
aerosafety/data/
├── taxonomy/
│   └── aviation_safety_taxonomy.yaml   — 9-branch taxonomy (proposal §9.1)
├── sources/
│   └── source_registry.yaml            — authoritative source registry (20 sources)
├── schemas/
│   └── domain_schemas.py               — Pydantic: KnowledgePoint, Provenance, RawDocument
├── downloaders/
│   ├── _base.py                        — shared fetch utilities + manifest writing
│   ├── download_asrs.py                — NASA ASRS (Task Families 1, 2)
│   ├── download_ntsb.py                — NTSB accident DB (Task Family 2)
│   ├── download_metar_taf.py           — METAR (IEM) + TAF (AWC) (Task Family 3)
│   ├── download_notam.py               — FAA NOTAM API (Task Family 4)
│   ├── download_adsb.py                — OpenSky ADS-B (Task Family 6)
│   └── download_faa_docs.py            — ACs, CFR, diagrams, wake tables, MMEL, SDR
└── README.md                           — this file
```

---

## Taxonomy

`taxonomy/aviation_safety_taxonomy.yaml` defines 9 branches corresponding to
the proposal §7 task families. Each branch has subtopics with:
- `key_rules_and_concepts`: regulatory basis (not invented)
- `knowledge_point_seeds`: types of KPs to extract
- `critical_failure_modes`: from proposal §14

---

## Source Registry

`sources/source_registry.yaml` lists 20 authoritative sources.

Sources requiring user action (API key or registration):
| source_id       | requires_user_action | action_needed                          |
|-----------------|----------------------|----------------------------------------|
| FAA_NOTAM       | true                 | Free API key at api.faa.gov            |
| OPENSKY_ADSB    | true                 | Register + request Impala access       |
| EUROCONTROL_DDS | true                 | Research collaboration request         |
| ICAO_DOCS       | true                 | Purchase or institutional library access|
| ICAO_NOTAM      | true                 | National AIS authority coordination    |
| ICAO_AIRPORT_OPS| true                 | Purchase or institutional library access|
| FAA_TFMS        | true                 | FAA data-sharing agreement             |

Direct downloads (no registration needed):
  NASA_ASRS, NTSB_ACCIDENT_DB, NTSB_FULL_REPORTS, FAA_SDR,
  NOAA_METAR, NOAA_TAF, FAA_AC, FAA_CFR14, FAA_AIRPORT_DIAGRAMS,
  FAA_WAKE_CATEGORIES, FAA_MMEL, EUROCONTROL_RECAT

---

## Schemas

`schemas/domain_schemas.py` defines:
- `Provenance` — full lineage for every data item
- `RawDocument` — ingested document before KP extraction
- `KnowledgePoint` — 7 domain fields per proposal §9.3
- `ManifestEntry` — one line of manifest.jsonl per downloaded file

These will be coordinated with `aerosafety/io.py` once T1 (infra-architect) publishes it.

---

## Downloaders

All downloader scripts default to `dry_run=True`.

Hard rules (enforced in `_base.py` and each downloader):
1. `dry_run=False` raises RuntimeError unless the guard is removed after team-lead approval.
2. Every URL fetched is logged at INFO level.
3. Every file downloaded writes a manifest.jsonl entry (sha256 + url + timestamp).
4. HTTP errors raise immediately — no silent fallback.
5. Rate limits are respected per documented source constraints.

---

## Governed by

- CLAUDE.md §1.1 (No Fabricated Data)
- CLAUDE.md §2 (Data Constraints)
- CLAUDE.md §2.2 (Synthetic Data Rules)
- CLAUDE.md §5.1 (Mandatory Logging)
- Proposal §9 (Data Curation Pipeline)
