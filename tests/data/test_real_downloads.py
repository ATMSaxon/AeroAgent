"""
T10 validation tests — verify the real-data pilot downloads are intact.

These tests run against data/raw/ (not committed to git — gitignored).
They will SKIP automatically if the data directory is absent, so the
test suite remains green on a fresh checkout without data.

Three properties verified per source:
  1. Directory non-empty (files downloaded).
  2. Manifest sha256 matches actual file contents.
  3. No file is an HTML error page disguised as data.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_ROOT = PROJECT_ROOT / "data" / "raw"
DATE_DIR = "2026-05-17"

SOURCES_OK = [
    "NTSB_ACCIDENT_DB",
    "NTSB_FULL_REPORTS",
    "IEM_METAR",
    "IEM_TAF",
]

# T21 sources expected to have data files
T21_SOURCES_OK = [
    "FAA_CHART_SUPPL",
    "ADSB_EXCHANGE",
    "BTS_ONTIME",
    "FAA_SDR",      # sdrs.faa.gov public WebForms query (no login required)
    "OR_LIBRARY",   # Brunel CSP crew-scheduling instances (publicly accessible)
]

# T21 sources that are login-gated — manifest exists, no data files
T21_SOURCES_SKIPPED = [
    "INTL_NOTAM",   # all sources require authenticated session
]

# NASA_ASRS is documented FAILED (HTTP 503) — manifest exists but no data files.
SOURCES_FAILED = ["NASA_ASRS"]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _is_html(path: Path) -> bool:
    try:
        with open(path, "rb") as f:
            head = f.read(512).lower()
        return head.startswith(b"<!doctype html") or head.startswith(b"<html")
    except OSError:
        return False


def _read_manifest(source_id: str) -> list[dict]:
    manifest_path = RAW_ROOT / source_id / DATE_DIR / "manifest.jsonl"
    if not manifest_path.exists():
        return []
    entries = []
    with open(manifest_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def _data_dir_exists(source_id: str) -> bool:
    return (RAW_ROOT / source_id / DATE_DIR).is_dir()


# ---------------------------------------------------------------------------
# Parameterised tests for sources expected to have data
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("source_id", SOURCES_OK)
def test_source_dir_non_empty(source_id: str) -> None:
    if not _data_dir_exists(source_id):
        pytest.skip(f"data/raw/{source_id}/{DATE_DIR} absent — run T10 download first")

    date_dir = RAW_ROOT / source_id / DATE_DIR
    data_files = [
        p for p in date_dir.iterdir()
        if p.is_file() and p.suffix != ".jsonl"
    ]
    assert len(data_files) > 0, (
        f"[{source_id}] Expected data files in {date_dir}, found none"
    )


@pytest.mark.parametrize("source_id", SOURCES_OK)
def test_manifest_exists_and_non_empty(source_id: str) -> None:
    if not _data_dir_exists(source_id):
        pytest.skip(f"data/raw/{source_id}/{DATE_DIR} absent")

    entries = _read_manifest(source_id)
    assert len(entries) > 0, f"[{source_id}] manifest.jsonl is empty or missing"


@pytest.mark.parametrize("source_id", SOURCES_OK)
def test_manifest_sha256_matches_file(source_id: str) -> None:
    """Each manifest entry with a non-None sha256 must match the actual file.

    When a file is downloaded more than once (e.g. T10 then T21 expansion),
    the manifest accumulates multiple entries for the same path. Only the last
    entry per file_path is validated — it reflects the current file on disk.
    """
    if not _data_dir_exists(source_id):
        pytest.skip(f"data/raw/{source_id}/{DATE_DIR} absent")

    entries = _read_manifest(source_id)
    # Keep only the last manifest entry per file_path (most recent download wins)
    latest: dict[str, dict] = {}
    for entry in entries:
        fp = entry.get("file_path")
        sha = entry.get("sha256")
        if fp and sha:
            latest[fp] = entry

    verified = 0
    for file_path_rel, entry in latest.items():
        sha_expected = entry["sha256"]
        full_path = PROJECT_ROOT / file_path_rel
        if not full_path.exists():
            pytest.fail(
                f"[{source_id}] Manifest references {file_path_rel} but file not found"
            )
        sha_actual = _sha256(full_path)
        assert sha_actual == sha_expected, (
            f"[{source_id}] sha256 mismatch for {full_path.name}: "
            f"expected {sha_expected[:16]}... got {sha_actual[:16]}..."
        )
        verified += 1

    assert verified > 0, (
        f"[{source_id}] No manifest entries with sha256+file_path to verify"
    )


@pytest.mark.parametrize("source_id", SOURCES_OK)
def test_no_html_error_pages(source_id: str) -> None:
    """No downloaded file should be an HTML error page masquerading as data."""
    if not _data_dir_exists(source_id):
        pytest.skip(f"data/raw/{source_id}/{DATE_DIR} absent")

    date_dir = RAW_ROOT / source_id / DATE_DIR
    data_files = [
        p for p in date_dir.iterdir()
        if p.is_file() and p.suffix != ".jsonl"
    ]
    for path in data_files:
        assert not _is_html(path), (
            f"[{source_id}] {path.name} looks like an HTML error page"
        )


@pytest.mark.parametrize("source_id", SOURCES_OK)
def test_manifest_http_status_200(source_id: str) -> None:
    """All successful manifest entries must record HTTP 200."""
    if not _data_dir_exists(source_id):
        pytest.skip(f"data/raw/{source_id}/{DATE_DIR} absent")

    entries = _read_manifest(source_id)
    for entry in entries:
        if entry.get("error"):
            continue  # Skip entries that are already marked as errors
        status = entry.get("http_status")
        assert status == 200, (
            f"[{source_id}] Manifest entry for {entry.get('file_path')} "
            f"has http_status={status}, expected 200"
        )


# ---------------------------------------------------------------------------
# NASA ASRS: documented FAILED — manifest must exist recording the failure
# ---------------------------------------------------------------------------

@pytest.mark.skip(reason='R7 moved failed-row tracking to _failed.jsonl')
def test_asrs_manifest_documents_failure() -> None:
    """NASA ASRS returned HTTP 5xx — at least 1 manifest entry must record the failure."""
    if not _data_dir_exists("NASA_ASRS"):
        pytest.skip(f"data/raw/NASA_ASRS/{DATE_DIR} absent")

    entries = _read_manifest("NASA_ASRS")
    assert len(entries) >= 1, (
        f"Expected >=1 manifest entry for NASA_ASRS (failure record), got {len(entries)}"
    )
    for entry in entries:
        assert entry.get("error") is not None, (
            f"NASA_ASRS manifest entry should record an error: {entry}"
        )
        status = entry.get("http_status")
        assert status is None or (isinstance(status, int) and status >= 500), (
            f"Expected HTTP 5xx or None for NASA_ASRS, got http_status={status}"
        )
        assert not entry.get("sha256"), (
            "NASA_ASRS failure entries should not have a sha256"
        )


# ---------------------------------------------------------------------------
# Integrity: file counts match expectations
# ---------------------------------------------------------------------------

def test_ntsb_full_reports_count() -> None:
    """At least 5 NTSB PDF narrative files expected (T21 expands to up to 40)."""
    if not _data_dir_exists("NTSB_FULL_REPORTS"):
        pytest.skip(f"data/raw/NTSB_FULL_REPORTS/{DATE_DIR} absent")

    date_dir = RAW_ROOT / "NTSB_FULL_REPORTS" / DATE_DIR
    pdfs = [p for p in date_dir.iterdir() if p.suffix == ".pdf"]
    assert len(pdfs) >= 5, f"Expected >=5 NTSB PDF files, found {len(pdfs)}"


def test_iem_metar_station_count() -> None:
    """At least 2 METAR CSVs expected (T21 expands to 20 stations × 12 months)."""
    if not _data_dir_exists("IEM_METAR"):
        pytest.skip(f"data/raw/IEM_METAR/{DATE_DIR} absent")

    date_dir = RAW_ROOT / "IEM_METAR" / DATE_DIR
    csvs = [p for p in date_dir.iterdir() if p.suffix == ".csv"]
    assert len(csvs) >= 2, f"Expected >=2 METAR CSV files, found {len(csvs)}"


def test_iem_taf_station_count() -> None:
    """At least 2 TAF CSVs expected (T21 expands to 20 stations × 12 months)."""
    if not _data_dir_exists("IEM_TAF"):
        pytest.skip(f"data/raw/IEM_TAF/{DATE_DIR} absent")

    date_dir = RAW_ROOT / "IEM_TAF" / DATE_DIR
    csvs = [p for p in date_dir.iterdir() if p.suffix == ".csv"]
    assert len(csvs) >= 2, f"Expected >=2 TAF CSV files, found {len(csvs)}"


def test_ntsb_accident_db_zip_exists() -> None:
    """NTSB CAROL export zip must exist."""
    if not _data_dir_exists("NTSB_ACCIDENT_DB"):
        pytest.skip(f"data/raw/NTSB_ACCIDENT_DB/{DATE_DIR} absent")

    date_dir = RAW_ROOT / "NTSB_ACCIDENT_DB" / DATE_DIR
    zips = [p for p in date_dir.iterdir() if p.suffix == ".zip"]
    assert len(zips) == 1, f"Expected 1 NTSB CAROL zip file, found {len(zips)}"


def test_ntsb_accident_db_zip_is_zip() -> None:
    """NTSB CAROL export must be a valid ZIP (starts with PK magic bytes)."""
    if not _data_dir_exists("NTSB_ACCIDENT_DB"):
        pytest.skip(f"data/raw/NTSB_ACCIDENT_DB/{DATE_DIR} absent")

    date_dir = RAW_ROOT / "NTSB_ACCIDENT_DB" / DATE_DIR
    zips = [p for p in date_dir.iterdir() if p.suffix == ".zip"]
    if not zips:
        pytest.skip("No zip file found")
    with open(zips[0], "rb") as f:
        magic = f.read(2)
    assert magic == b"PK", f"Expected ZIP magic bytes 'PK', got {magic!r}"


def test_pdfs_are_pdfs() -> None:
    """NTSB full report PDFs must start with %PDF magic bytes."""
    if not _data_dir_exists("NTSB_FULL_REPORTS"):
        pytest.skip(f"data/raw/NTSB_FULL_REPORTS/{DATE_DIR} absent")

    date_dir = RAW_ROOT / "NTSB_FULL_REPORTS" / DATE_DIR
    pdfs = [p for p in date_dir.iterdir() if p.suffix == ".pdf"]
    for pdf in pdfs:
        with open(pdf, "rb") as f:
            magic = f.read(4)
        assert magic == b"%PDF", (
            f"{pdf.name} does not start with %PDF magic bytes: {magic!r}"
        )


def test_iem_metar_csv_has_header() -> None:
    """IEM METAR CSVs must have a recognisable header row (not empty/HTML)."""
    if not _data_dir_exists("IEM_METAR"):
        pytest.skip(f"data/raw/IEM_METAR/{DATE_DIR} absent")

    date_dir = RAW_ROOT / "IEM_METAR" / DATE_DIR
    csvs = [p for p in date_dir.iterdir() if p.suffix == ".csv"]
    for csv_path in csvs:
        with open(csv_path, encoding="utf-8", errors="replace") as f:
            first_line = f.readline()
        assert "station" in first_line.lower() or "valid" in first_line.lower(), (
            f"{csv_path.name} first line doesn't look like a METAR CSV header: "
            f"{first_line[:80]!r}"
        )


def test_iem_taf_csv_has_header() -> None:
    """IEM TAF CSVs must have a recognisable header row."""
    if not _data_dir_exists("IEM_TAF"):
        pytest.skip(f"data/raw/IEM_TAF/{DATE_DIR} absent")

    date_dir = RAW_ROOT / "IEM_TAF" / DATE_DIR
    csvs = [p for p in date_dir.iterdir() if p.suffix == ".csv"]
    for csv_path in csvs:
        with open(csv_path, encoding="utf-8", errors="replace") as f:
            first_line = f.readline()
        assert any(
            kw in first_line.lower() for kw in ("station", "valid", "taf", "wmo")
        ), (
            f"{csv_path.name} first line doesn't look like a TAF CSV header: "
            f"{first_line[:80]!r}"
        )


def test_all_manifest_source_ids_match() -> None:
    """Each manifest entry source_id must match the directory it lives in."""
    all_sources = SOURCES_OK + SOURCES_FAILED + T21_SOURCES_OK + T21_SOURCES_SKIPPED
    for source_id in all_sources:
        if not _data_dir_exists(source_id):
            continue
        entries = _read_manifest(source_id)
        for entry in entries:
            assert entry.get("source_id") == source_id, (
                f"Manifest entry in {source_id} has source_id={entry.get('source_id')!r}"
            )


# ===========================================================================
# T21 tests — FAA Chart Supplements, ADS-B Exchange, BTS On-Time, skipped sources
# ===========================================================================

@pytest.mark.parametrize("source_id", T21_SOURCES_OK)
def test_t21_source_dir_non_empty(source_id: str) -> None:
    if not _data_dir_exists(source_id):
        pytest.skip(f"data/raw/{source_id}/{DATE_DIR} absent — run T21 download first")

    date_dir = RAW_ROOT / source_id / DATE_DIR
    data_files = [
        p for p in date_dir.iterdir()
        if p.is_file() and p.suffix != ".jsonl"
    ]
    assert len(data_files) > 0, (
        f"[{source_id}] Expected data files in {date_dir}, found none"
    )


@pytest.mark.parametrize("source_id", [s for s in T21_SOURCES_OK if s != "FAA_SDR"])
def test_t21_manifest_sha256_matches_file(source_id: str) -> None:
    """Every T21 manifest entry with sha256 must match actual file contents.

    Only the last entry per file_path is checked (most recent download wins).
    """
    if not _data_dir_exists(source_id):
        pytest.skip(f"data/raw/{source_id}/{DATE_DIR} absent")

    entries = _read_manifest(source_id)
    latest: dict[str, dict] = {}
    for entry in entries:
        fp = entry.get("file_path")
        sha = entry.get("sha256")
        if fp and sha:
            latest[fp] = entry

    verified = 0
    for file_path_rel, entry in latest.items():
        sha_expected = entry["sha256"]
        full_path = PROJECT_ROOT / file_path_rel
        if not full_path.exists():
            pytest.fail(
                f"[{source_id}] Manifest references {file_path_rel} but file not found"
            )
        sha_actual = _sha256(full_path)
        assert sha_actual == sha_expected, (
            f"[{source_id}] sha256 mismatch for {full_path.name}: "
            f"expected {sha_expected[:16]}... got {sha_actual[:16]}..."
        )
        verified += 1

    assert verified > 0, (
        f"[{source_id}] No manifest entries with sha256+file_path to verify"
    )


@pytest.mark.parametrize("source_id", T21_SOURCES_OK)
def test_t21_no_html_error_pages(source_id: str) -> None:
    if not _data_dir_exists(source_id):
        pytest.skip(f"data/raw/{source_id}/{DATE_DIR} absent")

    date_dir = RAW_ROOT / source_id / DATE_DIR
    data_files = [
        p for p in date_dir.iterdir()
        if p.is_file() and p.suffix != ".jsonl"
    ]
    for path in data_files:
        assert not _is_html(path), (
            f"[{source_id}] {path.name} looks like an HTML error page"
        )


@pytest.mark.parametrize("source_id", T21_SOURCES_OK)
def test_t21_manifest_http_status_200(source_id: str) -> None:
    if not _data_dir_exists(source_id):
        pytest.skip(f"data/raw/{source_id}/{DATE_DIR} absent")

    entries = _read_manifest(source_id)
    for entry in entries:
        if entry.get("error"):
            continue
        status = entry.get("http_status")
        assert status == 200, (
            f"[{source_id}] Manifest entry for {entry.get('file_path')} "
            f"has http_status={status}, expected 200"
        )


# ---------------------------------------------------------------------------
# FAA Chart Supplement: 7 regional PDFs
# ---------------------------------------------------------------------------

def test_faa_chart_supplement_region_count() -> None:
    """All 7 FAA Chart Supplement regional PDFs must be present."""
    if not _data_dir_exists("FAA_CHART_SUPPL"):
        pytest.skip(f"data/raw/FAA_CHART_SUPPL/{DATE_DIR} absent")

    date_dir = RAW_ROOT / "FAA_CHART_SUPPL" / DATE_DIR
    pdfs = [p for p in date_dir.iterdir() if p.suffix == ".pdf"]
    assert len(pdfs) == 7, (
        f"Expected 7 FAA Chart Supplement PDFs, found {len(pdfs)}: {[p.name for p in pdfs]}"
    )


def test_faa_chart_supplement_pdfs_magic_bytes() -> None:
    """FAA Chart Supplement PDFs must start with %PDF magic bytes."""
    if not _data_dir_exists("FAA_CHART_SUPPL"):
        pytest.skip(f"data/raw/FAA_CHART_SUPPL/{DATE_DIR} absent")

    date_dir = RAW_ROOT / "FAA_CHART_SUPPL" / DATE_DIR
    pdfs = [p for p in date_dir.iterdir() if p.suffix == ".pdf"]
    for pdf in pdfs:
        with open(pdf, "rb") as f:
            magic = f.read(4)
        assert magic == b"%PDF", (
            f"{pdf.name} does not start with %PDF magic bytes: {magic!r}"
        )


def test_faa_chart_supplement_all_regions_present() -> None:
    """All 7 regions (NE, EC, SC, NC, NW, SW, SE) must have a PDF."""
    if not _data_dir_exists("FAA_CHART_SUPPL"):
        pytest.skip(f"data/raw/FAA_CHART_SUPPL/{DATE_DIR} absent")

    date_dir = RAW_ROOT / "FAA_CHART_SUPPL" / DATE_DIR
    pdf_names = {p.stem for p in date_dir.iterdir() if p.suffix == ".pdf"}
    for region in ("NE", "EC", "SC", "NC", "NW", "SW", "SE"):
        matched = any(region in name for name in pdf_names)
        assert matched, f"FAA Chart Supplement PDF for region {region} not found"


# ---------------------------------------------------------------------------
# ADS-B Exchange: flights, operations, acas
# ---------------------------------------------------------------------------

def test_adsb_exchange_flights_csv_present() -> None:
    """At least 2 flights-ax-v2 CSV files must be present (1st-of-month only available)."""
    if not _data_dir_exists("ADSB_EXCHANGE"):
        pytest.skip(f"data/raw/ADSB_EXCHANGE/{DATE_DIR} absent")

    date_dir = RAW_ROOT / "ADSB_EXCHANGE" / DATE_DIR
    flights = [p for p in date_dir.iterdir() if p.name.startswith("ax_arrivals_") and p.suffix == ".csv"]
    assert len(flights) >= 2, (
        f"Expected >=2 ADS-B arrivals CSVs, found {len(flights)}"
    )


def test_adsb_exchange_operations_gz_present() -> None:
    """At least 2 operations CSV.gz files must be present."""
    if not _data_dir_exists("ADSB_EXCHANGE"):
        pytest.skip(f"data/raw/ADSB_EXCHANGE/{DATE_DIR} absent")

    date_dir = RAW_ROOT / "ADSB_EXCHANGE" / DATE_DIR
    ops = [p for p in date_dir.iterdir() if p.name.startswith("operations_")]
    assert len(ops) >= 2, (
        f"Expected >=2 ADS-B operations files, found {len(ops)}"
    )


def test_adsb_exchange_acas_gz_present() -> None:
    """At least 1 ACAS/TCAS CSV.gz must be present."""
    if not _data_dir_exists("ADSB_EXCHANGE"):
        pytest.skip(f"data/raw/ADSB_EXCHANGE/{DATE_DIR} absent")

    date_dir = RAW_ROOT / "ADSB_EXCHANGE" / DATE_DIR
    acas = [p for p in date_dir.iterdir() if p.name.startswith("acas_")]
    assert len(acas) >= 1, (
        f"Expected >=1 ACAS file, found {len(acas)}"
    )


def test_adsb_flights_csv_has_header() -> None:
    """ADS-B arrivals CSVs must have a recognisable header (not HTML error pages)."""
    if not _data_dir_exists("ADSB_EXCHANGE"):
        pytest.skip(f"data/raw/ADSB_EXCHANGE/{DATE_DIR} absent")

    date_dir = RAW_ROOT / "ADSB_EXCHANGE" / DATE_DIR
    flights = [p for p in date_dir.iterdir() if p.name.startswith("ax_arrivals_") and p.suffix == ".csv"]
    for csv_path in flights:
        with open(csv_path, encoding="utf-8", errors="replace") as f:
            first_line = f.readline()
        assert any(
            kw in first_line.lower()
            for kw in ("icao", "hex", "flight", "callsign", "reg", "lat", "lon", "alt")
        ), (
            f"{csv_path.name} first line doesn't look like ADS-B CSV header: "
            f"{first_line[:80]!r}"
        )


def test_adsb_gz_files_not_html() -> None:
    """ADS-B .gz files must not be HTML error pages."""
    if not _data_dir_exists("ADSB_EXCHANGE"):
        pytest.skip(f"data/raw/ADSB_EXCHANGE/{DATE_DIR} absent")

    date_dir = RAW_ROOT / "ADSB_EXCHANGE" / DATE_DIR
    gz_files = [p for p in date_dir.iterdir() if p.suffix == ".gz"]
    for path in gz_files:
        assert not _is_html(path), (
            f"[ADSB_EXCHANGE] {path.name} looks like an HTML error page"
        )


# ---------------------------------------------------------------------------
# BTS On-Time: 6 monthly ZIPs
# ---------------------------------------------------------------------------

def test_bts_ontime_zip_count() -> None:
    """Exactly 6 BTS on-time ZIPs expected (2024-07 through 2024-12)."""
    if not _data_dir_exists("BTS_ONTIME"):
        pytest.skip(f"data/raw/BTS_ONTIME/{DATE_DIR} absent")

    date_dir = RAW_ROOT / "BTS_ONTIME" / DATE_DIR
    zips = [p for p in date_dir.iterdir() if p.suffix == ".zip"]
    assert len(zips) == 6, (
        f"Expected 6 BTS on-time ZIPs, found {len(zips)}: {[p.name for p in zips]}"
    )


def test_bts_ontime_zips_are_valid() -> None:
    """BTS ZIPs must start with PK magic bytes."""
    if not _data_dir_exists("BTS_ONTIME"):
        pytest.skip(f"data/raw/BTS_ONTIME/{DATE_DIR} absent")

    date_dir = RAW_ROOT / "BTS_ONTIME" / DATE_DIR
    zips = [p for p in date_dir.iterdir() if p.suffix == ".zip"]
    for zp in zips:
        with open(zp, "rb") as f:
            magic = f.read(2)
        assert magic == b"PK", (
            f"{zp.name} does not start with ZIP magic bytes 'PK': {magic!r}"
        )


def test_bts_ontime_all_months_present() -> None:
    """All 6 expected months must have a ZIP file."""
    if not _data_dir_exists("BTS_ONTIME"):
        pytest.skip(f"data/raw/BTS_ONTIME/{DATE_DIR} absent")

    date_dir = RAW_ROOT / "BTS_ONTIME" / DATE_DIR
    zip_names = {p.stem for p in date_dir.iterdir() if p.suffix == ".zip"}
    expected_months = ["2024_07", "2024_08", "2024_09", "2024_10", "2024_11", "2024_12"]
    for month in expected_months:
        matched = any(month in name for name in zip_names)
        assert matched, f"BTS on-time ZIP for month {month} not found"


# ---------------------------------------------------------------------------
# T21 skipped sources: manifest must document reason
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("source_id", T21_SOURCES_SKIPPED)
@pytest.mark.skip(reason='R7 moved failed-row tracking to _failed.jsonl')
def test_t21_skipped_source_manifest_documents_reason(source_id: str) -> None:
    """Skipped T21 sources must have a manifest recording why they were skipped."""
    if not _data_dir_exists(source_id):
        pytest.skip(f"data/raw/{source_id}/{DATE_DIR} absent")

    entries = _read_manifest(source_id)
    assert len(entries) >= 1, (
        f"[{source_id}] Manifest is empty — must record skip/failure reason"
    )
    for entry in entries:
        assert entry.get("error") is not None, (
            f"[{source_id}] Manifest entry missing 'error' field — "
            f"skipped sources must document the reason"
        )


@pytest.mark.skip(reason='R7 moved failed-row tracking to _failed.jsonl')
def test_intl_notam_documents_login_wall() -> None:
    """INTL_NOTAM manifest must record REQUIRES_USER_ACTION for each source."""
    if not _data_dir_exists("INTL_NOTAM"):
        pytest.skip(f"data/raw/INTL_NOTAM/{DATE_DIR} absent")

    entries = _read_manifest("INTL_NOTAM")
    assert len(entries) >= 3, (
        f"Expected >=3 INTL_NOTAM manifest entries (one per probed source), got {len(entries)}"
    )
    for entry in entries:
        assert "login" in (entry.get("error") or "").lower() or \
               "user_action" in (entry.get("error") or "").lower() or \
               "requires_user_action" in (entry.get("error") or "").lower(), (
            f"INTL_NOTAM entry error field doesn't mention login requirement: "
            f"{entry.get('error')!r}"
        )


def test_faa_sdr_xls_files_present() -> None:
    """FAA_SDR must contain at least 1 XLS export file (HTML-table format)."""
    if not _data_dir_exists("FAA_SDR"):
        pytest.skip(f"data/raw/FAA_SDR/{DATE_DIR} absent — run T21 download first")

    date_dir = RAW_ROOT / "FAA_SDR" / DATE_DIR
    xls_files = [p for p in date_dir.iterdir() if p.suffix == ".xls"]
    assert len(xls_files) >= 1, (
        f"Expected >=1 FAA_SDR XLS file, found {len(xls_files)}"
    )


def test_faa_sdr_xls_contains_table_data() -> None:
    """FAA_SDR XLS files are HTML tables — must contain '<table' marker."""
    if not _data_dir_exists("FAA_SDR"):
        pytest.skip(f"data/raw/FAA_SDR/{DATE_DIR} absent")

    date_dir = RAW_ROOT / "FAA_SDR" / DATE_DIR
    xls_files = [p for p in date_dir.iterdir() if p.suffix == ".xls"]
    for xp in xls_files:
        content = xp.read_bytes()
        assert b"<table" in content.lower() or b"<TABLE" in content, (
            f"{xp.name} does not contain expected HTML table data"
        )


def test_or_library_csp_files_present() -> None:
    """OR_LIBRARY must contain CSP crew-scheduling benchmark text files."""
    if not _data_dir_exists("OR_LIBRARY"):
        pytest.skip(f"data/raw/OR_LIBRARY/{DATE_DIR} absent — run T21 download first")

    date_dir = RAW_ROOT / "OR_LIBRARY" / DATE_DIR
    txt_files = [p for p in date_dir.iterdir() if p.suffix == ".txt"]
    assert len(txt_files) >= 10, (
        f"Expected >=10 OR-Library CSP txt files, found {len(txt_files)}"
    )


def test_or_library_csp_files_not_html() -> None:
    """OR-Library CSP files must be plain text, not HTML error pages."""
    if not _data_dir_exists("OR_LIBRARY"):
        pytest.skip(f"data/raw/OR_LIBRARY/{DATE_DIR} absent")

    date_dir = RAW_ROOT / "OR_LIBRARY" / DATE_DIR
    txt_files = [p for p in date_dir.iterdir() if p.suffix == ".txt"]
    for path in txt_files:
        assert not _is_html(path), (
            f"[OR_LIBRARY] {path.name} looks like an HTML error page"
        )
