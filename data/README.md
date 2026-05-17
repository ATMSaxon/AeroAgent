# AeroSafetyEval — Data Directory

This directory holds all data for the AeroSafetyEval project.
It is organized into three strictly separated subdirectories.

---

## Directory Structure

```
data/
├── raw/           Real data downloaded from authoritative sources
├── processed/     Cleaned, parsed, and structured derivatives of raw data
└── synthetic/     Synthetic data generated from real operational constraints
```

---

## raw/

Contains data downloaded directly from authoritative sources with no modifications.

**Rules:**
- Files are organized by `source_id/` matching `aerosafety/data/sources/source_registry.yaml`.
- Every file must have a corresponding entry in `raw/manifest.jsonl`.
- `manifest.jsonl` contains: source_id, url_fetched, sha256, access_timestamp, local_file_path.
- Nothing in `raw/` is fabricated. All content originates from sources listed in the registry.

**Governed by:** CLAUDE.md §2.1 (Authoritative Sources Only), §5.1 (Mandatory Logging).

---

## processed/

Contains outputs of the data preprocessing pipeline applied to files in `raw/`.

**Rules:**
- Every processed file must record its source `doc_id` and the preprocessing steps applied.
- Preprocessing steps are logged in `processed/pipeline_log.jsonl`.
- No content is added during processing beyond what is in the source. Extraction only.
- Processed records use the `RawDocument` and `KnowledgePoint` schemas
  defined in `aerosafety/data/schemas/domain_schemas.py`.

**Governed by:** CLAUDE.md §2.1, §5.1, §5.2.

---

## synthetic/

Contains synthetically generated data items used for training and
low-coverage task families where authoritative data is insufficient.

**CRITICAL LABELING RULES (CLAUDE.md §2.2):**

1. Every file and every record in this directory is labeled `SYNTHETIC`.
2. Synthetic data is generated from real operational constraints — never invented without grounding.
3. Synthetic data is physically plausible and consistent with authoritative rules.
4. Synthetic data MUST NOT replace real validation data in the evaluation set.
5. Generation rules for every batch of synthetic data are documented in
   `synthetic/generation_configs/`.
6. Synthetic data is NEVER mixed with real data without explicit per-record labeling.
7. The evaluation (test) set MUST NOT contain synthetic data as ground truth
   for safety-critical decisions.

See `synthetic/README.md` for generation rules and labeling conventions.

**Governed by:** CLAUDE.md §2.2.

---

## manifest.jsonl

Located at `raw/manifest.jsonl`. One JSON line per downloaded file. Fields:

```json
{
  "source_id": "NASA_ASRS",
  "url_fetched": "https://asrs.arc.nasa.gov/...",
  "access_timestamp": "2026-05-17T12:00:00+00:00",
  "local_file_path": "data/raw/NASA_ASRS/asrs_2023.csv",
  "sha256": "abc123...64chars",
  "http_status_code": 200,
  "content_length_bytes": 12345678,
  "error": null
}
```

---

## What is NOT in this directory

- No model checkpoints (see `models/`).
- No evaluation outputs (see `eval_outputs/`).
- No prompt templates (see `aerosafety/prompts/`).
