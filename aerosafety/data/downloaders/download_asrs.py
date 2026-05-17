"""
Downloader: NASA ASRS Database (source_id=NASA_ASRS)

DO NOT EXECUTE without team-lead approval (task brief hard rule 1).

What this script does:
  1. Queries the ASRS database search form for bulk CSV export.
  2. Saves the CSV to data/raw/NASA_ASRS/.
  3. Writes a manifest entry for every file fetched.
  4. Fails loudly on any HTTP error — no silent fallback.

Rate limits: ASRS website does not publish a formal rate limit.
  Use conservative 2-second inter-request delay.

License: Public domain (U.S. Government work, 17 U.S.C. §105).
Commercial use: OK.
Citation:
  NASA Aviation Safety Reporting System (ASRS).
  National Aeronautics and Space Administration, Ames Research Center.
  Available at: https://asrs.arc.nasa.gov
"""

from __future__ import annotations

import logging
import sys

from aerosafety.data.downloaders._base import RAW_DATA_DIR, fetch_url

logger = logging.getLogger(__name__)

SOURCE_ID = "NASA_ASRS"
OUTPUT_DIR = RAW_DATA_DIR / SOURCE_ID
RATE_LIMIT_SECONDS = 2.0

# ASRS bulk download endpoint (CSV export via direct URL).
# The ASRS database search supports building query URLs by parameter.
# The URL below fetches all records in the chosen year range as CSV.
# Ref: https://asrs.arc.nasa.gov/search/database.html
ASRS_QUERY_BASE_URL = "https://asrs.arc.nasa.gov/search/request.php"


def download_asrs_csv(
    year_start: int,
    year_end: int,
    *,
    dry_run: bool = True,
) -> None:
    """
    Download ASRS records for the given year range.

    Args:
        year_start: First year (inclusive) to download.
        year_end:   Last year (inclusive) to download.
        dry_run:    If True (default), only log what would be fetched. NEVER
                    set to False without team-lead approval.
    """
    if not dry_run:
        raise RuntimeError(
            "dry_run=False is not permitted without explicit team-lead approval. "
            "See task brief hard rule 1."
        )

    for year in range(year_start, year_end + 1):
        params = {
            "format": "csv",
            "from": f"{year}01",
            "to": f"{year}12",
        }
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{ASRS_QUERY_BASE_URL}?{query_string}"
        dest = OUTPUT_DIR / f"asrs_{year}.csv"

        if dry_run:
            logger.info(
                "DRY RUN — would fetch: source_id=%s url=%s -> %s",
                SOURCE_ID, url, dest,
            )
            continue

        # Production path (only reachable after team-lead approval removes
        # the RuntimeError guard above).
        fetch_url(
            SOURCE_ID,
            url,
            dest,
            rate_limit_seconds=RATE_LIMIT_SECONDS,
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    # Default: dry run for 2020–2024 as a representative range.
    download_asrs_csv(2020, 2024, dry_run=True)
    logger.info(
        "Dry run complete. Set dry_run=False only after team-lead approval."
    )
