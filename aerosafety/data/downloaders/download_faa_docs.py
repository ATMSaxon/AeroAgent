"""
Downloader: FAA Regulatory Documents
  - FAA Published Orders, ACs, AIM (source_id=FAA_DOCS)
      Covers: Advisory Circulars, JO 7110.65, JO 7930.2, wake turbulence tables
  - Title 14 CFR / eCFR (source_id=FAA_CFR14)
  - FAA Airport Diagrams (source_id=FAA_AIRPORT_DIAGRAMS)
  - FAA MMEL Documents (source_id=FAA_MMEL)
  - FAA SDR Database (source_id=FAA_SDR)

DO NOT EXECUTE without team-lead approval (task brief hard rule 1).

All sources are public domain (U.S. Government work, 17 U.S.C. §105).
No API key, no registration, no residency restriction.

Rate limits:
  FAA websites do not publish formal rate limits.
  Use 1.5-second inter-request delay as courtesy.
"""

from __future__ import annotations

import logging
import sys

from aerosafety.data.downloaders._base import RAW_DATA_DIR, fetch_url

logger = logging.getLogger(__name__)

RATE_LIMIT_SECONDS = 1.5

# ── Advisory Circulars ──────────────────────────────────────────────────────

# FAA_DOCS covers all FAA published orders, ACs, and AIM.
# Advisory Circulars and JO orders are all under this single source_id.
AC_SOURCE_ID = "FAA_DOCS"
AC_OUTPUT_DIR = RAW_DATA_DIR / AC_SOURCE_ID / "advisory_circulars"

# Priority ACs mapped to task families and download URLs.
# URL pattern: https://www.faa.gov/documentLibrary/media/{DocNum}.pdf
# These URLs are the canonical FAA document library paths.
PRIORITY_ACS: list[tuple[str, str, list[int]]] = [
    # (AC number, URL, task_families)
    ("AC_120-92B", "https://www.faa.gov/documentLibrary/media/Advisory_Circular/AC_120-92B.pdf", [1, 2]),
    ("AC_60-22",   "https://www.faa.gov/documentLibrary/media/Advisory_Circular/AC_60-22.pdf", [1, 2]),
    ("AC_43-16A",  "https://www.faa.gov/documentLibrary/media/Advisory_Circular/AC_43-16A.pdf", [8]),
    ("AC_120-16G", "https://www.faa.gov/documentLibrary/media/Advisory_Circular/AC_120-16G.pdf", [8]),
    ("AC_00-6B",   "https://www.faa.gov/documentLibrary/media/Advisory_Circular/AC_00-6B.pdf", [3]),
    ("AC_00-45H",  "https://www.faa.gov/documentLibrary/media/Advisory_Circular/AC_00-45H.pdf", [3]),
    ("AC_150_5300-13A", "https://www.faa.gov/documentLibrary/media/Advisory_Circular/150_5300_13a.pdf", [5]),
]


def download_advisory_circulars(*, dry_run: bool = True) -> None:
    for ac_num, url, _ in PRIORITY_ACS:
        dest = AC_OUTPUT_DIR / f"{ac_num}.pdf"
        if dry_run:
            logger.info(
                "DRY RUN — AC source_id=%s ac=%s url=%s -> %s",
                AC_SOURCE_ID, ac_num, url, dest,
            )
            continue
        fetch_url(AC_SOURCE_ID, url, dest, rate_limit_seconds=RATE_LIMIT_SECONDS)


# ── eCFR Title 14 ──────────────────────────────────────────────────────────

CFR_SOURCE_ID = "FAA_CFR14"
CFR_OUTPUT_DIR = RAW_DATA_DIR / CFR_SOURCE_ID

# eCFR XML bulk download.
ECFR_FULL_XML_URL = "https://www.ecfr.gov/current/title-14.xml"
ECFR_TITLE14_URL = "https://www.ecfr.gov/current/title-14"


def download_cfr_title14(*, dry_run: bool = True) -> None:
    dest = CFR_OUTPUT_DIR / "title-14.xml"
    if dry_run:
        logger.info(
            "DRY RUN — CFR source_id=%s url=%s -> %s",
            CFR_SOURCE_ID, ECFR_FULL_XML_URL, dest,
        )
        return
    if not dry_run:
        raise RuntimeError(
            "dry_run=False requires team-lead approval. See task brief hard rule 1."
        )


