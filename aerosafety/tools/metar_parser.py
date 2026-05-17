"""
METAR parser conforming to WMO No. 306 Vol. I.1, Code form FM 15-XVI (METAR/SPECI).
Reference: https://library.wmo.int/records/item/35713-manual-on-codes-volume-i-1

Standard: WMO No. 306 Vol. I.1, FM 15-XVI METAR

Dependencies (for infra-architect):
    pydantic >= 2.0

NOTE: This is a research-grade parser covering the most operationally relevant
fields. It does NOT implement the full FM 15-XVI grammar (remarks section,
obscuration layers, runway contamination groups, etc.). Unparsed tokens are
collected in `remarks` verbatim.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

# pydantic import — infra-architect must install pydantic>=2.0
from pydantic import BaseModel, field_validator, model_validator


class METARParseError(ValueError):
    """Raised when the METAR string cannot be parsed."""


class SkyCoverEnum(str, Enum):
    FEW = "FEW"
    SCT = "SCT"
    BKN = "BKN"
    OVC = "OVC"
    CLR = "CLR"
    SKC = "SKC"
    CAVOK = "CAVOK"
    NSC = "NSC"
    NCD = "NCD"
    VV = "VV"  # vertical visibility


class SkyLayer(BaseModel):
    cover: SkyCoverEnum
    height_ft: Optional[int] = None  # hundreds of feet AGL; None for CLR/SKC/CAVOK
    cloud_type: Optional[str] = None  # CB or TCU if present


class WindObservation(BaseModel):
    direction_deg: Optional[int] = None  # None if variable (VRB)
    variable: bool = False
    speed_kt: int
    gust_kt: Optional[int] = None
    unit: str = "KT"


class METARObservation(BaseModel):
    """
    Parsed METAR observation.

    Standard: WMO No. 306 Vol. I.1, FM 15-XVI METAR
    Reference: https://library.wmo.int/records/item/35713-manual-on-codes-volume-i-1
    """

    raw: str
    station_id: str
    observation_time: datetime  # UTC, reconstructed with current month/year
    auto: bool = False
    wind: Optional[WindObservation] = None
    visibility_m: Optional[int] = None  # in metres; 9999 = ≥10 km
    rvr: list[str] = []  # raw RVR group strings (R28L/1200FT etc.)
    weather: list[str] = []  # present weather descriptors (e.g. "-RA", "TS")
    sky: list[SkyLayer] = []
    temp_c: Optional[int] = None
    dewpoint_c: Optional[int] = None
    altimeter_inhg: Optional[float] = None  # QNH in inHg when Axxx.x present
    altimeter_hpa: Optional[int] = None  # QNH in hPa when Qxxxx present
    remarks: str = ""  # everything after RMK or unrecognised trailing tokens

    @field_validator("station_id")
    @classmethod
    def station_must_be_icao(cls, v: str) -> str:
        if not re.fullmatch(r"[A-Z]{4}", v):
            raise METARParseError(f"Station ID '{v}' does not look like an ICAO code")
        return v


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

_WIND_RE = re.compile(
    r"^(?P<dir>\d{3}|VRB)(?P<spd>\d{2,3})(?:G(?P<gst>\d{2,3}))?(?P<unit>KT|MPS|KMH)$"
)
_VIS_RE = re.compile(r"^(?P<vis>\d{4}|9999|CAVOK)$")
_VIS_SM_RE = re.compile(r"^(?P<num>M?(?:\d+\s+)?\d+/\d+|\d+)SM$")
_RVR_RE = re.compile(r"^R\d{2}[LRC]?/")
_WEATHER_RE = re.compile(
    r"^(?P<int>[-+]|VC)?(?P<desc>MI|BC|PR|DR|BL|SH|TS|FZ)?"
    r"(?P<phen>DZ|RA|SN|SG|IC|PL|GR|GS|UP|FG|BR|SA|DU|HZ|FU|VA|PO|SQ|FC|SS|DS|"+
    r"RASN|SHRASN|TSGR|TSRA|FZDZ|FZRA|FZFG)+$"
)
_SKY_RE = re.compile(
    r"^(?P<cov>FEW|SCT|BKN|OVC|VV)(?P<hgt>\d{3})(?P<type>CB|TCU)?$"
)
_CLR_RE = re.compile(r"^(CLR|SKC|NSC|NCD|CAVOK)$")
_TEMP_RE = re.compile(r"^(?P<t>M?\d{2})/(?P<d>M?\d{2})$")
_ALTQ_RE = re.compile(r"^Q(?P<hpa>\d{4})$")
_ALTA_RE = re.compile(r"^A(?P<in>\d{4})$")
_TIME_RE = re.compile(r"^(?P<dd>\d{2})(?P<hh>\d{2})(?P<mm>\d{2})Z$")


def _parse_temp(s: str) -> int:
    return -int(s[1:]) if s.startswith("M") else int(s)


def _mps_to_kt(v: int) -> int:
    return round(v * 1.94384)


def parse_metar(raw: str) -> METARObservation:
    """
    Parse a METAR string and return a METARObservation.

    Standard: WMO No. 306 Vol. I.1, FM 15-XVI METAR
    Reference: https://library.wmo.int/records/item/35713-manual-on-codes-volume-i-1

    Raises METARParseError on any parsing failure.
    CLAUDE.md §8.1: no silent failure — every error surfaces explicitly.
    """
    raw = raw.strip()
    tokens = raw.split()
    if len(tokens) < 3:
        raise METARParseError(f"Too few tokens to be a valid METAR: {raw!r}")

    idx = 0

    # Optional METAR/SPECI type identifier
    if tokens[idx] in ("METAR", "SPECI"):
        idx += 1

    # Station identifier
    if idx >= len(tokens):
        raise METARParseError("Missing station identifier")
    station = tokens[idx]
    if not re.fullmatch(r"[A-Z]{4}", station):
        raise METARParseError(f"Expected ICAO station ID, got '{station}'")
    idx += 1

    # Date/time group
    if idx >= len(tokens):
        raise METARParseError("Missing date/time group")
    tm = _TIME_RE.match(tokens[idx])
    if not tm:
        raise METARParseError(f"Cannot parse date/time group '{tokens[idx]}'")
    day = int(tm.group("dd"))
    hour = int(tm.group("hh"))
    minute = int(tm.group("mm"))
    # Use current UTC year/month; day from METAR
    now = datetime.now(timezone.utc)
    try:
        obs_time = datetime(now.year, now.month, day, hour, minute, tzinfo=timezone.utc)
    except ValueError as exc:
        raise METARParseError(f"Invalid date/time group: {exc}") from exc
    idx += 1

    # AUTO / COR flags
    auto = False
    if idx < len(tokens) and tokens[idx] in ("AUTO", "COR"):
        auto = tokens[idx] == "AUTO"
        idx += 1

    wind: Optional[WindObservation] = None
    visibility_m: Optional[int] = None
    rvr: list[str] = []
    weather: list[str] = []
    sky: list[SkyLayer] = []
    temp_c: Optional[int] = None
    dewpoint_c: Optional[int] = None
    altimeter_inhg: Optional[float] = None
    altimeter_hpa: Optional[int] = None
    remarks_tokens: list[str] = []

    in_remarks = False

    while idx < len(tokens):
        tok = tokens[idx]

        if tok == "RMK":
            in_remarks = True
            idx += 1
            continue

        if in_remarks:
            remarks_tokens.append(tok)
            idx += 1
            continue

        # Wind
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
            direction = None if variable else int(dir_s)
            wind = WindObservation(
                direction_deg=direction,
                variable=variable,
                speed_kt=spd,
                gust_kt=gst,
                unit=unit,
            )
            idx += 1
            # optional variable direction suffix e.g. 350V040
            if idx < len(tokens) and re.fullmatch(r"\d{3}V\d{3}", tokens[idx]):
                idx += 1  # consume but don't store in this model
            continue

        # CAVOK — implies vis ≥10 km, no cloud below 5000 ft, no wx
        if tok == "CAVOK":
            visibility_m = 9999
            sky.append(SkyLayer(cover=SkyCoverEnum.CAVOK))
            idx += 1
            continue

        # Visibility (metres)
        vm = _VIS_RE.match(tok)
        if vm and visibility_m is None and tok != "CAVOK":
            visibility_m = 9999 if tok == "9999" else int(tok)
            idx += 1
            # optional direction suffix (e.g. 0800NE) — consume
            if idx < len(tokens) and re.fullmatch(r"[A-Z]{1,2}", tokens[idx]):
                idx += 1
            continue

        # Visibility (statute miles — US format)
        vsm = _VIS_SM_RE.match(tok)
        if vsm and visibility_m is None:
            # Convert SM to metres: 1 SM = 1609.344 m
            raw_num = vsm.group("num").replace("M", "").strip()
            try:
                if "/" in raw_num:
                    parts = raw_num.split()
                    if len(parts) == 2:
                        whole, frac = parts
                        n, d = frac.split("/")
                        val = int(whole) + int(n) / int(d)
                    else:
                        n, d = raw_num.split("/")
                        val = int(n) / int(d)
                else:
                    val = float(raw_num)
                visibility_m = round(val * 1609.344)
            except (ValueError, ZeroDivisionError) as exc:
                raise METARParseError(f"Cannot parse visibility '{tok}': {exc}") from exc
            idx += 1
            continue

        # RVR
        if _RVR_RE.match(tok):
            rvr.append(tok)
            idx += 1
            continue

        # Present weather
        if _WEATHER_RE.match(tok):
            weather.append(tok)
            idx += 1
            continue

        # Sky condition (CLR / SKC / NSC / NCD)
        clrm = _CLR_RE.match(tok)
        if clrm:
            sky.append(SkyLayer(cover=SkyCoverEnum(tok if tok != "CAVOK" else "CAVOK")))
            idx += 1
            continue

        # Sky layers (FEW/SCT/BKN/OVC/VV + height)
        sm = _SKY_RE.match(tok)
        if sm:
            height_ft = int(sm.group("hgt")) * 100
            ct = sm.group("type")
            sky.append(
                SkyLayer(
                    cover=SkyCoverEnum(sm.group("cov")),
                    height_ft=height_ft,
                    cloud_type=ct,
                )
            )
            idx += 1
            continue

        # Temperature / dewpoint
        tmm = _TEMP_RE.match(tok)
        if tmm:
            temp_c = _parse_temp(tmm.group("t"))
            dewpoint_c = _parse_temp(tmm.group("d"))
            idx += 1
            continue

        # Altimeter QNH (hPa)
        aqm = _ALTQ_RE.match(tok)
        if aqm:
            altimeter_hpa = int(aqm.group("hpa"))
            idx += 1
            continue

        # Altimeter (inHg)
        aam = _ALTA_RE.match(tok)
        if aam:
            altimeter_inhg = int(aam.group("in")) / 100.0
            idx += 1
            continue

        # Anything else goes to remarks
        remarks_tokens.append(tok)
        idx += 1

    return METARObservation(
        raw=raw,
        station_id=station,
        observation_time=obs_time,
        auto=auto,
        wind=wind,
        visibility_m=visibility_m,
        rvr=rvr,
        weather=weather,
        sky=sky,
        temp_c=temp_c,
        dewpoint_c=dewpoint_c,
        altimeter_inhg=altimeter_inhg,
        altimeter_hpa=altimeter_hpa,
        remarks=" ".join(remarks_tokens),
    )
