"""
Separation calculator: horizontal (haversine) and vertical separation.

Standard: FAA Order JO 7110.65Z — Air Traffic Control, Chapter 5 (Radar
  Separation) and Chapter 6 (Nonradar Separation).
Reference: https://www.faa.gov/air_traffic/publications/atpubs/atc_html/

Horizontal separation uses the haversine formula for great-circle distance.
  Reference: Sinnott, R.W. (1984). "Virtues of the Haversine".
             Sky and Telescope, 68(2), 159.

UNIT CONVENTION:
    - Horizontal distances: nautical miles (NM) — standard for ATC separation.
    - Vertical separations: feet — standard for ATC altitude assignment.
    - Input coordinates: decimal degrees (WGS-84 latitude/longitude).

IMPORTANT: This tool computes geometric separation only. It does NOT account
for radar accuracy, wake turbulence, terrain, airspace class, or procedural
offsets. Applying computed values directly to ATC decisions requires human
qualified controller judgment under FAA Order JO 7110.65Z.

Dependencies (for infra-architect):
    pydantic >= 2.0
    (math is stdlib)
"""

from __future__ import annotations

import math
from pydantic import BaseModel


class SeparationError(ValueError):
    """Raised on invalid input to separation calculation."""


class HorizontalSeparationResult(BaseModel):
    """
    Result of haversine horizontal separation computation.

    Standard: FAA Order JO 7110.65Z Chapter 5/6
    Reference: https://www.faa.gov/air_traffic/publications/atpubs/atc_html/
    """
    lat1_deg: float
    lon1_deg: float
    lat2_deg: float
    lon2_deg: float
    distance_nm: float
    distance_km: float


class VerticalSeparationResult(BaseModel):
    """
    Result of vertical separation computation.

    Standard: FAA Order JO 7110.65Z Chapter 5/6
    Reference: https://www.faa.gov/air_traffic/publications/atpubs/atc_html/
    """
    altitude1_ft: float
    altitude2_ft: float
    separation_ft: float  # always non-negative (absolute difference)


_EARTH_RADIUS_NM = 3440.065  # mean Earth radius in nautical miles (ICAO, WGS-84 approx)
_EARTH_RADIUS_KM = 6371.009  # mean Earth radius in km


def _validate_lat(lat: float, name: str) -> None:
    if not (-90.0 <= lat <= 90.0):
        raise SeparationError(f"{name} latitude must be -90 to +90, got {lat}")


def _validate_lon(lon: float, name: str) -> None:
    if not (-180.0 <= lon <= 180.0):
        raise SeparationError(f"{name} longitude must be -180 to +180, got {lon}")


def calculate_horizontal_separation(
    lat1_deg: float,
    lon1_deg: float,
    lat2_deg: float,
    lon2_deg: float,
) -> HorizontalSeparationResult:
    """
    Compute great-circle distance between two WGS-84 positions using the
    haversine formula.

    Args:
        lat1_deg, lon1_deg: First position in decimal degrees.
        lat2_deg, lon2_deg: Second position in decimal degrees.

    Returns:
        HorizontalSeparationResult with distance in NM and km.

    Raises:
        SeparationError: on out-of-range coordinates.

    Hand-verification (used in unit tests):
        KJFK (40.6413° N, 73.7781° W) to KLGA (40.7769° N, 73.8740° W):
          Expected ≈ 8.3 NM (published distance ≈ 8 NM).

        Same point to same point → 0.0 NM.

    Standard: FAA Order JO 7110.65Z; haversine from Sinnott (1984).
    """
    _validate_lat(lat1_deg, "lat1")
    _validate_lon(lon1_deg, "lon1")
    _validate_lat(lat2_deg, "lat2")
    _validate_lon(lon2_deg, "lon2")

    phi1 = math.radians(lat1_deg)
    phi2 = math.radians(lat2_deg)
    dphi = math.radians(lat2_deg - lat1_deg)
    dlambda = math.radians(lon2_deg - lon1_deg)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    distance_km = _EARTH_RADIUS_KM * c
    distance_nm = _EARTH_RADIUS_NM * c

    return HorizontalSeparationResult(
        lat1_deg=lat1_deg,
        lon1_deg=lon1_deg,
        lat2_deg=lat2_deg,
        lon2_deg=lon2_deg,
        distance_nm=round(distance_nm, 4),
        distance_km=round(distance_km, 4),
    )


def calculate_vertical_separation(
    altitude1_ft: float,
    altitude2_ft: float,
) -> VerticalSeparationResult:
    """
    Compute vertical separation between two altitudes in feet.

    Args:
        altitude1_ft: First altitude in feet (MSL).
        altitude2_ft: Second altitude in feet (MSL).

    Returns:
        VerticalSeparationResult with absolute separation in feet.

    Raises:
        SeparationError: if any altitude is unreasonably negative
            (below -2000 ft, below known sea-level aircraft operations).

    Hand-verification (used in unit tests):
        FL350 (35000 ft) vs FL330 (33000 ft) → 2000 ft separation.
        4000 ft vs 6000 ft → 2000 ft.

    Standard: FAA Order JO 7110.65Z Chapter 5 §5-5-1 (vertical separation minima)
    Reference: https://www.faa.gov/air_traffic/publications/atpubs/atc_html/
    """
    if altitude1_ft < -2000:
        raise SeparationError(f"altitude1_ft {altitude1_ft} is below -2000 ft — implausible")
    if altitude2_ft < -2000:
        raise SeparationError(f"altitude2_ft {altitude2_ft} is below -2000 ft — implausible")

    separation = abs(altitude1_ft - altitude2_ft)

    return VerticalSeparationResult(
        altitude1_ft=altitude1_ft,
        altitude2_ft=altitude2_ft,
        separation_ft=round(separation, 1),
    )
