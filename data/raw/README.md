# data/raw — Real Downloaded Data

This directory contains real data downloaded from public aviation data sources
as part of T10 (AeroSafetyEval Phase 1 pilot, 2026-05-17).

**The data files themselves are gitignored** (large binaries/CSVs).
Only the per-source `manifest.jsonl` files and this README are committed.

## Directory structure

```
data/raw/
  {SOURCE_ID}/
    {YYYY-MM-DD}/
      manifest.jsonl    ← committed; one JSON line per downloaded file
      *.csv / *.pdf / *.zip  ← NOT committed (gitignored)
```

## Sources downloaded (2026-05-17)

| Source | Status | Files | Total bytes | Notes |
|---|---|---|---|---|
| NTSB_ACCIDENT_DB | OK | 1 ZIP | 167,062 | CAROL API export; aviation accidents 2026-02-15..2026-05-17 |
| NTSB_FULL_REPORTS | OK | 5 PDF | 5,760,879 | Fatal accident narratives; internal Mkey format |
| IEM_METAR | OK | 2 CSV | 317,852 | KJFK + KORD, April 2026 |
| IEM_TAF | OK | 2 CSV | 669,939 | KJFK + KORD, April 2026 |
| NASA_ASRS | FAILED | 0 | 0 | HTTP 503 Service Unavailable on 2026-05-17; retry later |

**Grand total downloaded:** 6,915,732 bytes (6.60 MB)

## Reproducing the download

```bash
# Requires: team-lead approval for any re-run (CLAUDE.md §8.1)
AEROSAFETY_EVAL_MODE=1 python3 -m aerosafety.data.downloaders.run_pilot_download
```

## Manifest format

Each line in `manifest.jsonl` is a JSON object with:
- `source_id` — matches the parent directory name
- `source_url` — URL fetched (or attempted)
- `file_path` — relative path from project root (null for failures)
- `http_status` — actual HTTP response code
- `fetched_at_utc` — ISO-8601 timestamp
- `sha256` — hex digest of the saved file (null for failures)
- `content_length` — bytes written (0 for failures)
- `error` — error message if fetch failed, null otherwise

## Integrity verification

```bash
AEROSAFETY_EVAL_MODE=1 python3 -m pytest tests/data/test_real_downloads.py -v
```

Tests verify: directories non-empty, sha256 matches file contents,
no HTML error pages, correct file counts, valid ZIP/PDF/CSV magic bytes.
Tests skip automatically (not fail) if data files are absent.

## Licensing

| Source | License | Citation |
|---|---|---|
| NTSB accident data | Public domain (17 U.S.C. §105) | National Transportation Safety Board, Aviation Accident Database |
| IEM METAR/TAF | Iowa State University Mesonet — free for research | Iowa State University, Iowa Environmental Mesonet |
| NASA ASRS | Not yet downloaded | NASA Aviation Safety Reporting System |

## NTSB CAROL API notes

The NTSB CAROL system (`data.ntsb.gov/carol-main-public`) is a JavaScript SPA.
The download script uses the REST API discovered by reverse-engineering the SPA
JavaScript (search-results.js / results-list-view.js):

1. `POST /carol-main-public/api/Session/CreateSession` → integer session_id
2. `POST /carol-main-public/api/Query/FileExport` with session_id and query → ZIP blob

NTSB narrative PDFs use the internal `Mkey` (integer), not the public `NtsbNo`
report designator (e.g., `ERA23LA177`). Using NtsbNo in the
`GenerateNewestReport/{id}/pdf` URL returns HTTP 404.
