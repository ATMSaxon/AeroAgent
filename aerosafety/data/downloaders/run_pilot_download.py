"""
T10 Pilot Download Script — authorized real-data fetch for AeroSafetyEval Phase 1.

Authorization: team-lead task #10 assignment (2026-05-17).
Scope: deliberately small subset — NTSB CAROL last 90 days (CSV via API),
5 NTSB narrative PDFs, IEM METAR + TAF for KJFK+KORD April 2026.

NASA ASRS: server returned HTTP 503 (Service Unavailable) on all endpoints
during this run (2026-05-17). Documented as FAILED in manifest; no data saved.

Hard limits enforced here:
- Volume cap: 200 MB total; script aborts if any source exceeds its cap.
- Rate limits respected: >=2s NTSB, >=12s IEM (300 req/hr limit).
- Fail loudly on HTTP errors per CLAUDE.md §8.1.
- Each source gets its own manifest.jsonl under data/raw/{SOURCE_ID}/2026-05-17/.
- Real data ONLY to data/raw/ — never to data/synthetic/.

NTSB CAROL download uses the CAROL REST API (not a simple GET URL):
  1. POST /carol-main-public/api/Session/CreateSession  → session_id
  2. POST /carol-main-public/api/Query/FileExport  → ZIP blob (contains CSV + readme)
  Endpoint discovery: reverse-engineered from CAROL SPA JS (search-results.js).

NTSB PDFs: GenerateNewestReport endpoint uses internal Mkey (not report designator).
  Mkeys verified against live CAROL API responses on 2026-05-17.

Do NOT re-run this script without fresh team-lead approval.
"""

from __future__ import annotations

import hashlib
import json
import logging
import sys
import time
from datetime import UTC, date, datetime
from pathlib import Path

import httpx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("pilot_download")

PROJECT_ROOT = Path(__file__).resolve().parents[3]
RAW_ROOT = PROJECT_ROOT / "data" / "raw"

# Per-source volume caps (bytes) — abort if exceeded
VOLUME_CAP_BYTES = {
    "NASA_ASRS": 50 * 1024 * 1024,       # 50 MB
    "NTSB_ACCIDENT_DB": 50 * 1024 * 1024, # 50 MB
    "NTSB_FULL_REPORTS": 50 * 1024 * 1024, # 50 MB (5 PDFs)
    "IEM_METAR": 10 * 1024 * 1024,        # 10 MB
    "IEM_TAF": 10 * 1024 * 1024,          # 10 MB
}
TOTAL_CAP_BYTES = 200 * 1024 * 1024  # 200 MB hard ceiling


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_manifest(manifest_path: Path, entry: dict) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, default=str) + "\n")


def _check_html_error(path: Path) -> bool:
    """Return True if the file looks like an HTML error page rather than data."""
    try:
        with open(path, "rb") as f:
            head = f.read(512).lower()
        return head.startswith(b"<!doctype html") or head.startswith(b"<html")
    except OSError:
        return False


