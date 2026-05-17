# data/multimodal — Multimodal Ground-Truth Assets

This directory contains multimodal attachments for TaskCards in AeroSafetyEval.
All assets here are versioned ground truth per CLAUDE.md §5.2.

## Directory Layout

```
data/multimodal/
  airport_diagrams/   FAA Chart Supplement / d-TPP airport diagram crops
  trajectories/       ADS-B trajectory plots (OpenSky / ADS-B Exchange)
  lidar/              LiDAR scan renders (reserved for future families)
```

## File Naming Convention

```
{family}_{task_id}_{seq}.png
```

Examples:
- `airport_surface_T24_001.png`  — Family 5, task T24, sequence 001
- `atc_separation_T25_001.png`   — Family 6, task T25, sequence 001

## Integrity

Every directory may contain a `manifest.jsonl` file listing each asset with its
sha256 digest. Manifests are tracked in git (see `.gitignore` exception).

Each PNG embeds provenance metadata in its tEXt chunks:
- `source_pdf`            — absolute path of the originating PDF at extraction time
- `page_num`              — 1-based page number
- `dpi`                   — render resolution
- `bbox_pt`               — crop region in PDF point coordinates (if applicable)
- `extraction_timestamp`  — ISO-8601 UTC timestamp of extraction

## Provenance Rules (CLAUDE.md §2.1, §2.2)

- Assets extracted from real FAA / NTSB / OpenSky sources must carry
  `provenance.source` matching the `source_id` in `source_registry.yaml`.
- Synthetic or augmented assets must carry `provenance.source == "SYNTHETIC"`
  and must include `provenance.generation_rule`.
- Real and synthetic assets must never be mixed without explicit labeling.
