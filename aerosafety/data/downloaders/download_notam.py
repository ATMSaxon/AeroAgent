"""
Downloader: FAA NOTAM API (source_id=FAA_NOTAM)

DO NOT EXECUTE without team-lead approval (task brief hard rule 1).

Requires: FAA API key from https://api.faa.gov (free registration).
Set environment variable FAA_NOTAM_API_KEY before running.

Rate limits:
  FAA API: https://api.faa.gov/terms-and-conditions
  Default: 100 requests/minute per API key.
  -> Use 0.7-second inter-request delay.

License: Public domain (U.S. Government work, 17 U.S.C. §105).
Commercial use: OK.
Citation:
  Federal Aviation Administration (FAA).
  NOTAM Management System / NOTAM Search.
  API: https://api.faa.gov/notamapi/
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from aerosafety.data.downloaders._base import (
    RAW_DATA_DIR,
    fetch_json_api,
    _write_manifest_entry,
)

logger = logging.getLogger(__name__)

SOURCE_ID = "FAA_NOTAM"
OUTPUT_DIR = RAW_DATA_DIR / SOURCE_ID
RATE_LIMIT_SECONDS = 0.7  # ~85 req/min, below 100 limit

# FAA NOTAM API base URL.
# Ref: https://api.faa.gov/notamapi/
FAA_NOTAM_API_BASE = "https://api.faa.gov/notamapi/v1/notams"

# Priority airports for Task Family 4 (NOTAM compliance).
PRIORITY_AIRPORTS = [
    "KLAX", "KJFK", "KORD", "KATL", "KDFW",
    "KSFO", "KMIA", "KDEN", "KBOS", "KSEA",
    "KIAD", "KPHX", "KEWR", "KDTW", "KLAS",
]


def _get_api_key() -> str:
    key = os.environ.get("FAA_NOTAM_API_KEY")
    if not key:
        raise EnvironmentError(
            "FAA_NOTAM_API_KEY environment variable is not set. "
            "Register at https://api.faa.gov to obtain a free API key. "
            "This is a requires_user_action source."
        )
    return key


def download_notams_for_airport(
    icao: str,
    *,
    page_size: int = 100,
    max_pages: int = 10,
    dry_run: bool = True,
) -> None:
    """
    Download NOTAMs for a single airport from the FAA NOTAM API.

    Pages through results up to max_pages * page_size records.

    Args:
        icao:       ICAO airport identifier (e.g., 'KLAX').
        page_size:  Records per API page (max 100).
        max_pages:  Maximum pages to fetch per airport.
        dry_run:    If True, only log.
    """
    if not dry_run:
        raise RuntimeError(
            "dry_run=False requires team-lead approval. See task brief hard rule 1."
        )

    api_key = _get_api_key() if not dry_run else "DRY_RUN_KEY"

    for page_num in range(1, max_pages + 1):
        params = {
            "icaoLocation": icao,
            "pageSize": page_size,
            "pageNum": page_num,
        }
        headers = {"client_id": api_key}

        if dry_run:
            logger.info(
                "DRY RUN — NOTAM source_id=%s airport=%s page=%d url=%s params=%s",
                SOURCE_ID, icao, page_num, FAA_NOTAM_API_BASE, params,
            )
            break  # One log line per airport in dry run.

        body = fetch_json_api(
            SOURCE_ID,
            FAA_NOTAM_API_BASE,
            params,
            headers=headers,
            rate_limit_seconds=RATE_LIMIT_SECONDS,
        )

        items = body.get("items", [])
        if not items:
            logger.info(
                "No more NOTAMs for %s at page %d. Stopping.", icao, page_num
            )
            break

        dest = OUTPUT_DIR / icao / f"page_{page_num:04d}.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "w", encoding="utf-8") as f:
            json.dump(body, f, indent=2)

        # Write manifest entry for the API response.
        _write_manifest_entry({
            "source_id": SOURCE_ID,
            "url_fetched": FAA_NOTAM_API_BASE,
            "access_timestamp": datetime.now(timezone.utc).isoformat(),
            "local_file_path": str(dest),
            "sha256": "",  # Not applicable for API JSON responses directly.
            "http_status_code": 200,
            "content_length_bytes": len(json.dumps(body).encode()),
            "error": None,
            "query_params": params,
        })
        logger.info("Saved NOTAMs for %s page %d to %s", icao, page_num, dest)

        total_count = body.get("totalCount", 0)
        fetched_so_far = page_num * page_size
        if fetched_so_far >= total_count:
            logger.info("All %d NOTAMs fetched for %s.", total_count, icao)
            break


def download_all_priority_airports(*, dry_run: bool = True) -> None:
    """Download NOTAMs for all priority airports."""
    for icao in PRIORITY_AIRPORTS:
        download_notams_for_airport(icao, dry_run=dry_run)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    download_all_priority_airports(dry_run=True)
    logger.info(
        "Dry run complete. Set FAA_NOTAM_API_KEY and get team-lead approval "
        "before executing with dry_run=False."
    )