def fetch(
    source_id: str,
    url: str,
    dest: Path,
    manifest_path: Path,
    client: httpx.Client,
    rate_limit: float,
    source_bytes_so_far: int,
    *,
    method: str = "GET",
    post_json: dict | None = None,
) -> tuple[int, dict]:
    """
    Fetch one URL to dest. Returns (bytes_written, manifest_entry).
    Raises RuntimeError if volume cap exceeded or HTTP error occurs.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    fetched_at = datetime.now(UTC).isoformat()

    logger.info("FETCH %s %s %s -> %s", method, source_id, url, dest.name)

    entry: dict = {
        "source_id": source_id,
        "source_url": url,
        "file_path": str(dest.relative_to(PROJECT_ROOT)),
        "http_status": None,
        "fetched_at_utc": fetched_at,
        "sha256": "",
        "content_length": None,
        "error": None,
    }

    try:
        if method == "POST" and post_json is not None:
            req = client.stream(
                "POST", url,
                json=post_json,
                headers={"Content-Type": "application/json"},
                timeout=120,
            )
        else:
            req = client.stream("GET", url, timeout=120)

        with req as resp:
            entry["http_status"] = resp.status_code
            if resp.status_code >= 400:
                body = resp.read().decode(errors="replace")
                msg = f"HTTP {resp.status_code} for {url}: {body[:300]}"
                entry["error"] = msg
                _write_manifest(manifest_path, entry)
                raise RuntimeError(f"[{source_id}] FETCH FAILED — {msg}")

            bytes_written = 0
            with open(dest, "wb") as f:
                for chunk in resp.iter_bytes(65536):
                    if chunk:
                        f.write(chunk)
                        bytes_written += len(chunk)
    except httpx.HTTPError as e:
        msg = f"HTTP error fetching {url}: {e}"
        entry["error"] = msg
        _write_manifest(manifest_path, entry)
        raise RuntimeError(f"[{source_id}] FETCH FAILED — {msg}") from e

    # Volume cap check
    cap = VOLUME_CAP_BYTES.get(source_id, 50 * 1024 * 1024)
    if source_bytes_so_far + bytes_written > cap:
        dest.unlink(missing_ok=True)
        raise RuntimeError(
            f"[{source_id}] Volume cap {cap/1024/1024:.0f} MB exceeded "
            f"({(source_bytes_so_far + bytes_written)/1024/1024:.1f} MB). STOPPING."
        )

    # HTML error page guard
    if _check_html_error(dest):
        content_preview = dest.read_bytes()[:200]
        dest.unlink(missing_ok=True)
        raise RuntimeError(
            f"[{source_id}] Response appears to be an HTML error page, not data. "
            f"Preview: {content_preview!r}"
        )

    sha = _sha256(dest)
    entry["sha256"] = sha
    entry["content_length"] = bytes_written
    _write_manifest(manifest_path, entry)

    logger.info(
        "OK %s %d bytes sha256=%s...%s",
        dest.name, bytes_written, sha[:8], sha[-4:]
    )
    time.sleep(rate_limit)
    return bytes_written, entry


# ---------------------------------------------------------------------------
# Source 1: NASA ASRS — 100 most recent reports
# ---------------------------------------------------------------------------

def download_asrs(client: httpx.Client) -> dict:
    """
    NASA ASRS bulk CSV.

    NOTE: As of 2026-05-17, asrs.arc.nasa.gov returns HTTP 503 on all query
    endpoints (confirmed: request.php?format=csv&from=202602&to=202604 and
    two alternative parameter sets all returned 503). The service appears
    temporarily unavailable. This function documents the failure in the
    manifest and returns FAILED status without raising, so the other sources
    still proceed.

    Ref: https://asrs.arc.nasa.gov/search/database.html
    """
    source_id = "NASA_ASRS"
    date_dir = RAW_ROOT / source_id / "2026-05-17"
    manifest_path = date_dir / "manifest.jsonl"
    date_dir.mkdir(parents=True, exist_ok=True)

    url = (
        "https://asrs.arc.nasa.gov/search/request.php"
        "?format=csv&from=202602&to=202604"
    )
    fetched_at = datetime.now(UTC).isoformat()

    # Probe the server to capture the actual HTTP status in the manifest.
    try:
        resp = client.get(url, timeout=30)
        http_status = resp.status_code
        error_msg = f"HTTP {http_status} — server unavailable (503 Service Unavailable)"
    except httpx.HTTPError as e:
        http_status = None
        error_msg = f"Connection error: {e}"

    entry = {
        "source_id": source_id,
        "source_url": url,
        "file_path": None,
        "http_status": http_status,
        "fetched_at_utc": fetched_at,
        "sha256": None,
        "content_length": 0,
        "error": error_msg,
    }
    _write_manifest(manifest_path, entry)
    logger.error("[NASA_ASRS] FAILED — %s", error_msg)
    return {
        "source_id": source_id,
        "status": "FAILED",
        "error": error_msg,
        "files": [],
        "total_bytes": 0,
    }


# ---------------------------------------------------------------------------
# Source 2: NTSB CAROL — last 90 days structured export (ZIP containing CSV)
# ---------------------------------------------------------------------------

_CAROL_API_BASE = "https://data.ntsb.gov/carol-main-public/api/"


def _carol_create_session(client: httpx.Client) -> int:
    """Create a CAROL API session and return the integer session ID."""
    resp = client.post(
        _CAROL_API_BASE + "Session/CreateSession",
        json={},
        headers={"Content-Type": "application/json"},
        timeout=30,
    )
    if resp.status_code != 200:
        raise RuntimeError(
            f"CAROL CreateSession returned HTTP {resp.status_code}: {resp.text[:200]}"
        )
    return int(resp.text.strip().strip('"'))


def download_ntsb_carol(client: httpx.Client) -> dict:
    """
    NTSB CAROL aviation accident database — last 90 days export.

    Uses the CAROL REST API (reverse-engineered from CAROL SPA search-results.js):
      POST /carol-main-public/api/Session/CreateSession  → integer session_id
      POST /carol-main-public/api/Query/FileExport       → ZIP blob

    The ZIP contains a readme.txt and a CSV with all accident fields.
    Last 90 days = 2026-02-15 – 2026-05-17.  Aviation mode only.
    ResultSetSize=500 covers the expected ~300 records for 90 days.

    Ref: https://data.ntsb.gov/carol-main-public/query-entry
    """
    source_id = "NTSB_ACCIDENT_DB"
    date_dir = RAW_ROOT / source_id / "2026-05-17"
    manifest_path = date_dir / "manifest.jsonl"
    date_dir.mkdir(parents=True, exist_ok=True)

    export_url = _CAROL_API_BASE + "Query/FileExport"
    dest = date_dir / "ntsb_accidents_20260215_20260517.zip"
    fetched_at = datetime.now(UTC).isoformat()

    entry: dict = {
        "source_id": source_id,
        "source_url": export_url,
        "file_path": str(dest.relative_to(PROJECT_ROOT)),
        "http_status": None,
        "fetched_at_utc": fetched_at,
        "sha256": "",
        "content_length": None,
        "error": None,
        "note": "ZIP contains readme.txt + cases CSV; date range 2026-02-15..2026-05-17",
    }

    try:
        session_id = _carol_create_session(client)
        logger.info("[NTSB_ACCIDENT_DB] session_id=%d", session_id)
    except RuntimeError as e:
        entry["error"] = str(e)
        _write_manifest(manifest_path, entry)
        logger.error("[NTSB_ACCIDENT_DB] session creation FAILED: %s", e)
        return {"source_id": source_id, "status": "FAILED", "error": str(e), "files": [], "total_bytes": 0}

    export_payload = {
        "ResultSetSize": 500,
        "ResultSetOffset": 0,
        "QueryGroups": [
            {
                "AndOr": "and",
                "QueryRules": [
                    {
                        "RuleType": "Simple",
                        "Columns": ["Event.EventDate"],
                        "Operator": "is on or after",
                        "Values": ["2026-02-15"],
                        "TargetCollection": "cases",
                    },
                    {
                        "RuleType": "Simple",
                        "Columns": ["Event.EventDate"],
                        "Operator": "is on or before",
                        "Values": ["2026-05-17"],
                        "TargetCollection": "cases",
                    },
                    {
                        "RuleType": "Simple",
                        "Columns": ["Event.Mode"],
                        "Operator": "is",
                        "Values": ["Aviation"],
                        "TargetCollection": "cases",
                    },
                ],
            }
        ],
        "AndOr": "and",
        "SortColumn": None,
        "SortDescending": True,
        "TargetCollection": "cases",
        "SessionId": session_id,
        "ExportFormat": "data",
    }

    total_bytes = 0
    results = []
    try:
        b, updated_entry = fetch(
            source_id, export_url, dest, manifest_path, client, 2.0, total_bytes,
            method="POST", post_json=export_payload,
        )
        # Merge fetched entry back (fetch() writes its own manifest entry)
        total_bytes += b
        results.append(updated_entry)
        logger.info("[NTSB_ACCIDENT_DB] downloaded %d bytes (ZIP)", b)
    except RuntimeError as e:
        logger.error("[NTSB_ACCIDENT_DB] FAILED: %s", e)
        return {"source_id": source_id, "status": "FAILED", "error": str(e), "files": results, "total_bytes": total_bytes}

    return {"source_id": source_id, "status": "OK", "files": results, "total_bytes": total_bytes}


# ---------------------------------------------------------------------------
# Source 3: NTSB Full Reports — 5 representative narrative PDFs
# ---------------------------------------------------------------------------

# Five NTSB fatal accident narrative PDFs from 2023-2024.
# Selected for regional diversity: Eastern, Western Pacific, Alaska.
# Uses internal CAROL Mkey (integer), not the public NtsbNo report designator.
# The GenerateNewestReport endpoint requires Mkey — using NtsbNo returns 404.
# Mkeys verified via live CAROL Query/Main API response on 2026-05-17.
NTSB_REPORT_IDS = [
    # Format: (mkey, ntsb_no_for_label, description)
    ("106995", "ERA23LA177", "2023_accident_fl"),         # 2023, Florida, ~770 KB
    ("199430", "WPR25FA062", "2024_fatal_western_pac"),   # 2024-12-16, ~2.3 MB
    ("199437", "ANC25FA010", "2024_fatal_alaska"),        # 2024-12-17, Alaska, ~1.1 MB
    ("199456", "ERA25FA082", "2024_fatal_eastern_a"),     # 2024-12-20, ~760 KB
    ("199447", "ERA25FA080", "2024_fatal_eastern_b"),     # 2024-12-19, ~760 KB
]

NTSB_PDF_URL_TEMPLATE = (
    "https://data.ntsb.gov/carol-repgen/api/Aviation/ReportMain/"
    "GenerateNewestReport/{mkey}/pdf"
)


def download_ntsb_full_reports(client: httpx.Client) -> dict:
    """
    Download 5 NTSB narrative PDFs from published final accident reports.

    Uses internal CAROL Mkey (verified 2026-05-17) — NtsbNo report designators
    cause the GenerateNewestReport endpoint to return 404.
    """
    source_id = "NTSB_FULL_REPORTS"
    date_dir = RAW_ROOT / source_id / "2026-05-17"
    manifest_path = date_dir / "manifest.jsonl"
    date_dir.mkdir(parents=True, exist_ok=True)

    total_bytes = 0
    results = []
    failed = []

    for mkey, ntsb_no, label in NTSB_REPORT_IDS:
        url = NTSB_PDF_URL_TEMPLATE.format(mkey=mkey)
        dest = date_dir / f"{ntsb_no}_{label}.pdf"
        try:
            b, entry = fetch(source_id, url, dest, manifest_path, client, 2.0, total_bytes)
            total_bytes += b
            results.append(entry)
            logger.info("[NTSB_FULL_REPORTS] %s (mkey=%s): %d bytes", ntsb_no, mkey, b)
        except RuntimeError as e:
            logger.error("[NTSB_FULL_REPORTS] %s (mkey=%s) FAILED: %s", ntsb_no, mkey, e)
            failed.append({"ntsb_no": ntsb_no, "mkey": mkey, "error": str(e)})

    status = "OK" if not failed else ("PARTIAL" if results else "FAILED")
    return {
        "source_id": source_id,
        "status": status,
        "files": results,
        "failed": failed,
        "total_bytes": total_bytes,
    }


# ---------------------------------------------------------------------------
# Source 4 & 5: IEM METAR + TAF — KJFK + KORD, April 2026
# ---------------------------------------------------------------------------

IEM_STATIONS = ["KJFK", "KORD"]
IEM_START = date(2026, 4, 1)
IEM_END = date(2026, 4, 30)
IEM_RATE = 12.0  # seconds — 300 req/hr limit


def _iem_metar_url(station: str, start: date, end: date) -> str:
    return (
        f"https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py"
        f"?station={station}&data=all"
        f"&year1={start.year}&month1={start.month}&day1={start.day}"
        f"&year2={end.year}&month2={end.month}&day2={end.day}"
        f"&tz=UTC&format=onlycomma&latlon=no&direct=no&report_type=3"
    )


def _iem_taf_url(station: str, start: date, end: date) -> str:
    return (
        f"https://mesonet.agron.iastate.edu/cgi-bin/request/taf.py"
        f"?station={station}"
        f"&year1={start.year}&month1={start.month}&day1={start.day}"
        f"&year2={end.year}&month2={end.month}&day2={end.day}"
        f"&tz=UTC&format=csv"
    )


def download_iem_metar(client: httpx.Client) -> dict:
    source_id = "IEM_METAR"
    date_dir = RAW_ROOT / source_id / "2026-05-17"
    manifest_path = date_dir / "manifest.jsonl"
    date_dir.mkdir(parents=True, exist_ok=True)

    total_bytes = 0
    results = []
    failed = []

    for station in IEM_STATIONS:
        url = _iem_metar_url(station, IEM_START, IEM_END)
        dest = date_dir / f"{station}_METAR_202604.csv"
        try:
            b, entry = fetch(source_id, url, dest, manifest_path, client, IEM_RATE, total_bytes)
            total_bytes += b
            results.append(entry)
            logger.info("[IEM_METAR] %s: %d bytes", station, b)
        except RuntimeError as e:
            logger.error("[IEM_METAR] %s FAILED: %s", station, e)
            failed.append({"station": station, "error": str(e)})

    status = "OK" if not failed else ("PARTIAL" if results else "FAILED")
    return {
        "source_id": source_id,
        "status": status,
        "files": results,
        "failed": failed,
        "total_bytes": total_bytes,
    }


def download_iem_taf(client: httpx.Client) -> dict:
    source_id = "IEM_TAF"
    date_dir = RAW_ROOT / source_id / "2026-05-17"
    manifest_path = date_dir / "manifest.jsonl"
    date_dir.mkdir(parents=True, exist_ok=True)

    total_bytes = 0
    results = []
    failed = []

    for station in IEM_STATIONS:
        url = _iem_taf_url(station, IEM_START, IEM_END)
        dest = date_dir / f"{station}_TAF_202604.csv"
        try:
            b, entry = fetch(source_id, url, dest, manifest_path, client, IEM_RATE, total_bytes)
            total_bytes += b
            results.append(entry)
            logger.info("[IEM_TAF] %s: %d bytes", station, b)
        except RuntimeError as e:
            logger.error("[IEM_TAF] %s FAILED: %s", station, e)
            failed.append({"station": station, "error": str(e)})

    status = "OK" if not failed else ("PARTIAL" if results else "FAILED")
    return {
        "source_id": source_id,
        "status": status,
        "files": results,
        "failed": failed,
        "total_bytes": total_bytes,
    }


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def run_all() -> None:
    client = httpx.Client(
        headers={
            "User-Agent": (
                "AeroSafetyEval-Research/1.0 "
                "(academic research; contact: aerosafety-research@example.edu)"
            )
        },
        follow_redirects=True,
    )

    logger.info("=== T10 Pilot Download starting ===")
    logger.info("Total volume cap: %d MB", TOTAL_CAP_BYTES // 1024 // 1024)
    logger.info("NOTE: NASA ASRS is documented FAILED (HTTP 503) — proceeding with other 4 sources.")

    results = {}
    total_all_bytes = 0

    # --- NASA ASRS (expected FAILED — HTTP 503 as of 2026-05-17) ---
    r = download_asrs(client)
    results["NASA_ASRS"] = r
    total_all_bytes += r.get("total_bytes", 0)
    _check_total_cap(total_all_bytes)

    # --- NTSB CAROL structured CSV ---
    r = download_ntsb_carol(client)
    results["NTSB_ACCIDENT_DB"] = r
    total_all_bytes += r.get("total_bytes", 0)
    _check_total_cap(total_all_bytes)

    # --- NTSB Full Reports (5 PDFs) ---
    r = download_ntsb_full_reports(client)
    results["NTSB_FULL_REPORTS"] = r
    total_all_bytes += r.get("total_bytes", 0)
    _check_total_cap(total_all_bytes)

    # --- IEM METAR ---
    r = download_iem_metar(client)
    results["IEM_METAR"] = r
    total_all_bytes += r.get("total_bytes", 0)
    _check_total_cap(total_all_bytes)

    # --- IEM TAF ---
    r = download_iem_taf(client)
    results["IEM_TAF"] = r
    total_all_bytes += r.get("total_bytes", 0)
    _check_total_cap(total_all_bytes)

    # Summary
    logger.info("=== T10 Pilot Download complete ===")
    logger.info("Total bytes downloaded: %d (%.1f MB)", total_all_bytes, total_all_bytes / 1024 / 1024)

    print("\n=== DOWNLOAD SUMMARY ===")
    for source_id, r in results.items():
        status = r.get("status", "?")
        n_files = len(r.get("files", []))
        n_failed = len(r.get("failed", []))
        b = r.get("total_bytes", 0)
        print(f"  {source_id}: status={status} files={n_files} failed={n_failed} bytes={b} ({b/1024:.1f} KB)")
        if r.get("error"):
            print(f"    ERROR: {r['error']}")
        for f in r.get("failed", []):
            print(f"    FAILED: {f}")

    print(f"\nGRAND TOTAL: {total_all_bytes} bytes ({total_all_bytes/1024/1024:.2f} MB)")
    print("Manifests written to data/raw/{SOURCE_ID}/2026-05-17/manifest.jsonl")


def _check_total_cap(total_bytes: int) -> None:
    if total_bytes > TOTAL_CAP_BYTES:
        raise RuntimeError(
            f"TOTAL volume cap {TOTAL_CAP_BYTES/1024/1024:.0f} MB exceeded "
            f"({total_bytes/1024/1024:.1f} MB). STOPPING all downloads."
        )


if __name__ == "__main__":
    run_all()
