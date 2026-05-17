"""
TAF parser conforming to WMO No. 306 Vol. I.1, Code form FM 51-XVI (TAF).
Reference: https://library.wmo.int/records/item/35713-manual-on-codes-volume-i-1

Standard: WMO No. 306 Vol. I.1, FM 51-XVI TAF

Dependencies (for infra-architect):
    pydantic >= 2.0

Covers:
- Validity period (YYGGggZ YYGGggZ)
- FM (from) groups
- BECMG (becoming) groups
- TEMPO (temporary) groups
- PROB groups (PROB30, PROB40)

Unparsed tokens are stored in `remarks` verbatim. This parser is
research-grade and does not implement the full FM 51 grammar.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel

from aerosafety.tools.metar_parser import (
    _CLR_RE,
    _SKY_RE,
    _VIS_RE,
    _WEATHER_RE,
    _WIND_RE,
    SkyCoverEnum,
    SkyLayer,
    WindObservation,
    _mps_to_kt,
)


class TAFParseError(ValueError):
    """Raised when the TAF string cannot be parsed."""


class ChangeIndicator(str, Enum):
    FM = "FM"
    BECMG = "BECMG"
    TEMPO = "TEMPO"
    PROB30 = "PROB30"
    PROB40 = "PROB40"


class TAFConditions(BaseModel):
    """Weather conditions in a TAF base or change group."""
    wind: WindObservation | None = None
    visibility_m: int | None = None
    weather: list[str] = []
    sky: list[SkyLayer] = []
    remarks: str = ""


class TAFChangeGroup(BaseModel):
    """
    A FM/BECMG/TEMPO/PROB change group within a TAF.

    Standard: WMO No. 306 Vol. I.1, FM 51-XVI §15.6
    """
    indicator: ChangeIndicator
    valid_from: datetime | None = None   # UTC
    valid_to: datetime | None = None     # UTC
    conditions: TAFConditions


class TAFObservation(BaseModel):
    """
    Parsed TAF observation.

    Standard: WMO No. 306 Vol. I.1, FM 51-XVI TAF
    Reference: https://library.wmo.int/records/item/35713-manual-on-codes-volume-i-1
    """
    raw: str
    station_id: str
    issue_time: datetime       # UTC — when the TAF was issued
    valid_from: datetime       # UTC — start of TAF validity window
    valid_to: datetime         # UTC — end of TAF validity window
    amd: bool = False          # True if AMD (amendment)
    cor: bool = False          # True if COR (correction)
    base_conditions: TAFConditions
    change_groups: list[TAFChangeGroup] = []


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_TIME_RE = re.compile(r"^(?P<dd>\d{2})(?P<hh>\d{2})(?P<mm>\d{2})Z$")
_VALID_RE = re.compile(r"^(?P<d1>\d{2})(?P<h1>\d{2})/(?P<d2>\d{2})(?P<h2>\d{2})$")
_FM_RE = re.compile(r"^FM(?P<dd>\d{2})(?P<hh>\d{2})(?P<mm>\d{2})$")
_PROB_RE = re.compile(r"^PROB(?P<pct>\d{2})$")
_TEMPO_BECMG_VALID_RE = re.compile(r"^(?P<d1>\d{2})(?P<h1>\d{2})/(?P<d2>\d{2})(?P<h2>\d{2})$")


def _make_utc(year: int, month: int, day: int, hour: int, minute: int = 0) -> datetime:
    # Hour 24 means midnight of next day (WMO convention for TAF end times)
    if hour == 24:
        from datetime import timedelta
        base = datetime(year, month, day, 0, 0, tzinfo=UTC)
        return base + timedelta(days=1)
    try:
        return datetime(year, month, day, hour, minute, tzinfo=UTC)
    except ValueError as exc:
        raise TAFParseError(f"Invalid date components day={day} hour={hour}: {exc}") from exc


def _parse_conditions(tokens: list[str]) -> TAFConditions:
    """Parse a flat list of condition tokens into a TAFConditions object."""
    wind: WindObservation | None = None
    visibility_m: int | None = None
    weather: list[str] = []
    sky: list[SkyLayer] = []
    remainder: list[str] = []

    for tok in tokens:
        if tok == "CAVOK":
            visibility_m = 9999
            sky.append(SkyLayer(cover=SkyCoverEnum.CAVOK))
            continue

        wm = _WIND_RE.match(tok)
        if wm and wind is None:
            dir_s = wm.group("dir")
            spd = int(wm.group("spd"))
            gst = int(wm.group("gst")) if wm.group("gst") else None
            unit = wm.group("unit")
            if unit == "MPS":
                spd = _mps_to_kt(spd)
                gst = _mps_to_kt(gst) if gst else None
                unit = "KT"
            elif unit == "KMH":
                spd = round(spd / 1.852)
                gst = round(gst / 1.852) if gst else None
                unit = "KT"
            variable = dir_s == "VRB"
            wind = WindObservation(
                direction_deg=None if variable else int(dir_s),
                variable=variable,
                speed_kt=spd,
                gust_kt=gst,
                unit=unit,
            )
            continue

        vm = _VIS_RE.match(tok)
        if vm and visibility_m is None:
            visibility_m = 9999 if tok == "9999" else int(tok)
            continue

        if _WEATHER_RE.match(tok):
            weather.append(tok)
            continue

        clrm = _CLR_RE.match(tok)
        if clrm:
            sky.append(SkyLayer(cover=SkyCoverEnum(tok)))
            continue

        sm = _SKY_RE.match(tok)
        if sm:
            sky.append(
                SkyLayer(
                    cover=SkyCoverEnum(sm.group("cov")),
                    height_ft=int(sm.group("hgt")) * 100,
                    cloud_type=sm.group("type"),
                )
            )
            continue

        # NSW — No Significant Weather (clears weather in BECMG/TEMPO)
        if tok == "NSW":
            weather = []
            continue

        remainder.append(tok)

    return TAFConditions(
        wind=wind,
        visibility_m=visibility_m,
        weather=weather,
        sky=sky,
        remarks=" ".join(remainder),
    )


def parse_taf(raw: str) -> TAFObservation:
    """
    Parse a TAF string and return a TAFObservation.

    Standard: WMO No. 306 Vol. I.1, FM 51-XVI TAF
    Reference: https://library.wmo.int/records/item/35713-manual-on-codes-volume-i-1

    Raises TAFParseError on any parsing failure.
    CLAUDE.md §8.1: no silent failure.
    """
    raw = raw.strip()
    tokens = raw.split()
    if len(tokens) < 4:
        raise TAFParseError(f"Too few tokens to be a valid TAF: {raw!r}")

    idx = 0
    now = datetime.now(UTC)

    # Optional TAF type identifier
    if tokens[idx] == "TAF":
        idx += 1

    # AMD / COR flags
    amd = False
    cor = False
    while idx < len(tokens) and tokens[idx] in ("AMD", "COR"):
        if tokens[idx] == "AMD":
            amd = True
        else:
            cor = True
        idx += 1

    # Station identifier
    if idx >= len(tokens):
        raise TAFParseError("Missing station identifier")
    station = tokens[idx]
    if not re.fullmatch(r"[A-Z]{4}", station):
        raise TAFParseError(f"Expected ICAO station ID, got '{station}'")
    idx += 1

    # Issue time
    if idx >= len(tokens):
        raise TAFParseError("Missing issue time")
    tm = _TIME_RE.match(tokens[idx])
    if not tm:
        raise TAFParseError(f"Cannot parse issue time '{tokens[idx]}'")
    issue_time = _make_utc(now.year, now.month, int(tm.group("dd")), int(tm.group("hh")), int(tm.group("mm")))
    idx += 1

    # Validity period  DDhh/DDhh
    if idx >= len(tokens):
        raise TAFParseError("Missing validity period")
    vm = _VALID_RE.match(tokens[idx])
    if not vm:
        raise TAFParseError(f"Cannot parse validity period '{tokens[idx]}'")
    valid_from = _make_utc(now.year, now.month, int(vm.group("d1")), int(vm.group("h1")))
    valid_to = _make_utc(now.year, now.month, int(vm.group("d2")), int(vm.group("h2")))
    idx += 1

    # Split remaining tokens into base + change groups by change indicators
    # Indicators: FM..., BECMG, TEMPO, PROBxx
    CHANGE_STARTERS = {"BECMG", "TEMPO"}

    def is_change_start(tok: str) -> bool:
        return (
            tok in CHANGE_STARTERS
            or _FM_RE.match(tok) is not None
            or _PROB_RE.match(tok) is not None
        )

    # Collect base tokens (everything before the first change group)
    base_tokens: list[str] = []
    while idx < len(tokens) and not is_change_start(tokens[idx]):
        base_tokens.append(tokens[idx])
        idx += 1

    base_conditions = _parse_conditions(base_tokens)

    # Parse change groups
    change_groups: list[TAFChangeGroup] = []
    while idx < len(tokens):
        tok = tokens[idx]

        # FM group: FMDDHHmm
        fm = _FM_RE.match(tok)
        if fm:
            idx += 1
            fm_from = _make_utc(now.year, now.month, int(fm.group("dd")), int(fm.group("hh")), int(fm.group("mm")))
            cond_tokens: list[str] = []
            while idx < len(tokens) and not is_change_start(tokens[idx]):
                cond_tokens.append(tokens[idx])
                idx += 1
            change_groups.append(TAFChangeGroup(
                indicator=ChangeIndicator.FM,
                valid_from=fm_from,
                valid_to=None,  # FM groups end when next FM or TAF ends
                conditions=_parse_conditions(cond_tokens),
            ))
            continue

        # BECMG / TEMPO with validity window DDhh/DDhh
        if tok in ("BECMG", "TEMPO"):
            indicator = ChangeIndicator(tok)
            idx += 1
            grp_from: datetime | None = None
            grp_to: datetime | None = None
            if idx < len(tokens) and _TEMPO_BECMG_VALID_RE.match(tokens[idx]):
                gv = _TEMPO_BECMG_VALID_RE.match(tokens[idx])
                grp_from = _make_utc(now.year, now.month, int(gv.group("d1")), int(gv.group("h1")))
                grp_to = _make_utc(now.year, now.month, int(gv.group("d2")), int(gv.group("h2")))
                idx += 1
            cond_tokens = []
            while idx < len(tokens) and not is_change_start(tokens[idx]):
                cond_tokens.append(tokens[idx])
                idx += 1
            change_groups.append(TAFChangeGroup(
                indicator=indicator,
                valid_from=grp_from,
                valid_to=grp_to,
                conditions=_parse_conditions(cond_tokens),
            ))
            continue

        # PROB30 / PROB40 — may be followed by TEMPO and a validity window
        pb = _PROB_RE.match(tok)
        if pb:
            pct = int(pb.group("pct"))
            if pct not in (30, 40):
                raise TAFParseError(f"PROB group has unexpected probability: PROB{pct}")
            indicator = ChangeIndicator(f"PROB{pct}")
            idx += 1
            # PROB may be followed by TEMPO
            if idx < len(tokens) and tokens[idx] == "TEMPO":
                idx += 1  # consume TEMPO but indicator stays PROBxx
            grp_from = None
            grp_to = None
            if idx < len(tokens) and _TEMPO_BECMG_VALID_RE.match(tokens[idx]):
                gv = _TEMPO_BECMG_VALID_RE.match(tokens[idx])
                grp_from = _make_utc(now.year, now.month, int(gv.group("d1")), int(gv.group("h1")))
                grp_to = _make_utc(now.year, now.month, int(gv.group("d2")), int(gv.group("h2")))
                idx += 1
            cond_tokens = []
            while idx < len(tokens) and not is_change_start(tokens[idx]):
                cond_tokens.append(tokens[idx])
                idx += 1
            change_groups.append(TAFChangeGroup(
                indicator=indicator,
                valid_from=grp_from,
                valid_to=grp_to,
                conditions=_parse_conditions(cond_tokens),
            ))
            continue

        # Unrecognised token at change group boundary
        idx += 1

    return TAFObservation(
        raw=raw,
        station_id=station,
        issue_time=issue_time,
        valid_from=valid_from,
        valid_to=valid_to,
        amd=amd,
        cor=cor,
        base_conditions=base_conditions,
        change_groups=change_groups,
    )
