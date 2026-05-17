# Real Airport Methodology — Family 5 Airport Surface Operations

## Overview

Type B, C, and D task cards in this family are grounded in real US airport data extracted from FAA Chart Supplement PDFs, cycle 20260514 (effective 14 May 2026 – 9 July 2026). This document describes how real data was identified, extracted, and incorporated into task cards.

## Data Source

**FAA Chart Supplement (formerly Airport/Facility Directory)** — published every 56 days by the FAA Aeronautical Information Services. Each PDF covers a geographic region of the US and contains:
- Airport descriptions with communication frequencies
- Runway and taxiway data including geometry, restrictions, and closures
- Hot Spot descriptions (numbered HS-N locations with documented incursion/confusion history)
- LAHSO available distances
- Wingspan restrictions on specific taxiways
- Special operations notes (SMGCS, EMAS, ASDE-X, GBAS, RWSL)

**Cycle:** 20260514  
**Access date:** 2026-05-17  
**Files used:**

| Region | File | Size |
|--------|------|------|
| Northeast | FAA_CS_NE_20260514.pdf | 40.6 MB |
| East Central | FAA_CS_EC_20260514.pdf | 27.0 MB |
| South Central | FAA_CS_SC_20260514.pdf | 26.1 MB |
| North Central | FAA_CS_NC_20260514.pdf | 21.6 MB |
| Northwest | FAA_CS_NW_20260514.pdf | 18.0 MB |
| Southwest | FAA_CS_SW_20260514.pdf | 48.9 MB |
| Southeast | FAA_CS_SE_20260514.pdf | 35.3 MB |

All files are stored in `data/raw/FAA_CHART_SUPPL/2026-05-17/` with SHA-256 verification per `manifest.jsonl`.

## Target Airports

Cards cover the following real US airports. Page references indicate the Chart Supplement PDF page where airport data was sourced:

| ICAO | Airport | Region PDF | Pages |
|------|---------|------------|-------|
| KJFK | John F. Kennedy Intl, New York | NE | p.226-227 |
| KLGA | LaGuardia, New York | NE | p.228 |
| KBOS | Boston Logan Intl | NE | p.643 |
| KPHL | Philadelphia Intl | NE | p.643 |
| KATL | Hartsfield-Jackson Atlanta Intl | SE | p.203-204 |
| KCLT | Charlotte Douglas Intl | SE | p.603 |
| KMIA | Miami Intl | SE | p.602 |
| KLAX | Los Angeles Intl | SW | p.200-201 |
| KSFO | San Francisco Intl | SW | p.275-276 |
| KPHX | Phoenix Sky Harbor Intl | SW | p.76-77 |
| KDEN | Denver Intl | SW | p.649 |
| KSAN | San Diego Intl | SW | p.647 |
| KORD | Chicago O'Hare Intl | EC | p.42-44 |
| KIAH | Houston George Bush Intercontinental | SC | p.358-359 |
| KDFW | Dallas/Fort Worth Intl | SC | p.309-311 |
| KSEA | Seattle-Tacoma Intl | NW | p.270-271 |

## Hot Spot Identification

Hot Spots (HS-N) are numbered runway incursion and confusion locations published in the Chart Supplement's airport diagrams section. They represent locations with documented history of surface incidents. Each HS entry in the Chart Supplement includes:
- A location description (taxiway/runway intersection)
- The specific confusion type (misidentification, sight-line limitation, canted hold bar, etc.)

For each target airport, all published hot spots were read and the most operationally significant were selected for task card scenarios. Hot spot descriptions are quoted verbatim or closely paraphrased from the Chart Supplement.

## Provenance Format

Every real card uses this provenance structure:

```json
{
  "source": "FAA Chart Supplement [Region] U.S., cycle 20260514, FAA_CS_[XX]_20260514.pdf, p.[N] — [ICAO]",
  "access_date": "2026-05-17",
  "generation_rule": null,
  "license": "PILOT — NOT EXPERT-REVIEWED"
}
```

The `generation_rule` field is `null` for all real cards (used only for SYNTHETIC cards).

## Card Type Distribution

| Type | Count | Provenance | Description |
|------|-------|------------|-------------|
| A | 32 | SYNTHETIC | General aviation knowledge — no real airport data required |
| B | 25 | REAL | Hazard identification at specific hot spots, citing PDF + page |
| C | 15 | REAL | Consequence scenarios grounded in real hot spot geometry |
| D | 15 | REAL | Agentic surface conflict decisions using real airport layouts |

This gives 100% of B/C/D cards with real Chart Supplement citations, exceeding the ≥60% requirement.

## License

All task cards carry the license: `"PILOT — NOT EXPERT-REVIEWED"`

This label indicates the cards were constructed from publicly available FAA publications by a research analyst — they have not been reviewed or validated by certified aviation professionals, air traffic controllers, or FAA personnel. Cards should not be used for actual operational decision-making.

## Limitations

- Hot spot geometry is described from Chart Supplement text entries, not from the airport diagram images themselves. Spatial relationships are based on textual descriptions and may not capture all geometric details.
- Airport data reflects cycle 20260514 only. Subsequent cycles may change hot spot designations, taxiway restrictions, or LAHSO distances.
- LAHSO available distances and wingspan restrictions are taken verbatim from the Chart Supplement. Crews must always verify with current NOTAMs and airport diagram for actual operations.
