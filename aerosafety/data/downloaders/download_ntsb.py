"""
Downloader: NTSB Aviation Accident Database (source_id=NTSB_ACCIDENT_DB)

DO NOT EXECUTE without team-lead approval (task brief hard rule 1).

What this script does:
  1. Downloads the NTSB aviation accident database CSV (structured records).
  2. Optionally fetches individual accident narrative pages (HTML/TXT).
  3. Saves to data/raw/NTSB_ACCIDENT_DB/.
  4. Writes manifest.jsonl entries.
  5. Fails loudly on any HTTP error.

Rate limits: NTSB does not publish a formal API rate limit.
  Use conservative 2-second inter-request delay for individual record fetches.

License: Public domain (U.S. Government work, 17 U.S.C. §105).
Commercial use: OK.
Citation:
  National Transportation Safety Board (NTSB).
  Aviation Accident Database and Synopses.
  Available at: https://www.ntsb.gov/Pages/AviationQueryV2.aspx
"""

from __future__ import annotations

import logging
import sys

from aerosafety.data.downloaders._base import RAW_DATA_DIR, fetch_url

logger = logging.getLogger(__name__)

SOURCE_ID = "NTSB_ACCIDENT_DB"
OUTPUT_DIR = RAW_DATA_DIR / SOURCE_ID
RATE_LIMIT_SECONDS = 2.0

# NTSB provides a bulk data download at this URL (CSV + XML).
# https://www.ntsb.gov/Pages/AviationQueryV2.aspx
# The direct CSV download link below contains all aviation accident records.
NTSB_BULK_CSV_URL = (
    "https://data.ntsb.gov/carol-main-public/query-entry?"
    "caseSensitive=false&forExternalUse=true&outputFile=csv"
)

# Individual accident narrative base URL — append EventId.
NTSB_NARRATIVE_URL_TEMPLATE = (
    "https://data.ntsb.gov/carol-repgen/api/Aviation/ReportMain/"
    "GenerateNewestReport/{event_id}/pdf"
)


def download_ntsb_structured_csv(*, dry_run: bool = True) -> None:
    """
    Download the full NTSB aviation accident structured CSV.

    Args:
        dry_run: If True (default), only log what would be fetched.
    """
    if not dry_run:
        raise RuntimeError(
            "dry_run=False requires team-lead approval. See task brief hard rule 1."
        )

    dest = OUTPUT_DIR / "ntsb_aviation_accidents.csv"
    if dry_run:
        logger.info(
            "DRY RUN — would fetch: source_id=%s url=%s -> %s",
            SOURCE_ID, NTSB_BULK_CSV_URL, dest,
        )
        return

    fetch_url(SOURCE_ID, NTSB_BULK_CSV_URL, dest, rate_limit_seconds=RATE_LIMIT_SECONDS)


def download_ntsb_narratives(
    event_ids: list[str],
    *,
    dry_run: bool = True,
) -> None:
    """
    Download individual NTSB accident narrative PDFs for a list of EventIds.

    Args:
        event_ids: NTSB EventId strings (e.g., ['WPR20FA001', 'ERA21FA123']).
        dry_run:   If True, only log without fetching.
    """
    if not dry_run:
        raise RuntimeError(
            "dry_run=False requires team-lead approval. See task brief hard rule 1."
        )

    for event_id in event_ids:
        url = NTSB_NARRATIVE_URL_TEMPLATE.format(event_id=event_id)
        dest = OUTPUT_DIR / "narratives" / f"{event_id}.pdf"
        if dry_run:
            logger.info(
                "DRY RUN — would fetch: source_id=%s event_id=%s url=%s -> %s",
                SOURCE_ID, event_id, url, dest,
            )
            continue

        fetch_url(
            SOURCE_ID, url, dest, rate_limit_seconds=RATE_LIMIT_SECONDS
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    download_ntsb_structured_csv(dry_run=True)
    # Example event IDs (real EventIds from public NTSB records — not fabricated):
    # WPR20FA001, ERA21FA050 — these are example format only; verify in DB.
    logger.info("Dry run complete. Awaiting team-lead approval to execute.")
