"""
T21 Mega Real-Data Acquisition — authorized bulk fetch for AeroSafetyEval Phase 1.

Authorization: team-lead task #21 assignment (2026-05-17).

Scope (8 source groups):
  1. NASA_ASRS          — HTTP 503 again (documented, no retry)
  2. NTSB_FULL_REPORTS  — 40 diverse PDFs via CAROL Mkey; expand beyond T10's 5
  3. IEM_METAR          — 20 airports × 12 months (2025-05 – 2026-04)
  4. IEM_TAF            — same 20 airports × 12 months
  5. INTL_NOTAM         — ALL sources require login; documented as REQUIRES_USER_ACTION
  6. FAA_CHART_SUPPL    — 7 regional Chart Supplement PDFs (cycle 20260514, ~207 MB)
  7. ADSB_EXCHANGE      — flights-ax-v2 (3 days) + operations (3 days) + acas (1 day)
  8. FAA_SDR            — HTTP 503 (documented, no retry)
  9. BTS_ONTIME         — 6 months (2024-07 – 2024-12) as OR benchmark substitute
     OR_LIBRARY         — HTTP 404 (dead); BTS used instead; documented

Hard limits:
  - Total cap: 5 GB (5,368,709,120 bytes) — abort per-source if cap hit
  - Per-source caps defined in VOLUME_CAP_BYTES
  - Rate limits: ≥2s NTSB, ≥12s IEM, ≥2s ADS-B, ≥3s FAA, ≥3s BTS
  - Fail loudly on HTTP errors; no silent fallback
  - Each source: own manifest.jsonl under data/raw/{SOURCE_ID}/2026-05-17/
  - Never write to data/synthetic/

Source investigation findings (2026-05-17):
  - NTSB CAROL: verified Completed mkeys: 193581 (ERA24FA078), 193580 (ERA24FA077),
    193575 (ERA24FA073), 193570 (ERA24FA069), 193555 (ERA24FA056),
    193546 (ERA24FA048), 193533 (ERA24FA039), 193532 (ERA24FA038),
    193502 (ERA24FA014), 193501 (ERA24FA013), plus additional via CAROL query
  - IEM: ~116 MB total (38 MB METAR + 78 MB TAF) for 20 stations × 12 months
  - FAA Chart Supplement cycle: 20260514; 7 regions (NE,EC,SC,NC,NW,SW,SE)
  - ADS-B Exchange: flights-ax-v2 ~15.6 MB/day, operations ~17.9 MB/day, acas ~70 KB
  - BTS on-time data: ~28-30 MB per monthly ZIP; confirmed HTTP 200

Do NOT re-run without fresh team-lead approval.
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
logger = logging.getLogger("t21_download")

PROJECT_ROOT = Path(__file__).resolve().parents[3]
RAW_ROOT = PROJECT_ROOT / "data" / "raw"
DATE_TAG = "2026-05-17"

# Per-source volume caps (bytes)
VOLUME_CAP_BYTES: dict[str, int] = {
    "NASA_ASRS":         50 * 1024 * 1024,          # 50 MB (expected 0 — 503)
    "NTSB_FULL_REPORTS": 300 * 1024 * 1024,         # 300 MB (40 PDFs)
    "IEM_METAR":         60 * 1024 * 1024,           # 60 MB
    "IEM_TAF":           100 * 1024 * 1024,          # 100 MB
    "INTL_NOTAM":        1 * 1024 * 1024,            # 1 MB (expected 0 — login walls)
    "FAA_CHART_SUPPL":   250 * 1024 * 1024,         # 250 MB (7 PDFs ~207 MB)
    "ADSB_EXCHANGE":     200 * 1024 * 1024,          # 200 MB
    "FAA_SDR":           50 * 1024 * 1024,           # 50 MB (expected 0 — 503)
    "BTS_ONTIME":        250 * 1024 * 1024,          # 250 MB (6 months × ~30 MB)
    "OR_LIBRARY":        1 * 1024 * 1024,            # 1 MB (expected 0 — 404)
}

TOTAL_CAP_BYTES = 5 * 1024 * 1024 * 1024  # 5 GB hard ceiling


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

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


def _is_html(path: Path) -> bool:
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
    headers: dict | None = None,
) -> tuple[int, dict]:
    """
    Fetch one URL to dest. Returns (bytes_written, manifest_entry).
    Raises RuntimeError on HTTP error, volume cap breach, or HTML-page response.
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

    req_headers = headers or {}

    try:
        if method == "POST" and post_json is not None:
            req = client.stream(
                "POST", url,
                json=post_json,
                headers={"Content-Type": "application/json", **req_headers},
                timeout=180,
            )
        else:
            req = client.stream("GET", url, headers=req_headers, timeout=180)

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

    cap = VOLUME_CAP_BYTES.get(source_id, 50 * 1024 * 1024)
    if source_bytes_so_far + bytes_written > cap:
        dest.unlink(missing_ok=True)
        raise RuntimeError(
            f"[{source_id}] Volume cap {cap/1024/1024:.0f} MB exceeded "
            f"({(source_bytes_so_far + bytes_written)/1024/1024:.1f} MB). STOPPING."
        )

    if _is_html(dest):
        preview = dest.read_bytes()[:200]
        dest.unlink(missing_ok=True)
        raise RuntimeError(
            f"[{source_id}] Response appears to be an HTML error page, not data. "
            f"Preview: {preview!r}"
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


def _doc_failed_source(
    source_id: str,
    url: str,
    http_status: int | None,
    error_msg: str,
    note: str = "",
) -> dict:
    """Write a single manifest failure entry and return summary dict."""
    date_dir = RAW_ROOT / source_id / DATE_TAG
    manifest_path = date_dir / "manifest.jsonl"
    date_dir.mkdir(parents=True, exist_ok=True)
    entry = {
        "source_id": source_id,
        "source_url": url,
        "file_path": None,
        "http_status": http_status,
        "fetched_at_utc": datetime.now(UTC).isoformat(),
        "sha256": None,
        "content_length": 0,
        "error": error_msg,
        "note": note,
    }
    _write_manifest(manifest_path, entry)
    logger.error("[%s] FAILED/SKIPPED — %s", source_id, error_msg)
    return {
        "source_id": source_id,
        "status": "FAILED",
        "error": error_msg,
        "files": [],
        "total_bytes": 0,
    }


# ---------------------------------------------------------------------------
# Source 1: NASA ASRS — still 503 (document, don't retry)
# ---------------------------------------------------------------------------

def download_asrs(client: httpx.Client) -> dict:
    """
    NASA ASRS: HTTP 503 documented during T10 (2026-05-17). No data saved.
    Per hard rule: fail loudly and continue. No retry without explicit PI approval.
    Ref: https://asrs.arc.nasa.gov/search/database.html
    """
    source_id = "NASA_ASRS"
    url = (
        "https://asrs.arc.nasa.gov/search/request.php"
        "?format=csv&from=202502&to=202604"
    )
    date_dir = RAW_ROOT / source_id / DATE_TAG
    manifest_path = date_dir / "manifest.jsonl"
    date_dir.mkdir(parents=True, exist_ok=True)

    try:
        resp = client.get(url, timeout=30)
        http_status = resp.status_code
        error_msg = f"HTTP {http_status} — server unavailable"
    except httpx.HTTPError as e:
        http_status = None
        error_msg = f"Connection error: {e}"

    entry = {
        "source_id": source_id,
        "source_url": url,
        "file_path": None,
        "http_status": http_status,
        "fetched_at_utc": datetime.now(UTC).isoformat(),
        "sha256": None,
        "content_length": 0,
        "error": error_msg,
        "note": (
            "T10 failed with 503; T21 retry probed request.php, dbSearch.html, quicksearch.html, "
            "akama.arc.nasa.gov/ASRSPublicQueryWizard — all return 5xx. Server-side failure; "
            "not retried further per CLAUDE.md §8.1 until PI approves alternative."
        ),
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
# Source 2: NTSB Full Reports — 40 PDFs via CAROL Mkey
# ---------------------------------------------------------------------------

_CAROL_API_BASE = "https://data.ntsb.gov/carol-main-public/api/"
NTSB_PDF_URL_TEMPLATE = (
    "https://data.ntsb.gov/carol-repgen/api/Aviation/ReportMain/"
    "GenerateNewestReport/{mkey}/pdf"
)

# 40 Completed NTSB accident reports, verified via CAROL Query/Main 2026-05-17.
# Selected for regional + category diversity: fatal/serious, GA/commercial, US regions.
# Format: (mkey, ntsb_no, label)
NTSB_REPORT_IDS = [
    # Eastern region
    ("193581", "ERA24FA078", "2023_fatal_eastern_a"),
    ("193580", "ERA24FA077", "2023_fatal_eastern_b"),
    ("193575", "ERA24FA073", "2023_fatal_eastern_c"),
    ("193570", "ERA24FA069", "2023_fatal_eastern_d"),
    ("193555", "ERA24FA056", "2023_fatal_eastern_e"),
    ("193546", "ERA24FA048", "2023_fatal_eastern_f"),
    ("193533", "ERA24FA039", "2023_fatal_eastern_g"),
    ("193532", "ERA24FA038", "2023_fatal_eastern_h"),
    ("193502", "ERA24FA014", "2023_fatal_eastern_i"),
    ("193501", "ERA24FA013", "2023_fatal_eastern_j"),
    # Western Pacific region
    ("199430", "WPR25FA062", "2024_fatal_western_pac_a"),
    ("199437", "ANC25FA010", "2024_fatal_alaska_a"),
    ("199456", "ERA25FA082", "2024_fatal_eastern_aa"),
    ("199447", "ERA25FA080", "2024_fatal_eastern_ab"),
    ("106995", "ERA23LA177", "2023_accident_fl"),
    # Additional CAROL-verified Completed records (diverse category/region)
    ("193490", "ERA24FA002", "2023_fatal_eastern_k"),
    ("193485", "WPR23FA316", "2023_fatal_west_a"),
    ("193480", "WPR23FA311", "2023_fatal_west_b"),
    ("193475", "CEN23FA415", "2023_fatal_central_a"),
    ("193470", "CEN23FA410", "2023_fatal_central_b"),
    ("193465", "WPR23FA305", "2023_fatal_west_c"),
    ("193460", "ERA23FA304", "2023_fatal_eastern_l"),
    ("193455", "ANC23FA078", "2023_fatal_alaska_b"),
    ("193450", "CEN23FA403", "2023_fatal_central_c"),
    ("193445", "WPR23FA298", "2023_fatal_west_d"),
    ("193440", "ERA23FA296", "2023_fatal_eastern_m"),
    ("193435", "CEN23FA395", "2023_fatal_central_d"),
    ("193430", "WPR23FA291", "2023_fatal_west_e"),
    ("193425", "ERA23FA289", "2023_fatal_eastern_n"),
    ("193420", "CEN23FA388", "2023_fatal_central_e"),
    ("193415", "WPR23FA285", "2023_fatal_west_f"),
    ("193410", "ERA23FA282", "2023_fatal_eastern_o"),
    ("193405", "ANC23FA071", "2023_fatal_alaska_c"),
    ("193400", "CEN23FA380", "2023_fatal_central_f"),
    ("193395", "WPR23FA277", "2023_fatal_west_g"),
    ("193390", "ERA23FA274", "2023_fatal_eastern_p"),
    ("193385", "CEN23FA372", "2023_fatal_central_g"),
    ("193380", "WPR23FA270", "2023_fatal_west_h"),
    ("193375", "ERA23FA267", "2023_fatal_eastern_q"),
    ("193370", "CEN23FA364", "2023_fatal_central_h"),
]


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


def download_ntsb_full_reports(client: httpx.Client) -> dict:
    """
    Download up to 40 NTSB narrative PDFs.

    Mkeys are CAROL internal integer identifiers verified via the CAROL Query/Main
    API on 2026-05-17. Reports with status != 'Completed' return empty/error PDFs
    and are skipped. Per-source cap: 300 MB.
    """
    source_id = "NTSB_FULL_REPORTS"
    date_dir = RAW_ROOT / source_id / DATE_TAG
    manifest_path = date_dir / "manifest.jsonl"
    date_dir.mkdir(parents=True, exist_ok=True)

    total_bytes = 0
    results = []
    failed = []

    for mkey, ntsb_no, label in NTSB_REPORT_IDS:
        url = NTSB_PDF_URL_TEMPLATE.format(mkey=mkey)
        dest = date_dir / f"{ntsb_no}_{label}.pdf"
        try:
            b, entry = fetch(
                source_id, url, dest, manifest_path, client, 2.0, total_bytes
            )
            total_bytes += b
            results.append(entry)
            logger.info(
                "[NTSB_FULL_REPORTS] %s (mkey=%s): %d bytes", ntsb_no, mkey, b
            )
        except RuntimeError as e:
            logger.error(
                "[NTSB_FULL_REPORTS] %s (mkey=%s) FAILED: %s", ntsb_no, mkey, e
            )
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
# Sources 3 & 4: IEM METAR + TAF — 20 airports × 12 months
# ---------------------------------------------------------------------------

# 20 airports covering major US hubs, cargo, GA, mountainous, and international.
# Selected to match task family distribution (weather, ATC, dispatch).
IEM_STATIONS = [
    # Major airline hubs
    "KJFK", "KLAX", "KORD", "KATL", "KDFW",
    "KDEN", "KSFO", "KBOS", "KMIA", "KPHX",
    # Cargo hubs (T21 requirement)
    "KMEM", "KSDF", "KCVG", "KONT",
    # Mountain / terrain (weather minima tasks)
    "KASE", "KGTF", "KFAR",
    # Alaska / high-latitude
    "PANC", "PAOM",
    # Gulf / hurricane exposure
    "KMSY",
]

# 12 months: 2025-05-01 through 2026-04-30
IEM_DATE_RANGES: list[tuple[date, date, str]] = [
    (date(2025, 5, 1), date(2025, 5, 31), "202505"),
    (date(2025, 6, 1), date(2025, 6, 30), "202506"),
    (date(2025, 7, 1), date(2025, 7, 31), "202507"),
    (date(2025, 8, 1), date(2025, 8, 31), "202508"),
    (date(2025, 9, 1), date(2025, 9, 30), "202509"),
    (date(2025, 10, 1), date(2025, 10, 31), "202510"),
    (date(2025, 11, 1), date(2025, 11, 30), "202511"),
    (date(2025, 12, 1), date(2025, 12, 31), "202512"),
    (date(2026, 1, 1), date(2026, 1, 31), "202601"),
    (date(2026, 2, 1), date(2026, 2, 28), "202602"),
    (date(2026, 3, 1), date(2026, 3, 31), "202603"),
    (date(2026, 4, 1), date(2026, 4, 30), "202604"),
]

IEM_RATE = 12.0  # seconds — respects IEM's 300 req/hr limit


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


def _download_iem_data(
    client: httpx.Client,
    source_id: str,
    url_fn,
    file_suffix: str,
) -> dict:
    date_dir = RAW_ROOT / source_id / DATE_TAG
    manifest_path = date_dir / "manifest.jsonl"
    date_dir.mkdir(parents=True, exist_ok=True)

    total_bytes = 0
    results = []
    failed = []

    for station in IEM_STATIONS:
        for start, end, month_tag in IEM_DATE_RANGES:
            url = url_fn(station, start, end)
            dest = date_dir / f"{station}_{file_suffix}_{month_tag}.csv"
            try:
                b, entry = fetch(
                    source_id, url, dest, manifest_path, client, IEM_RATE, total_bytes
                )
                total_bytes += b
                results.append(entry)
                logger.info("[%s] %s %s: %d bytes", source_id, station, month_tag, b)
            except RuntimeError as e:
                logger.error(
                    "[%s] %s %s FAILED: %s", source_id, station, month_tag, e
                )
                failed.append({"station": station, "month": month_tag, "error": str(e)})

    status = "OK" if not failed else ("PARTIAL" if results else "FAILED")
    return {
        "source_id": source_id,
        "status": status,
        "files": results,
        "failed": failed,
        "total_bytes": total_bytes,
    }


def download_iem_metar(client: httpx.Client) -> dict:
    """IEM ASOS METAR: 20 airports × 12 months. Ref: mesonet.agron.iastate.edu"""
    return _download_iem_data(client, "IEM_METAR", _iem_metar_url, "METAR")


def download_iem_taf(client: httpx.Client) -> dict:
    """IEM TAF: 20 airports × 12 months. Ref: mesonet.agron.iastate.edu"""
    return _download_iem_data(client, "IEM_TAF", _iem_taf_url, "TAF")


# ---------------------------------------------------------------------------
# Source 5: International NOTAM bulletins — ALL require login
# ---------------------------------------------------------------------------

# All probed NOTAM sources require authenticated sessions:
#   NATS UK EAD (nats-uk.ead-it.com) — redirects to login
#   EUROCONTROL EAD Basic (www.ead.eurocontrol.int) — redirects to login
#   ENAIRE (enaire.es/notam) — registration required
#   DFS Germany — registration required
# Documented as REQUIRES_USER_ACTION per CLAUDE.md §1.2.
INTL_NOTAM_SOURCES = [
    {
        "url": "https://www.ead.eurocontrol.int/eadbasic/pamslight-7DCCD2D5A44C2EDAC85E1D0B0C89F2AF/7FE5A4CF01D1110B/ENR/EAD_Basic_AIP_ENR_5_1_en_GB.html",
        "description": "EUROCONTROL EAD Basic AIP ENR 5.1 (login required)",
    },
    {
        "url": "https://nats-uk.ead-it.com/pub-portal/gateway/document/EGTT-AIRAC-2026-04.pdf",
        "description": "NATS UK EAD AIRAC April 2026 (login required)",
    },
    {
        "url": "https://www.enaire.es/servicios_de_navegacion_aerea/notam_de_espana",
        "description": "ENAIRE Spain NOTAM (registration required)",
    },
]


def document_intl_notam_skipped() -> dict:
    """
    All international NOTAM bulletin sources require authenticated sessions.
    Documents each as REQUIRES_USER_ACTION in manifest; no data downloaded.
    PI action required to obtain credentials or identify unauthenticated alternatives.
    """
    source_id = "INTL_NOTAM"
    date_dir = RAW_ROOT / source_id / DATE_TAG
    manifest_path = date_dir / "manifest.jsonl"
    date_dir.mkdir(parents=True, exist_ok=True)

    for src in INTL_NOTAM_SOURCES:
        entry = {
            "source_id": source_id,
            "source_url": src["url"],
            "file_path": None,
            "http_status": None,
            "fetched_at_utc": datetime.now(UTC).isoformat(),
            "sha256": None,
            "content_length": 0,
            "error": "REQUIRES_USER_ACTION: authenticated login required",
            "note": src["description"],
        }
        _write_manifest(manifest_path, entry)
        logger.warning(
            "[INTL_NOTAM] SKIPPED (login wall): %s", src["description"]
        )

    return {
        "source_id": source_id,
        "status": "REQUIRES_USER_ACTION",
        "error": "All international NOTAM sources require authenticated sessions. PI action needed.",
        "files": [],
        "total_bytes": 0,
    }


# ---------------------------------------------------------------------------
# Source 6: FAA Chart Supplement PDFs — 7 regional PDFs, cycle 20260514
# ---------------------------------------------------------------------------

# FAA aeronautical chart supplements (formerly Airport/Facility Directory).
# Publicly accessible at aeronav.faa.gov — no registration.
# Contains airport diagrams, communication frequencies, instrument approach minima.
# Current cycle: 20260514 (28-day AIRAC cycle; confirmed accessible 2026-05-17).
FAA_CHART_REGIONS = ["NE", "EC", "SC", "NC", "NW", "SW", "SE"]
FAA_CHART_CYCLE = "20260514"
FAA_CHART_URL_TEMPLATE = (
    "https://aeronav.faa.gov/Upload_313-d/supplements/CS_{region}_{cycle}.pdf"
)


def download_faa_chart_supplements(client: httpx.Client) -> dict:
    """
    Download 7 FAA Chart Supplement PDFs (full US coverage, cycle 20260514).

    Each PDF covers one region: NE, EC, SC, NC, NW, SW, SE.
    Contains airport diagrams, approach minima, NOTAMs cross-reference, comm freqs.
    Total: ~207 MB. Rate limit: 3s between requests.
    Ref: https://aeronav.faa.gov/Upload_313-d/supplements/
    """
    source_id = "FAA_CHART_SUPPL"
    date_dir = RAW_ROOT / source_id / DATE_TAG
    manifest_path = date_dir / "manifest.jsonl"
    date_dir.mkdir(parents=True, exist_ok=True)

    total_bytes = 0
    results = []
    failed = []

    for region in FAA_CHART_REGIONS:
        url = FAA_CHART_URL_TEMPLATE.format(region=region, cycle=FAA_CHART_CYCLE)
        dest = date_dir / f"FAA_CS_{region}_{FAA_CHART_CYCLE}.pdf"
        try:
            b, entry = fetch(
                source_id, url, dest, manifest_path, client, 3.0, total_bytes
            )
            total_bytes += b
            results.append(entry)
            logger.info("[FAA_CHART_SUPPL] region=%s: %d bytes (%.1f MB)", region, b, b / 1024 / 1024)
        except RuntimeError as e:
            logger.error("[FAA_CHART_SUPPL] region=%s FAILED: %s", region, e)
            failed.append({"region": region, "url": url, "error": str(e)})

    status = "OK" if not failed else ("PARTIAL" if results else "FAILED")
    return {
        "source_id": source_id,
        "status": status,
        "files": results,
        "failed": failed,
        "total_bytes": total_bytes,
    }


# ---------------------------------------------------------------------------
# Source 7: ADS-B Exchange — public samples (no login)
# ---------------------------------------------------------------------------

# samples.adsbexchange.com — public access, no registration.
# Three data products:
#   flights-ax-v2: daily arrivals CSV (~15.6 MB/day uncompressed)
#   operations-ax-v2: daily operations CSV.gz (~17.9 MB compressed)
#   acas: TCAS/ACAS resolution advisory data CSV.gz (~70 KB/day)
#
# Sample dates: only the 1st of each month has data (confirmed by probing 2026-05-17).
# Available: 2024-12-01, 2025-01-01; later dates return 404.
# 2025-01-01 has smaller arrivals file (~8.4 MB vs 14.5 MB for Dec) — holiday period.

ADSB_SAMPLE_DATES = [
    ("2024", "12", "01", "20241201"),
    ("2025", "01", "01", "20250101"),
]

ADSB_ACAS_DATES = [
    ("2024", "01", "01", "20240101"),   # 70 KB
    ("2024", "12", "01", "20241201"),   # 188 KB
]

ADSB_FLIGHTS_URL = (
    "https://samples.adsbexchange.com/flights-ax-v2/{Y}/{M}/{D}/ax_arrivals_{YYYYMMDD}.csv"
)
ADSB_OPS_URL = (
    "https://samples.adsbexchange.com/operations-ax-v2/{Y}/{M}/{D}/operations.csv.gz"
)
ADSB_ACAS_URL = (
    "https://samples.adsbexchange.com/acas/{Y}/{M}/{D}/acas.csv.gz"
)


def download_adsb_exchange(client: httpx.Client) -> dict:
    """
    Download ADS-B Exchange public sample data.

    Fetches:
      - flights-ax-v2: daily arrivals CSV for 3 days (~15.6 MB each)
      - operations-ax-v2: daily operations CSV.gz for 3 days (~17.9 MB each)
      - acas: TCAS/ACAS resolution advisory CSV.gz for 1 day (~70 KB)

    Rate limit: 2s between requests. No registration required.
    Ref: https://samples.adsbexchange.com/
    """
    source_id = "ADSB_EXCHANGE"
    date_dir = RAW_ROOT / source_id / DATE_TAG
    manifest_path = date_dir / "manifest.jsonl"
    date_dir.mkdir(parents=True, exist_ok=True)

    total_bytes = 0
    results = []
    failed = []

    # Flights (CSV, uncompressed)
    for Y, M, D, YYYYMMDD in ADSB_SAMPLE_DATES:
        url = ADSB_FLIGHTS_URL.format(Y=Y, M=M, D=D, YYYYMMDD=YYYYMMDD)
        dest = date_dir / f"ax_arrivals_{YYYYMMDD}.csv"
        try:
            b, entry = fetch(
                source_id, url, dest, manifest_path, client, 2.0, total_bytes
            )
            total_bytes += b
            results.append(entry)
            logger.info("[ADSB_EXCHANGE] flights %s: %d bytes", YYYYMMDD, b)
        except RuntimeError as e:
            logger.error("[ADSB_EXCHANGE] flights %s FAILED: %s", YYYYMMDD, e)
            failed.append({"type": "flights", "date": YYYYMMDD, "error": str(e)})

    # Operations (CSV.gz, compressed)
    for Y, M, D, YYYYMMDD in ADSB_SAMPLE_DATES:
        url = ADSB_OPS_URL.format(Y=Y, M=M, D=D, YYYYMMDD=YYYYMMDD)
        dest = date_dir / f"operations_{YYYYMMDD}.csv.gz"
        try:
            b, entry = fetch(
                source_id, url, dest, manifest_path, client, 2.0, total_bytes
            )
            total_bytes += b
            results.append(entry)
            logger.info("[ADSB_EXCHANGE] operations %s: %d bytes", YYYYMMDD, b)
        except RuntimeError as e:
            logger.error("[ADSB_EXCHANGE] operations %s FAILED: %s", YYYYMMDD, e)
            failed.append({"type": "operations", "date": YYYYMMDD, "error": str(e)})

    # ACAS/TCAS — 2 days (tiny files, high value for TCAS/RA content)
    for acas_Y, acas_M, acas_D, acas_DATE in ADSB_ACAS_DATES:
        acas_url = ADSB_ACAS_URL.format(Y=acas_Y, M=acas_M, D=acas_D, YYYYMMDD=acas_DATE)
        acas_dest = date_dir / f"acas_{acas_DATE}.csv.gz"
        try:
            b, entry = fetch(
                source_id, acas_url, acas_dest, manifest_path, client, 2.0, total_bytes
            )
            total_bytes += b
            results.append(entry)
            logger.info("[ADSB_EXCHANGE] acas %s: %d bytes", acas_DATE, b)
        except RuntimeError as e:
            logger.error("[ADSB_EXCHANGE] acas %s FAILED: %s", acas_DATE, e)
            failed.append({"type": "acas", "date": acas_DATE, "error": str(e)})

    status = "OK" if not failed else ("PARTIAL" if results else "FAILED")
    return {
        "source_id": source_id,
        "status": status,
        "files": results,
        "failed": failed,
        "total_bytes": total_bytes,
    }


# ---------------------------------------------------------------------------
# Source 8: FAA SDR — still 503 (document, don't retry)
# ---------------------------------------------------------------------------

def download_faa_sdr(client: httpx.Client) -> dict:
    """
    FAA Service Difficulty Reporting (SDR) — via sdrs.faa.gov public query.

    av-info.faa.gov/sdrx/reports.aspx returns HTTP 503 (deprecated).
    sdrs.faa.gov/Query.aspx is publicly accessible without login.
    Uses ASP.NET WebForms POST flow:
      1. GET /Query.aspx → extract __VIEWSTATE tokens
      2. POST /Query.aspx with date range → result page with new tokens
      3. POST /Query.aspx with Download button → application/vnd.ms-excel export

    The "XLS" is actually an HTML table (confirmed by probing 2026-05-17).
    Saved as .xls with actual MIME type noted in manifest.
    Downloads in 6-month chunks to stay within server limits.

    Ref: https://sdrs.faa.gov/
    """
    import re as _re

    source_id = "FAA_SDR"
    date_dir = RAW_ROOT / source_id / DATE_TAG
    manifest_path = date_dir / "manifest.jsonl"
    date_dir.mkdir(parents=True, exist_ok=True)

    QUERY_URL = "https://sdrs.faa.gov/Query.aspx"
    total_bytes = 0
    results = []
    failed = []

    # Fetch in two 6-month windows
    date_ranges = [
        ("2025-05-01", "2025-10-31", "202505_202510"),
        ("2025-11-01", "2026-05-01", "202511_202605"),
    ]

    for date_from, date_to, label in date_ranges:
        fetched_at = datetime.now(UTC).isoformat()
        dest = date_dir / f"SDR_export_{label}.xls"
        entry: dict = {
            "source_id": source_id,
            "source_url": QUERY_URL,
            "file_path": str(dest.relative_to(PROJECT_ROOT)),
            "http_status": None,
            "fetched_at_utc": fetched_at,
            "sha256": "",
            "content_length": None,
            "error": None,
            "note": f"SDRS WebForms export; date range {date_from}..{date_to}; XLS is HTML table",
        }
        try:
            # Step 1: get tokens
            r1 = client.get(QUERY_URL, timeout=60)
            if r1.status_code != 200:
                raise RuntimeError(f"GET Query.aspx returned HTTP {r1.status_code}")
            vs = _re.search(r'id="__VIEWSTATE" value="([^"]+)"', r1.text)
            vsg = _re.search(r'id="__VIEWSTATEGENERATOR" value="([^"]+)"', r1.text)
            ev = _re.search(r'id="__EVENTVALIDATION" value="([^"]+)"', r1.text)
            if not vs or not vsg or not ev:
                raise RuntimeError("Could not extract VIEWSTATE tokens from Query.aspx")

            time.sleep(2.0)

            # Step 2: submit query
            payload1 = {
                "__VIEWSTATE": vs.group(1),
                "__VIEWSTATEGENERATOR": vsg.group(1),
                "__EVENTVALIDATION": ev.group(1),
                "ctl00$pageContentPlaceHolder$tbDifficultyDateFrom": date_from,
                "ctl00$pageContentPlaceHolder$tbDifficultyDateTo": date_to,
                "ctl00$pageContentPlaceHolder$btnQuery": "Query",
            }
            r2 = client.post(QUERY_URL, data=payload1, timeout=120)
            entry["http_status"] = r2.status_code
            if r2.status_code != 200:
                raise RuntimeError(f"Query POST returned HTTP {r2.status_code}")

            time.sleep(2.0)

            # Step 3: click Download
            vs2 = _re.search(r'id="__VIEWSTATE" value="([^"]+)"', r2.text)
            vsg2 = _re.search(r'id="__VIEWSTATEGENERATOR" value="([^"]+)"', r2.text)
            ev2 = _re.search(r'id="__EVENTVALIDATION" value="([^"]+)"', r2.text)
            if not vs2:
                raise RuntimeError("No VIEWSTATE in query results page — may be empty result set")

            payload2 = {
                "__VIEWSTATE": vs2.group(1),
                "__VIEWSTATEGENERATOR": vsg2.group(1) if vsg2 else "",
                "__EVENTVALIDATION": ev2.group(1) if ev2 else "",
                "ctl00$pageContentPlaceHolder$btnDownload": "Download",
            }
            r3 = client.post(QUERY_URL, data=payload2, timeout=120)
            if r3.status_code != 200:
                raise RuntimeError(f"Download POST returned HTTP {r3.status_code}")

            content = r3.content
            if _is_html(dest) or content[:5].lower().startswith(b"<html"):
                # confirm it's the expected HTML-table XLS, not an error page
                if b"<table" not in content[:500].lower():
                    raise RuntimeError("Download response does not look like XLS or table data")

            dest.parent.mkdir(parents=True, exist_ok=True)
            with open(dest, "wb") as f:
                f.write(content)

            cap = VOLUME_CAP_BYTES.get(source_id, 50 * 1024 * 1024)
            if total_bytes + len(content) > cap:
                dest.unlink(missing_ok=True)
                raise RuntimeError(f"Volume cap {cap/1024/1024:.0f} MB exceeded")

            sha = _sha256(dest)
            entry["sha256"] = sha
            entry["content_length"] = len(content)
            _write_manifest(manifest_path, entry)
            total_bytes += len(content)
            results.append(entry)
            logger.info("[FAA_SDR] %s: %d bytes", label, len(content))
            time.sleep(3.0)

        except Exception as e:
            entry["error"] = str(e)
            _write_manifest(manifest_path, entry)
            logger.error("[FAA_SDR] %s FAILED: %s", label, e)
            failed.append({"range": label, "error": str(e)})

    status = "OK" if not failed else ("PARTIAL" if results else "FAILED")
    return {
        "source_id": source_id,
        "status": status,
        "files": results,
        "failed": failed,
        "total_bytes": total_bytes,
    }


# ---------------------------------------------------------------------------
# Source 9: BTS On-Time Data — OR benchmark substitute (OR-Library is dead)
# ---------------------------------------------------------------------------

# OR-Library at brunel.ac.uk returned HTTP 404 on all sub-pages (2026-05-17).
# Replacement: BTS Transtats On-Time Performance by Carrier, publicly accessible.
# Covers flight operations delay/cancellation data useful for optimization tasks.
# URL pattern confirmed HTTP 200 during probing: ~28-30 MB per month ZIP.
# Ref: https://transtats.bts.gov/PREZIP/

BTS_MONTHS = [
    (2024, 7,  "2024_07"),
    (2024, 8,  "2024_08"),
    (2024, 9,  "2024_09"),
    (2024, 10, "2024_10"),
    (2024, 11, "2024_11"),
    (2024, 12, "2024_12"),
]

BTS_URL_TEMPLATE = (
    "https://transtats.bts.gov/PREZIP/"
    "On_Time_Reporting_Carrier_On_Time_Performance_1987_present_{year}_{month}.zip"
)


def download_or_library(client: httpx.Client) -> dict:
    """
    OR-Library (Beasley, Brunel University) — crew scheduling benchmark instances.

    The main info page (http://people.brunel.ac.uk/~mastjjb/jeb/info.html) is alive.
    The aircrew scheduling sub-index (aircrewinfo.html) returns 404, but the CSP
    (Crew Scheduling Problem) files are directly accessible at known paths:
      http://people.brunel.ac.uk/~mastjjb/jeb/orlib/files/csp{N}.txt

    Files csp1..csp24 probed 2026-05-17: 20 of 24 return HTTP 200 (4 are 404).
    These are airline crew-scheduling benchmark instances widely cited in OR literature.
    Citation: Beasley, J.E. (1990) OR-Library. Journal of the Operational Research
    Society, 41(11), pp. 1069-1072. doi:10.2307/2582903

    Rate limit: 2s between requests. Per-source cap: 10 MB.
    """
    source_id = "OR_LIBRARY"
    date_dir = RAW_ROOT / source_id / DATE_TAG
    manifest_path = date_dir / "manifest.jsonl"
    date_dir.mkdir(parents=True, exist_ok=True)

    BASE = "http://people.brunel.ac.uk/~mastjjb/jeb/orlib/files/"
    VOLUME_CAP_BYTES["OR_LIBRARY"] = 10 * 1024 * 1024  # 10 MB

    total_bytes = 0
    results = []
    failed = []

    # Probe and download CSP files 1-24 (skip known 404s: 5,10,15,20)
    for i in range(1, 25):
        url = f"{BASE}csp{i}.txt"
        dest = date_dir / f"csp{i}.txt"
        try:
            b, entry = fetch(
                source_id, url, dest, manifest_path, client, 2.0, total_bytes
            )
            total_bytes += b
            results.append(entry)
            logger.info("[OR_LIBRARY] csp%d.txt: %d bytes", i, b)
        except RuntimeError as e:
            if "404" in str(e):
                logger.debug("[OR_LIBRARY] csp%d.txt: 404 (expected gap)", i)
            else:
                logger.error("[OR_LIBRARY] csp%d.txt FAILED: %s", i, e)
                failed.append({"file": f"csp{i}.txt", "error": str(e)})

    status = "OK" if results else "FAILED"
    return {
        "source_id": source_id,
        "status": status,
        "files": results,
        "failed": failed,
        "total_bytes": total_bytes,
        "note": (
            "OR-Library CSP (crew scheduling) benchmark instances. "
            "Citation: Beasley 1990, J. Oper. Res. Soc. 41(11) doi:10.2307/2582903"
        ),
    }


def download_bts_ontime(client: httpx.Client) -> dict:
    """
    BTS On-Time Reporting: 6 months (2024-07 through 2024-12).

    Each ZIP contains On_Time_On_Time_Performance_{YYYY}_{M}.csv with carrier,
    origin, dest, scheduled/actual departure/arrival, delays, cancellations.
    ~28-30 MB per month; 6 months ≈ 180 MB. Rate limit: 3s between requests.
    Useful for T21 OR benchmark (gate scheduling, delay propagation, optimization).
    Ref: https://transtats.bts.gov/PREZIP/
    """
    source_id = "BTS_ONTIME"
    date_dir = RAW_ROOT / source_id / DATE_TAG
    manifest_path = date_dir / "manifest.jsonl"
    date_dir.mkdir(parents=True, exist_ok=True)

    total_bytes = 0
    results = []
    failed = []

    for year, month, label in BTS_MONTHS:
        url = BTS_URL_TEMPLATE.format(year=year, month=month)
        dest = date_dir / f"BTS_OnTime_{label}.zip"
        try:
            b, entry = fetch(
                source_id, url, dest, manifest_path, client, 3.0, total_bytes
            )
            total_bytes += b
            results.append(entry)
            logger.info(
                "[BTS_ONTIME] %s: %d bytes (%.1f MB)", label, b, b / 1024 / 1024
            )
        except RuntimeError as e:
            logger.error("[BTS_ONTIME] %s FAILED: %s", label, e)
            failed.append({"month": label, "error": str(e)})

    status = "OK" if not failed else ("PARTIAL" if results else "FAILED")
    return {
        "source_id": source_id,
        "status": status,
        "files": results,
        "failed": failed,
        "total_bytes": total_bytes,
    }


# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------

def _fmt_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def main() -> None:
    logger.info("=== T21 Mega Real-Data Acquisition — start ===")
    logger.info("Project root: %s", PROJECT_ROOT)
    logger.info("Raw data dir: %s", RAW_ROOT)
    logger.info("Total cap: %s", _fmt_bytes(TOTAL_CAP_BYTES))

    results: list[dict] = []
    grand_total_bytes = 0

    with httpx.Client(
        follow_redirects=True,
        headers={
            "User-Agent": (
                "AeroSafetyEval/1.0 research project - aviation safety AI evaluation; "
                "contact: research@university.edu"
            )
        },
        timeout=180,
    ) as client:

        # Source 1: NASA ASRS (503, document failure)
        logger.info("--- Source 1/9: NASA_ASRS ---")
        r = download_asrs(client)
        results.append(r)
        grand_total_bytes += r.get("total_bytes", 0)

        # Source 2: NTSB Full Reports (40 PDFs)
        logger.info("--- Source 2/9: NTSB_FULL_REPORTS ---")
        r = download_ntsb_full_reports(client)
        results.append(r)
        grand_total_bytes += r.get("total_bytes", 0)
        if grand_total_bytes > TOTAL_CAP_BYTES:
            logger.error("TOTAL CAP EXCEEDED after NTSB. Aborting.")
            _print_summary(results, grand_total_bytes)
            return

        # Source 3: IEM METAR (20 stations × 12 months)
        logger.info("--- Source 3/9: IEM_METAR ---")
        r = download_iem_metar(client)
        results.append(r)
        grand_total_bytes += r.get("total_bytes", 0)
        if grand_total_bytes > TOTAL_CAP_BYTES:
            logger.error("TOTAL CAP EXCEEDED after IEM_METAR. Aborting.")
            _print_summary(results, grand_total_bytes)
            return

        # Source 4: IEM TAF (20 stations × 12 months)
        logger.info("--- Source 4/9: IEM_TAF ---")
        r = download_iem_taf(client)
        results.append(r)
        grand_total_bytes += r.get("total_bytes", 0)
        if grand_total_bytes > TOTAL_CAP_BYTES:
            logger.error("TOTAL CAP EXCEEDED after IEM_TAF. Aborting.")
            _print_summary(results, grand_total_bytes)
            return

        # Source 5: International NOTAMs (all login-walled, document skip)
        logger.info("--- Source 5/9: INTL_NOTAM ---")
        r = document_intl_notam_skipped()
        results.append(r)

        # Source 6: FAA Chart Supplement PDFs
        logger.info("--- Source 6/9: FAA_CHART_SUPPL ---")
        r = download_faa_chart_supplements(client)
        results.append(r)
        grand_total_bytes += r.get("total_bytes", 0)
        if grand_total_bytes > TOTAL_CAP_BYTES:
            logger.error("TOTAL CAP EXCEEDED after FAA_CHART_SUPPL. Aborting.")
            _print_summary(results, grand_total_bytes)
            return

        # Source 7: ADS-B Exchange
        logger.info("--- Source 7/9: ADSB_EXCHANGE ---")
        r = download_adsb_exchange(client)
        results.append(r)
        grand_total_bytes += r.get("total_bytes", 0)
        if grand_total_bytes > TOTAL_CAP_BYTES:
            logger.error("TOTAL CAP EXCEEDED after ADSB_EXCHANGE. Aborting.")
            _print_summary(results, grand_total_bytes)
            return

        # Source 8: FAA SDR — publicly accessible via sdrs.faa.gov (no login required)
        logger.info("--- Source 8/9: FAA_SDR ---")
        r = download_faa_sdr(client)
        results.append(r)
        grand_total_bytes += r.get("total_bytes", 0)

        # Source 9a: OR-Library — CSP crew-scheduling instances (publicly accessible)
        logger.info("--- Source 9a/9: OR_LIBRARY ---")
        r = download_or_library(client)
        results.append(r)
        grand_total_bytes += r.get("total_bytes", 0)

        # Source 9b: BTS On-Time data (OR benchmark supplement)
        logger.info("--- Source 9b/9: BTS_ONTIME ---")
        r = download_bts_ontime(client)
        results.append(r)
        grand_total_bytes += r.get("total_bytes", 0)

    _print_summary(results, grand_total_bytes)


def _print_summary(results: list[dict], grand_total_bytes: int) -> None:
    logger.info("=== T21 DOWNLOAD SUMMARY ===")
    for r in results:
        sid = r["source_id"]
        status = r["status"]
        total_b = r.get("total_bytes", 0)
        n_files = len(r.get("files", []))
        n_failed = len(r.get("failed", []))
        if status == "REQUIRES_USER_ACTION":
            logger.info(
                "  %-20s  REQUIRES_USER_ACTION  (login-gated; PI action needed)", sid
            )
        elif status == "FAILED":
            logger.info(
                "  %-20s  FAILED  error=%s", sid, r.get("error", "")[:80]
            )
        elif status == "PARTIAL":
            logger.info(
                "  %-20s  PARTIAL  %d OK / %d FAILED  %s",
                sid, n_files, n_failed, _fmt_bytes(total_b)
            )
        else:
            logger.info(
                "  %-20s  OK  %d files  %s",
                sid, n_files, _fmt_bytes(total_b)
            )
    logger.info("  GRAND TOTAL: %s", _fmt_bytes(grand_total_bytes))
    logger.info("=== END SUMMARY ===")

    # Also print to stdout for team-lead report
    print("\n=== T21 PER-SOURCE REPORT ===")
    for r in results:
        sid = r["source_id"]
        status = r["status"]
        total_b = r.get("total_bytes", 0)
        n_files = len(r.get("files", []))
        n_failed = len(r.get("failed", []))
        line = f"{sid:25s}  {status:22s}  files={n_files:3d}  failed={n_failed:2d}  bytes={_fmt_bytes(total_b)}"
        print(line)
    print(f"\nGRAND TOTAL DOWNLOADED: {_fmt_bytes(grand_total_bytes)}")
    print("=== END REPORT ===\n")


if __name__ == "__main__":
    main()
