"""
Downloader: METAR and TAF archives via Iowa State Mesonet (source_id=IEM_METAR)

DO NOT EXECUTE without team-lead approval (task brief hard rule 1).

Single source for both METAR and TAF data — the Iowa Environmental Mesonet
(IEM) at Iowa State University provides a globally accessible mirror of
NOAA/NWS METAR and TAF data with no API key and no residency restriction.

DESIGN NOTE: NOAA Aviation Weather Center API (aviationweather.gov) was
removed from the critical path (residency_restriction=us_resident). IEM
provides the same underlying NOAA/NWS data. See source_registry.yaml
NOAA_AWC_API (off critical path).

Rate limits:
  IEM: No more than 300 requests/hour per IP.
  Reference: https://mesonet.agron.iastate.edu/info/tos.phtml
  -> Use 12-second inter-request delay (= ~300 req/hr max usage).

OGIMET (secondary): 5-second minimum between requests.

License: Public domain (NOAA/NWS data); IEM TOS apply.
Commercial use: OK.
Citation:
  Iowa Environmental Mesonet (IEM), Iowa State University.
  ASOS-METAR Archive.
  Available at: https://mesonet.agron.iastate.edu/request/download.phtml
"""

from __future__ import annotations

import logging
import sys
from datetime import date

from aerosafety.data.downloaders._base import (
    RAW_DATA_DIR,
    fetch_url,
)

logger = logging.getLogger(__name__)

SOURCE_ID = "IEM_METAR"
OUTPUT_DIR = RAW_DATA_DIR / SOURCE_ID
RATE_LIMIT_SECONDS = 12.0  # 300 req/hr limit -> 12s/request

# IEM ASOS download service (METAR).
# Ref: https://mesonet.agron.iastate.edu/request/download.phtml
IEM_ASOS_URL = "https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py"

# IEM TAF download service.
# report_type=6 selects TAF records within the ASOS feed.
# For a dedicated TAF archive, IEM also provides:
IEM_TAF_URL = "https://mesonet.agron.iastate.edu/cgi-bin/request/taf.py"

# OGIMET secondary source — used only if IEM unavailable for a station.
OGIMET_SOURCE_ID = "OGIMET_METAR"
OGIMET_METAR_URL = "https://www.ogimet.com/cgi-bin/getmetar.py"
OGIMET_RATE_LIMIT_SECONDS = 5.0

# Priority stations covering high-traffic airports globally.
# Mix of US, European, and Asian airports to support diverse scenario construction.
PRIORITY_STATIONS = [
    # US
    "KLAX", "KJFK", "KORD", "KATL", "KDFW",
    "KSFO", "KMIA", "KDEN", "KBOS", "KSEA",
    "KIAD", "KPHX", "KEWR", "KDTW", "KLAS",
    # Europe
    "EGLL",  # London Heathrow
    "LFPG",  # Paris CDG
    "EDDF",  # Frankfurt
    "EHAM",  # Amsterdam Schiphol
    "LEMD",  # Madrid Barajas
    # Asia-Pacific
    "RJTT",  # Tokyo Haneda
    "VHHH",  # Hong Kong
    "YSSY",  # Sydney
]


def download_metar_station_range(
    station: str,
    start_date: date,
    end_date: date,
    *,
    dry_run: bool = True,
) -> None:
    """
    Download METAR observations for one station over a date range via IEM.

    Args:
        station:    ICAO station code (e.g., 'KLAX').
        start_date: First date (inclusive).
        end_date:   Last date (inclusive).
        dry_run:    If True (default), only log.
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
    dest = OUTPUT_DIR / "metar" / f"{station}_{start_date}_{end_date}.csv"

    if dry_run:
        logger.info(
            "DRY RUN — METAR source_id=%s station=%s url=%s -> %s",
            SOURCE_ID, station, url, dest,
        )
        return

    fetch_url(SOURCE_ID, url, dest, rate_limit_seconds=RATE_LIMIT_SECONDS)


def download_taf_station_range(
    station: str,
    start_date: date,
    end_date: date,
    *,
    dry_run: bool = True,
) -> None:
    """
    Download TAF records for one station over a date range via IEM TAF service.

    Args:
        station:    ICAO station code (e.g., 'KJFK').
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
        "year1": start_date.year,
        "month1": start_date.month,
        "day1": start_date.day,
        "year2": end_date.year,
        "month2": end_date.month,
        "day2": end_date.day,
        "tz": "UTC",
        "format": "csv",
    }
    param_str = "&".join(f"{k}={v}" for k, v in params.items())
    url = f"{IEM_TAF_URL}?{param_str}"
    dest = OUTPUT_DIR / "taf" / f"{station}_{start_date}_{end_date}.csv"

    if dry_run:
        logger.info(
            "DRY RUN — TAF source_id=%s station=%s url=%s -> %s",
            SOURCE_ID, station, url, dest,
        )
        return

    fetch_url(SOURCE_ID, url, dest, rate_limit_seconds=RATE_LIMIT_SECONDS)


def download_metar_ogimet_fallback(
    station: str,
    year: int,
    month: int,
    *,
    dry_run: bool = True,
) -> None:
    """
    Fallback: fetch METAR from OGIMET for stations not available in IEM.

    Use only when IEM returns no data for a non-US station.

    Args:
        station: ICAO station code (e.g., 'VHHH').
        year:    Year (e.g., 2023).
        month:   Month 1–12.
        dry_run: If True, only log.
    """
    if not dry_run:
        raise RuntimeError(
            "dry_run=False requires team-lead approval. See task brief hard rule 1."
        )

    params = {
        "icao": station,
        "ano": year,
        "mes": f"{month:02d}",
        "day": "01",
        "hora": "00",
        "min": "00",
        "type": "SA",
        "fmt": "txt",
    }
    param_str = "&".join(f"{k}={v}" for k, v in params.items())
    url = f"{OGIMET_METAR_URL}?{param_str}"
    dest = OUTPUT_DIR / "metar_ogimet_fallback" / f"{station}_{year}_{month:02d}.txt"

    if dry_run:
        logger.info(
            "DRY RUN — OGIMET fallback source_id=%s station=%s url=%s -> %s",
            OGIMET_SOURCE_ID, station, url, dest,
        )
        return

    fetch_url(
        OGIMET_SOURCE_ID, url, dest, rate_limit_seconds=OGIMET_RATE_LIMIT_SECONDS
    )


def download_all_priority_stations(
    start_date: date,
    end_date: date,
    *,
    include_taf: bool = True,
    dry_run: bool = True,
) -> None:
    """Download METAR (and optionally TAF) for all priority stations."""
    for station in PRIORITY_STATIONS:
        download_metar_station_range(station, start_date, end_date, dry_run=dry_run)
        if include_taf:
            download_taf_station_range(station, start_date, end_date, dry_run=dry_run)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    download_all_priority_stations(
        date(2023, 1, 1), date(2023, 12, 31), dry_run=True
    )
    logger.info(
        "Dry run complete. Awaiting team-lead approval.\n"
        "Source: IEM (Iowa State Mesonet) — no key, no residency restriction.\n"
        "NOAA AWC API (aviationweather.gov) is off critical path per PI constraint."
    )
