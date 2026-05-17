"""
Downloader: FAA NOTAM Reference Documents (source_id=FAA_DOCS, NOTAM subset)

DO NOT EXECUTE without team-lead approval (task brief hard rule 1).

What this script downloads:
  1. FAA JO 7930.2 — NOTAM System Order (NOTAM format definitions and examples).
  2. FAA AIM Chapter 5 Section 1 (NOTAM operational procedures).
  3. FAA JO 7110.65 (ATC order — NOTAM handling in ATC context).
  4. FAA AC 91-70B (contains NOTAM worked examples for oceanic operations).

These are the primary sources for Task Family 4 (NOTAM compliance) KP extraction.
Real NOTAM volume for scenario construction uses publicly archived NOTAM
snapshots from academic papers and ADS-B Exchange, not a gated API.

DESIGN NOTE: The FAA NOTAM API (api.faa.gov) was removed from the critical
path because it requires registration with US-resident orientation.
See source_registry.yaml FAA_NOTAM_API (off critical path,
residency_restriction=us_resident). This script replaces it with equivalent
public PDF/HTML documents that contain NOTAM format specifications and examples.

Rate limits: FAA website — no published limit; use 1.5-second inter-request delay.

License: Public domain (U.S. Government work, 17 U.S.C. §105).
Commercial use: OK.
"""

from __future__ import annotations

import logging
import sys

from aerosafety.data.downloaders._base import RAW_DATA_DIR, fetch_url

logger = logging.getLogger(__name__)

SOURCE_ID = "FAA_DOCS"
OUTPUT_DIR = RAW_DATA_DIR / SOURCE_ID / "notam_reference"
RATE_LIMIT_SECONDS = 1.5

# FAA JO 7930.2 — NOTAM System Order.
# Defines: NOTAM format, Q-code structure, effective time encoding,
# schedule groups, keyword taxonomy, annotated examples.
JO_7930_2_URL = (
    "https://www.faa.gov/documentLibrary/media/Order/JO_7930.2R.pdf"
)

# FAA JO 7110.65 (ATC Order) — full order including NOTAM handling in ATC.
JO_7110_65_URL = (
    "https://www.faa.gov/documentLibrary/media/Order/"
    "7110.65Z_Basic_dtd_4-3-14.pdf"
)

# FAA AC 91-70B — contains NOTAM worked examples for oceanic/remote operations.
AC_91_70B_URL = (
    "https://www.faa.gov/documentLibrary/media/Advisory_Circular/AC_91-70B.pdf"
)

# AIM Chapter 5 Section 1 HTML — NOTAM operational procedures for pilots/dispatchers.
AIM_NOTAM_SECTION_URL = (
    "https://www.faa.gov/air_traffic/publications/atpubs/aim_html/"
    "chap5_section_1.html"
)

NOTAM_REFERENCE_DOCS: list[tuple[str, str]] = [
    ("JO_7930.2_NOTAM_System.pdf", JO_7930_2_URL),
    ("JO_7110.65_ATC_Order.pdf", JO_7110_65_URL),
    ("AC_91-70B_Oceanic_Operations.pdf", AC_91_70B_URL),
    ("AIM_Chapter5_Section1_NOTAMs.html", AIM_NOTAM_SECTION_URL),
]


def download_notam_reference_docs(*, dry_run: bool = True) -> None:
    """
    Download FAA NOTAM format reference documents.

    No API key or registration required. All public domain.

    Args:
        dry_run: If True (default), only log what would be fetched.
    """
    if not dry_run:
        raise RuntimeError(
            "dry_run=False requires team-lead approval. See task brief hard rule 1."
        )

    for filename, url in NOTAM_REFERENCE_DOCS:
        dest = OUTPUT_DIR / filename
        if dry_run:
            logger.info(
                "DRY RUN — NOTAM ref source_id=%s url=%s -> %s",
                SOURCE_ID, url, dest,
            )
            continue

        fetch_url(SOURCE_ID, url, dest, rate_limit_seconds=RATE_LIMIT_SECONDS)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    download_notam_reference_docs(dry_run=True)
    logger.info(
        "Dry run complete. Awaiting team-lead approval.\n"
        "REMINDER: FAA NOTAM API (api.faa.gov) is off critical path "
        "(residency_restriction=us_resident). NOTAM KPs extracted from "
        "JO 7930.2 and AIM instead."
    )