# ── Airport Diagrams ───────────────────────────────────────────────────────

DIAG_SOURCE_ID = "FAA_AIRPORT_DIAGRAMS"
DIAG_OUTPUT_DIR = RAW_DATA_DIR / DIAG_SOURCE_ID

# FAA d-TPP Airport Diagram cycle URL.
# The {CYCLE} placeholder is replaced with the 4-digit AIRAC cycle number.
# Current cycle can be found at https://aeronav.faa.gov/d-tpp/
DIAG_URL_TEMPLATE = (
    "https://aeronav.faa.gov/d-tpp/{cycle}/pdf/AD_{icao}.PDF"
)

PRIORITY_AIRPORTS_DIAGRAMS = [
    "KLAX", "KJFK", "KORD", "KATL", "KDFW",
    "KSFO", "KMIA", "KDEN", "KBOS", "KSEA",
]


def download_airport_diagrams(cycle: str, *, dry_run: bool = True) -> None:
    """
    Download airport diagrams for priority airports.

    Args:
        cycle: AIRAC cycle string, e.g. '2401' for first cycle of 2024.
        dry_run: If True, only log.
    """
    for icao in PRIORITY_AIRPORTS_DIAGRAMS:
        url = DIAG_URL_TEMPLATE.format(cycle=cycle, icao=icao)
        dest = DIAG_OUTPUT_DIR / cycle / f"{icao}.pdf"
        if dry_run:
            logger.info(
                "DRY RUN — DIAG source_id=%s icao=%s url=%s -> %s",
                DIAG_SOURCE_ID, icao, url, dest,
            )
            continue
        if not dry_run:
            raise RuntimeError(
                "dry_run=False requires team-lead approval. See task brief hard rule 1."
            )


# ── FAA JO 7110.65 Wake Turbulence Chapter ────────────────────────────────

WAKE_SOURCE_ID = "FAA_DOCS"
WAKE_OUTPUT_DIR = RAW_DATA_DIR / WAKE_SOURCE_ID / "wake_categories"

# ATC order JO 7110.65 HTML chapters.
# Wake turbulence separation is in Chapter 5 (Radar) and Chapter 3 (Terminal).
JO_7110_65_BASE = "https://www.faa.gov/air_traffic/publications/atpubs/atc_html/"
JO_WAKE_CHAPTER_URL = f"{JO_7110_65_BASE}chap5_section_5.html"


def download_wake_category_tables(*, dry_run: bool = True) -> None:
    dest = WAKE_OUTPUT_DIR / "jO7110_65_chap5_wake.html"
    if dry_run:
        logger.info(
            "DRY RUN — WAKE source_id=%s url=%s -> %s",
            WAKE_SOURCE_ID, JO_WAKE_CHAPTER_URL, dest,
        )
        return
    if not dry_run:
        raise RuntimeError(
            "dry_run=False requires team-lead approval. See task brief hard rule 1."
        )


# ── FAA MMEL ──────────────────────────────────────────────────────────────

MMEL_SOURCE_ID = "FAA_MMEL"
MMEL_OUTPUT_DIR = RAW_DATA_DIR / MMEL_SOURCE_ID

# MMEL index page — individual MMELs accessible from here.
MMEL_INDEX_URL = (
    "https://rgl.faa.gov/Regulatory_and_Guidance_Library/"
    "rgMakeModel.nsf/0/MainFrameSet"
)

# Priority MMEL documents with known direct PDF URLs (verify before use).
# These are example URLs; actual PDF paths require navigating the RGL system.
PRIORITY_MMEL: list[tuple[str, str]] = [
    # (aircraft_type_id, URL)
    # Actual MMEL PDF URLs must be retrieved from the RGL system at download time.
    # Placeholder format only — team-lead to confirm before enabling.
    ("B737-NG", "https://rgl.faa.gov/Regulatory_and_Guidance_Library/rgMakeModel.nsf/TODO_B737"),
    ("A320",    "https://rgl.faa.gov/Regulatory_and_Guidance_Library/rgMakeModel.nsf/TODO_A320"),
]


