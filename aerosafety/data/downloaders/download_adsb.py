"""
Downloader: OpenSky Network Historical ADS-B Data (source_id=OPENSKY_ADSB)

DO NOT EXECUTE without team-lead approval (task brief hard rule 1).

Requires: OpenSky Network account + Impala SSH access.
  Register at: https://opensky-network.org/register
  Request Impala access: https://opensky-network.org/data/impala

This script uses the traffic library (https://traffic-viz.github.io/)
which wraps Impala/REST access to OpenSky.

Rate limits:
  Impala: Resource-based; use short time windows and targeted airport queries.
  REST API: 100 flights/call, documented at https://opensky-network.org/apidoc/

License:
  OpenSky Network Data License — academic/research use permitted.
  Commercial use requires separate agreement.
  NOT commercial_use_ok.

Citation:
  Schäfer et al. Bringing Up OpenSky: A Large-scale ADS-B Sensor Network
  for Research. IPSN-14, April 2014.
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from aerosafety.data.downloaders._base import RAW_DATA_DIR

logger = logging.getLogger(__name__)

SOURCE_ID = "OPENSKY_ADSB"
OUTPUT_DIR = RAW_DATA_DIR / SOURCE_ID
RATE_LIMIT_SECONDS = 5.0

# Bounding boxes for terminal areas of priority airports (lat_min, lon_min, lat_max, lon_max).
# These restrict ADS-B queries to within ~50 NM of each airport.
# Values are approximate reference boxes — verify against current airspace charts.
AIRPORT_BBOXES: dict[str, tuple[float, float, float, float]] = {
    "KLAX": (33.2, -118.8, 34.5, -117.5),
    "KJFK": (40.3, -74.5, 41.2, -73.5),
    "KORD": (41.5, -88.1, 42.4, -87.2),
    "KATL": (33.0, -85.0, 34.2, -83.8),
    "EGLL": (50.8, -1.5, 52.1, -0.1),
}


def _check_traffic_available() -> bool:
    try:
        import traffic  # noqa: F401
        return True
    except ImportError:
        return False


def download_adsb_trajectories(
    airport: str,
    start: datetime,
    end: datetime,
    *,
    dry_run: bool = True,
) -> None:
    """
    Download ADS-B trajectory data for a terminal area bounding box.

    Args:
        airport: Airport key matching AIRPORT_BBOXES (e.g., 'KLAX').
        start:   UTC start datetime.
        end:     UTC end datetime.
        dry_run: If True, only log.
    """
    if not dry_run:
        raise RuntimeError(
            "dry_run=False requires team-lead approval. See task brief hard rule 1."
        )

    if airport not in AIRPORT_BBOXES:
        raise ValueError(
            f"Airport '{airport}' not in AIRPORT_BBOXES. "
            f"Add bounding box before downloading."
        )

    bbox = AIRPORT_BBOXES[airport]
    dest = OUTPUT_DIR / airport / f"{airport}_{start.date()}_{end.date()}.parquet"

    if dry_run:
        logger.info(
            "DRY RUN — ADS-B source_id=%s airport=%s bbox=%s start=%s end=%s -> %s",
            SOURCE_ID, airport, bbox, start.isoformat(), end.isoformat(), dest,
        )
        return

    if not _check_traffic_available():
        raise ImportError(
            "The 'traffic' library is required for ADS-B download. "
            "Install: pip install traffic"
        )

    from traffic.data import opensky  # type: ignore

    logger.info(
        "Querying OpenSky for %s bbox=%s %s to %s",
        airport, bbox, start, end,
    )
    traffic_data = opensky.history(
        start,
        stop=end,
        bounds=bbox,
    )

    if traffic_data is None or len(traffic_data) == 0:
        raise RuntimeError(
            f"OpenSky returned no data for {airport} {start} to {end}. "
            "Check credentials and Impala access."
        )

    dest.parent.mkdir(parents=True, exist_ok=True)
    traffic_data.to_parquet(dest)
    logger.info("ADS-B data saved to %s", dest)

    from aerosafety.data.downloaders._base import _write_manifest_entry
    import hashlib

    sha = hashlib.sha256(dest.read_bytes()).hexdigest()
    _write_manifest_entry({
        "source_id": SOURCE_ID,
        "url_fetched": f"opensky://impala/{airport}",
        "access_timestamp": datetime.now(timezone.utc).isoformat(),
        "local_file_path": str(dest),
        "sha256": sha,
        "http_status_code": 200,
        "content_length_bytes": dest.stat().st_size,
        "error": None,
    })


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    from datetime import date
    start_dt = datetime(2023, 6, 1, 0, 0, 0, tzinfo=timezone.utc)
    end_dt = datetime(2023, 6, 1, 6, 0, 0, tzinfo=timezone.utc)
    download_adsb_trajectories("KLAX", start_dt, end_dt, dry_run=True)
    logger.info(
        "Dry run complete. Register at opensky-network.org and get "
        "team-lead approval before executing with dry_run=False."
    )
