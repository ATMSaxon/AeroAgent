"""
Downloader: METAR (IEM) and TAF (AWC) archives
  source_id=NOAA_METAR  — Iowa Environmental Mesonet METAR archive
  source_id=NOAA_TAF    — NOAA Aviation Weather Center TAF API

DO NOT EXECUTE without team-lead approval (task brief hard rule 1).

Rate limits:
  IEM: https://mesonet.agron.iastate.edu/info/tos.phtml
    "No more than 300 requests per hour per IP."
    -> Use 12-second inter-request delay to stay well within limit.
  AWC API: Documented at https://aviationweather.gov/data/api/
    No formal published rate limit; use 2-second delay as courtesy.

License:
  NOAA_METAR: Public domain (NOAA/NWS data), IEM TOS apply.
  NOAA_TAF: Public domain (U.S. Government work).
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from aerosafety.data.downloaders._base import (
    RAW_DATA_DIR,
    MANIFEST_PATH,
    fetch_json_api,
    fetch_url,
    _write_manifest_entry,
)

logger = logging.getLogger(__name__)

METAR_SOURCE_ID = "NOAA_METAR"
TAF_SOURCE_ID = "NOAA_TAF"
METAR_OUTPUT_DIR = RAW_DATA_DIR / METAR_SOURCE_ID
TAF_OUTPUT_DIR = RAW_DATA_DIR / TAF_SOURCE_ID

# IEM ASOS download service endpoint.
# Ref: https://mesonet.agron.iastate.edu/request/download.phtml
IEM_ASOS_URL = "https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py"
IEM_RATE_LIMIT_SECONDS = 12.0  # 300 req/hr -> 12s per request

# AWC TAF API endpoint.
# Ref: https://aviationweather.gov/data/api/
AWC_TAF_URL = "https://aviationweather.gov/api/data/taf"
AWC_RATE_LIMIT_SECONDS = 2.0

# Priority stations for this project (high-traffic airports).
PRIORITY_STATIONS = [
    "KLAX", "KJFK", "KORD", "KATL", "KDFW",
    "KSFO", "KMIA", "KDEN", "KBOS", "KSEA",
    "EGLL",  # London Heathrow
    "RJTT",  # Tokyo Haneda
    "LFPG",  # Paris CDG
    "EDDF",  # Frankfurt
]


def download_metar_station_range(
    station: str,
    start_date: date,
    end_date: date,
    *,
    dry_run: bool = True,
) -> None:
    """
    Download METAR observations for one station over a date range from IEM.

    Args:
        station:    ICAO station code (e.g., 'KLAX').
        start_date: First date (inclusive).
        end_date:   Last date (inclusive).
        dry_run:    If True, only log.
    """
    if not dry_run:
        raise RuntimeError(
            "dry_run=False requires team-lead approval. See task brief hard rule 1."
        )

    params = {
        "station": station,
        "data": "all",
        "year1": start_date.year,
        "month1": start_date.month,
        "day1": start_date.day,
        "year2": end_date.year,
        "month2": end_date.month,
        "day2": end_date.day,
        "tz": "UTC",
        "format": "onlycomma",
        "latlon": "no",
        "direct": "no",
        "report_type": "3",  # METAR (not special obs)
    }
    param_str = "&".join(f"{k}={v}" for k, v in params.items())
    url = f"{IEM_ASOS_URL}?{param_str}"
    dest = METAR_OUTPUT_DIR / f"{station}_{start_date}_{end_date}.csv"

    if dry_run:
        logger.info(
            "DRY RUN — METAR source_id=%s station=%s url=%s -> %s",
            METAR_SOURCE_ID, station, url, dest,
        )
        return

    fetch_url(METAR_SOURCE_ID, url, dest, rate_limit_seconds=IEM_RATE_LIMIT_SECONDS)


def download_taf_station(
    station: str,
    *,
    dry_run: bool = True,
) -> None:
    """
    Fetch current TAF for one station from the AWC API.

    For historical TAF data, use IEM's asos.py with report_type=6 or a
    separate archival source. This fetches the current TAF as a baseline.

    Args:
        station: ICAO station code (e.g., 'KJFK').
        dry_run: If True, only log.
    """
    if not dry_run:
        raise RuntimeError(
            "dry_run=False requires team-lead approval. See task brief hard rule 1."
        )

    params = {
        "ids": station,
        "format": "json",
    }
    if dry_run:
        logger.info(
            "DRY RUN — TAF source_id=%s station=%s url=%s params=%s",
            TAF_SOURCE_ID, station, AWC_TAF_URL, params,
        )
        return

    body = fetch_json_api(
        TAF_SOURCE_ID, AWC_TAF_URL, params, rate_limit_seconds=AWC_RATE_LIMIT_SECONDS
    )
    dest = TAF_OUTPUT_DIR / f"{station}_taf_{datetime.now(timezone.utc).date()}.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(body, f, indent=2)
    logger.info("TAF saved to %s", dest)


def download_all_priority_stations(
    start_date: date,
    end_date: date,
    *,
    dry_run: bool = True,
) -> None:
    """Convenience wrapper: download METAR for all priority stations."""
    for station in PRIORITY_STATIONS:
        download_metar_station_range(
            station, start_date, end_date, dry_run=dry_run
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    from datetime import date
    download_all_priority_stations(
        date(2023, 1, 1), date(2023, 12, 31), dry_run=True
    )
    logger.info("Dry run complete. Awaiting team-lead approval to execute.")