def download_mmel_documents(*, dry_run: bool = True) -> None:
    for aircraft_id, url in PRIORITY_MMEL:
        dest = MMEL_OUTPUT_DIR / f"{aircraft_id}_MMEL.pdf"
        if dry_run:
            logger.info(
                "DRY RUN — MMEL source_id=%s aircraft=%s url=%s -> %s "
                "[NOTE: URLs marked TODO — verify in RGL before enabling]",
                MMEL_SOURCE_ID, aircraft_id, url, dest,
            )
            continue
        if not dry_run:
            raise RuntimeError(
                "dry_run=False requires team-lead approval. See task brief hard rule 1."
            )


# ── FAA SDR ───────────────────────────────────────────────────────────────

SDR_SOURCE_ID = "FAA_SDR"
SDR_OUTPUT_DIR = RAW_DATA_DIR / SDR_SOURCE_ID

# FAA SDR download endpoint.
SDR_DOWNLOAD_URL = "https://av-info.faa.gov/sdrx/SDR_Export.asp"


def download_sdr_database(*, dry_run: bool = True) -> None:
    dest = SDR_OUTPUT_DIR / "sdr_export.csv"
    if dry_run:
        logger.info(
            "DRY RUN — SDR source_id=%s url=%s -> %s",
            SDR_SOURCE_ID, SDR_DOWNLOAD_URL, dest,
        )
        return
    if not dry_run:
        raise RuntimeError(
            "dry_run=False requires team-lead approval. See task brief hard rule 1."
        )


# ── ICAO Doc 8643 — Aircraft Type Designators (wake category lookup) ──────

ICAO8643_SOURCE_ID = "ICAO_DOC8643"
ICAO8643_OUTPUT_DIR = RAW_DATA_DIR / ICAO8643_SOURCE_ID

# ICAO Doc 8643 provides a searchable HTML/CSV interface at:
# https://www.icao.int/publications/doc8643/Pages/default.aspx
# The CSV export of aircraft type designators (including wake category) is
# accessible without registration.
ICAO8643_CSV_URL = (
    "https://www.icao.int/publications/doc8643/Pages/doc8643.aspx"
)


def download_icao_doc8643(*, dry_run: bool = True) -> None:
    """
    Download ICAO Doc 8643 aircraft type designator data.

    This provides the authoritative ICAO wake turbulence category (J/H/M/L)
    per aircraft type for Task Family 7.
    """
    dest = ICAO8643_OUTPUT_DIR / "doc8643_aircraft_types.csv"
    if dry_run:
        logger.info(
            "DRY RUN — ICAO8643 source_id=%s url=%s -> %s",
            ICAO8643_SOURCE_ID, ICAO8643_CSV_URL, dest,
        )
        return
    if not dry_run:
        raise RuntimeError(
            "dry_run=False requires team-lead approval. See task brief hard rule 1."
        )


# ── ICAO Free Documents (Doc 9859, Doc 9870) ──────────────────────────────

ICAO_FREE_SOURCE_IDS = {
    "ICAO_DOC9859": (
        "ICAO_DOC9859",
        # URL sourced from ICAO safety management guidance page (public).
        "https://www.icao.int/safety/SafetyManagement/Documents/"
        "Doc.9859.3rd%20Edition.alltext.en.pdf",
        "ICAO_Doc9859_Safety_Management_Manual.pdf",
    ),
    "ICAO_DOC9870": (
        "ICAO_DOC9870",
        "https://www.icao.int/safety/RunwayIncursion/Documents/"
        "Doc%209870%20EN.pdf",
        "ICAO_Doc9870_Runway_Incursion_Prevention.pdf",
    ),
}


def download_icao_free_docs(*, dry_run: bool = True) -> None:
    """Download ICAO documents that are freely available without purchase."""
    for source_id, url, filename in ICAO_FREE_SOURCE_IDS.values():
        dest = RAW_DATA_DIR / source_id / filename
        if dry_run:
            logger.info(
                "DRY RUN — ICAO free doc source_id=%s url=%s -> %s",
                source_id, url, dest,
            )
            continue
        if not dry_run:
            raise RuntimeError(
                "dry_run=False requires team-lead approval. See task brief hard rule 1."
            )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    download_advisory_circulars(dry_run=True)
    download_cfr_title14(dry_run=True)
    download_airport_diagrams("2312", dry_run=True)
    download_wake_category_tables(dry_run=True)
    download_mmel_documents(dry_run=True)
    download_sdr_database(dry_run=True)
    download_icao_doc8643(dry_run=True)
    download_icao_free_docs(dry_run=True)
    logger.info("All dry runs complete. Awaiting team-lead approval.")
