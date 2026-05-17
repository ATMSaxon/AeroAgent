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
    """Each manifest entry with a non-None sha256 must match the actual file."""
    if not _data_dir_exists(source_id):
        pytest.skip(f"data/raw/{source_id}/{DATE_DIR} absent")

    entries = _read_manifest(source_id)
    verified = 0
    for entry in entries:
        sha_expected = entry.get("sha256")
        file_path_rel = entry.get("file_path")
        if not sha_expected or not file_path_rel:
            continue
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

def test_asrs_manifest_documents_failure() -> None:
    """NASA ASRS returned HTTP 503 — manifest must record the failure."""
    if not _data_dir_exists("NASA_ASRS"):
        pytest.skip(f"data/raw/NASA_ASRS/{DATE_DIR} absent")

    entries = _read_manifest("NASA_ASRS")
    assert len(entries) == 1, (
        f"Expected exactly 1 manifest entry for NASA_ASRS (the failure record), "
        f"got {len(entries)}"
    )
    entry = entries[0]
    assert entry.get("error") is not None, "NASA_ASRS manifest entry should record an error"
    assert entry.get("http_status") == 503, (
        f"Expected http_status=503, got {entry.get('http_status')}"
    )
    assert entry.get("sha256") is None or entry.get("sha256") == "", (
        "NASA_ASRS failure entry should not have a sha256"
    )


# ---------------------------------------------------------------------------
# Integrity: file counts match expectations
# ---------------------------------------------------------------------------

def test_ntsb_full_reports_count() -> None:
    """Exactly 5 PDF narrative files expected."""
    if not _data_dir_exists("NTSB_FULL_REPORTS"):
        pytest.skip(f"data/raw/NTSB_FULL_REPORTS/{DATE_DIR} absent")

    date_dir = RAW_ROOT / "NTSB_FULL_REPORTS" / DATE_DIR
    pdfs = [p for p in date_dir.iterdir() if p.suffix == ".pdf"]
    assert len(pdfs) == 5, f"Expected 5 NTSB PDF files, found {len(pdfs)}: {[p.name for p in pdfs]}"


def test_iem_metar_station_count() -> None:
    """Exactly 2 METAR CSVs expected (KJFK, KORD)."""
    if not _data_dir_exists("IEM_METAR"):
        pytest.skip(f"data/raw/IEM_METAR/{DATE_DIR} absent")

    date_dir = RAW_ROOT / "IEM_METAR" / DATE_DIR
    csvs = [p for p in date_dir.iterdir() if p.suffix == ".csv"]
    assert len(csvs) == 2, f"Expected 2 METAR CSV files, found {len(csvs)}"


def test_iem_taf_station_count() -> None:
    """Exactly 2 TAF CSVs expected (KJFK, KORD)."""
    if not _data_dir_exists("IEM_TAF"):
        pytest.skip(f"data/raw/IEM_TAF/{DATE_DIR} absent")

    date_dir = RAW_ROOT / "IEM_TAF" / DATE_DIR
    csvs = [p for p in date_dir.iterdir() if p.suffix == ".csv"]
    assert len(csvs) == 2, f"Expected 2 TAF CSV files, found {len(csvs)}"


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
    for source_id in SOURCES_OK + SOURCES_FAILED:
        if not _data_dir_exists(source_id):
            continue
        entries = _read_manifest(source_id)
        for entry in entries:
            assert entry.get("source_id") == source_id, (
                f"Manifest entry in {source_id} has source_id={entry.get('source_id')!r}"
            )
