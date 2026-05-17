"""
NOTAM parser conforming to ICAO Annex 15 (16th edition, 2018) and
FAA Order JO 7930.2S — Notices to Air Missions.

References:
    ICAO Annex 15, 16th edition, 2018 — Aeronautical Information Services
    https://www.icao.int/safety/information-management/Pages/Annex15.aspx

    FAA Order JO 7930.2S — Notices to Air Missions (NOTAMs)
    https://www.faa.gov/regulations_policies/orders_notices/index.cfm/go/document.information/documentID/1038268

Format covered: ICAO NOTAM (Series/Number/Year, Q/A/B/C/D/E/F/G fields)
as distributed via ICAO SNOWFLAKE / AFTN format.

Dependencies (for infra-architect):
    pydantic >= 2.0

LIMITATION: The parser handles the standard structured NOTAM format.
Domestic US D-NOTAMs in older plain-text format may not parse correctly.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime

from pydantic import BaseModel


class NOTAMParseError(ValueError):
    """Raised when the NOTAM string cannot be parsed."""


class QLine(BaseModel):
    """
    Decoded NOTAM Q-line.

    ICAO Annex 15, Appendix 6, §6.2:
      Q) FIR/NOTAM_CODE/TRAFFIC/PURPOSE/SCOPE/LOWER/UPPER/COORDINATES
    """
    fir: str                       # Flight Information Region (e.g. KZNY)
    notam_code: str                # ICAO NOTAM code (e.g. QMRLC = runway light change)
    traffic: str                   # IV/V/K (IFR, VFR, ...)
    purpose: str                   # N/B/O/M/K (Normal, Briefing, ...)
    scope: str                     # A/AE/AW/E/W (Aerodrome, En-route, ...)
    lower_fl: int                  # lower flight level limit (000 = ground)
    upper_fl: int                  # upper flight level limit
    coordinates: str               # lat/lon centre + radius (e.g. 5129N00028W005)
    subject: str                   # first 2 chars of notam_code (subject)
    condition: str                 # chars 3-4 of notam_code (condition)


class NOTAMObservation(BaseModel):
    """
    Parsed NOTAM observation.

    Standards:
        ICAO Annex 15, 16th edition, 2018
        FAA Order JO 7930.2S
    References:
        https://www.icao.int/safety/information-management/Pages/Annex15.aspx
        https://www.faa.gov/regulations_policies/orders_notices
    """
    raw: str
    series: str                        # NOTAM series letter (A-Z)
    number: str                        # NOTAM number (e.g. 1234/24)
    notam_type: str                    # N(ew)/R(eplacement)/C(ancellation)
    q_line: QLine | None = None
    location: str                      # A) field — ICAO location indicator
    effective_from: datetime | None = None  # B) field — UTC
    effective_to: datetime | None = None    # C) field — UTC; None if PERM
    permanent: bool = False            # True if C) field is PERM
    estimated: bool = False            # True if C) field has suffix EST
    schedule: str | None = None    # D) field (schedule string, optional)
    text: str = ""                     # E) field — plain-language description
    lower_limit: str | None = None # F) field (lower limit, optional)
    upper_limit: str | None = None # G) field (upper limit, optional)
    affected_runways: list[str] = []   # runway IDs extracted from E text
    affected_taxiways: list[str] = []  # taxiway IDs extracted from E text


# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# NOTAM header: series + number  e.g.  A1234/24 NOTAMN
_HDR_RE = re.compile(
    r"(?P<series>[A-Z])(?P<num>\d{4}/\d{2,4})\s+NOTAM(?P<type>[NRC])"
)

# Q-line
# Coordinate format: DDDDNdddddErrr or DDDDSdddddWrrr (lat=4 digits + N/S,
# lon=5 digits + E/W, radius=3 digits). Example: 4038N07356W025
_Q_RE = re.compile(
    r"Q\)\s*(?P<fir>[A-Z]{4})/(?P<code>Q[A-Z]{4})/(?P<tfc>[A-Z/]+)/"
    r"(?P<purp>[A-Z/]+)/(?P<scope>[A-Z/]+)/(?P<lower>\d{3})/(?P<upper>\d{3})/"
    r"(?P<coords>\d{4}[NS]\d{5}[EW]\d{3})"
)

# Simple field extractors — each line begins with letter and )
_FIELD_RE = re.compile(
    r"\b(?P<field>[A-G])\)\s*(?P<value>[^\n]+?)(?=\s+[A-G]\)|$)", re.DOTALL
)

# Datetime: YYMMDDHHmm (10 digits)
_DT_RE = re.compile(r"(?P<yy>\d{2})(?P<mo>\d{2})(?P<dd>\d{2})(?P<hh>\d{2})(?P<mm>\d{2})")

# Runway extraction: find each RWY/RWYS/RW keyword, then collect all \d{2}[LRC]?
# identifiers within the next 40 characters, stopping before the first
# 4+-letter word that is not AND/OR (e.g. stop at CLOSED, FOR, MAINTENANCE).
# Handles: "RWY 13R/31L", "RWY 13R AND 31L", "RWY 13R AND RWY 31L",
#          "RWYS 13R, 31L", "RWY 09", "RWY 13/31".
_RWY_ANCHOR_RE = re.compile(r"\bRW(?:YS?|S)?\b", re.IGNORECASE)
_RWY_ID_RE = re.compile(r"\b(\d{2}[LRC]?)\b")
_RWY_STOP_RE = re.compile(r"\b(?!AND\b|OR\b)[A-Z]{4,}\b", re.IGNORECASE)

# Taxiway pattern: TWY [A-Z]+[0-9]* in E text
_TWY_RE = re.compile(r"\bTWY\s+(?P<id>[A-Z][A-Z0-9]*)\b")


def _parse_notam_dt(s: str, century_year: int) -> datetime | None:
    """Parse a 10-digit NOTAM datetime string to UTC datetime."""
    s = s.strip()
    if s in ("PERM", "UFN", ""):
        return None
    m = _DT_RE.match(s)
    if not m:
        raise NOTAMParseError(f"Cannot parse NOTAM datetime '{s}'")
    yy = int(m.group("yy"))
    mo = int(m.group("mo"))
    dd = int(m.group("dd"))
    hh = int(m.group("hh"))
    mm = int(m.group("mm"))
    full_year = (century_year // 100) * 100 + yy
    try:
        return datetime(full_year, mo, dd, hh, mm, tzinfo=UTC)
    except ValueError as exc:
        raise NOTAMParseError(f"Invalid NOTAM datetime '{s}': {exc}") from exc


def parse_notam(raw: str) -> NOTAMObservation:
    """
    Parse an ICAO-format NOTAM string.

    Standards:
        ICAO Annex 15, 16th edition, 2018
        FAA Order JO 7930.2S
    References:
        https://www.icao.int/safety/information-management/Pages/Annex15.aspx
        https://www.faa.gov/regulations_policies/orders_notices

    Raises NOTAMParseError on any parsing failure.
    CLAUDE.md §8.1: no silent failure.
    """
    raw = raw.strip()
    now = datetime.now(UTC)

    # Header
    hdr = _HDR_RE.search(raw)
    if not hdr:
        raise NOTAMParseError(
            f"Cannot find NOTAM header (series+number+type) in: {raw[:80]!r}"
        )
    series = hdr.group("series")
    number = hdr.group("num")
    notam_type = hdr.group("type")

    # Q-line
    q_line: QLine | None = None
    qm = _Q_RE.search(raw)
    if qm:
        code = qm.group("code")
        q_line = QLine(
            fir=qm.group("fir"),
            notam_code=code,
            traffic=qm.group("tfc"),
            purpose=qm.group("purp"),
            scope=qm.group("scope"),
            lower_fl=int(qm.group("lower")),
            upper_fl=int(qm.group("upper")),
            coordinates=qm.group("coords"),
            subject=code[1:3] if len(code) >= 3 else code,
            condition=code[3:5] if len(code) >= 5 else "",
        )

    # Field extraction A-G
    fields: dict[str, str] = {}
    for fm in _FIELD_RE.finditer(raw):
        fields[fm.group("field")] = fm.group("value").strip()

    # A) Location
    location = fields.get("A", "").strip()
    if not location:
        raise NOTAMParseError("Missing A) field (location) in NOTAM")

    # B) Effective from
    b_raw = fields.get("B", "")
    effective_from = _parse_notam_dt(b_raw, now.year) if b_raw else None

    # C) Effective to
    c_raw = fields.get("C", "").upper()
    permanent = False
    estimated = False
    effective_to: datetime | None = None
    if c_raw:
        if "PERM" in c_raw:
            permanent = True
        elif "UFN" in c_raw or c_raw == "":
            effective_to = None
        else:
            if c_raw.endswith("EST"):
                estimated = True
                c_raw = c_raw[:-3].strip()
            effective_to = _parse_notam_dt(c_raw, now.year)

    # D) Schedule
    schedule = fields.get("D", None)

    # E) Plain-language text
    text = fields.get("E", "")

    # F) Lower limit
    lower_limit = fields.get("F", None)

    # G) Upper limit
    upper_limit = fields.get("G", None)

    # Extract runway IDs: anchor on each RWY/RW keyword, then scan the next
    # 40 chars for \d{2}[LRC]? tokens, stopping at the first 4+-letter
    # non-AND/OR word. Handles slash- and AND-separated lists.
    runway_ids: set[str] = set()
    for anchor in _RWY_ANCHOR_RE.finditer(text):
        segment = text[anchor.end():anchor.end() + 40]
        stop = _RWY_STOP_RE.search(segment)
        if stop:
            segment = segment[: stop.start()]
        for id_match in _RWY_ID_RE.finditer(segment):
            runway_ids.add(id_match.group(1))
    affected_runways = sorted(runway_ids)
    affected_taxiways = sorted({m.group("id") for m in _TWY_RE.finditer(text)})

    return NOTAMObservation(
        raw=raw,
        series=series,
        number=number,
        notam_type=notam_type,
        q_line=q_line,
        location=location,
        effective_from=effective_from,
        effective_to=effective_to,
        permanent=permanent,
        estimated=estimated,
        schedule=schedule,
        text=text,
        lower_limit=lower_limit,
        upper_limit=upper_limit,
        affected_runways=sorted(affected_runways),
        affected_taxiways=sorted(affected_taxiways),
    )
