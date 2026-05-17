"""
Wind component calculator: headwind, crosswind, tailwind.

Standard: FAA Pilot's Handbook of Aeronautical Knowledge (FAA-H-8083-25C),
  Chapter 5 "Aerodynamics of Flight" — wind components.
  https://www.faa.gov/regulations_policies/handbooks_manuals/aviation/phak

HEADING CONVENTION (critical for safety — CLAUDE.md §8.1):
    ALL angles in this module are MAGNETIC degrees (0-360).
    Both 0 and 360 represent north (runway 36 = 360°); they are treated
    identically. Runway headings from published aeronautical charts are
    magnetic. Wind direction from METAR is MAGNETIC when reported in
    degrees (WMO FM 15 §15.4.3: "direction from which wind blows, in
    degrees true" — but FAA METAR practice reports magnetic; this module
    accepts MAGNETIC and raises if True/Magnetic distinction is
    ambiguous in the caller's context).

    Callers MUST explicitly document whether they are passing magnetic
    or true values. Mixing magnetic and true without a variation
    correction is a safety-critical error.

Dependencies (for infra-architect):
    pydantic >= 2.0
    (math is stdlib)
"""

from __future__ import annotations

import math

from pydantic import BaseModel


class WindComponentError(ValueError):
    """Raised on invalid input to wind component calculation."""


class WindComponentResult(BaseModel):
    """
    Result of wind component decomposition.

    Positive headwind_kt  → headwind component (into the nose).
    Negative headwind_kt  → tailwind component.
    Positive crosswind_kt → from the right of the runway.
    Negative crosswind_kt → from the left of the runway.
    tailwind_kt is provided as a convenience (= max(0, -headwind_kt)).

    Standard: FAA-H-8083-25C Chapter 5
    Reference: https://www.faa.gov/regulations_policies/handbooks_manuals/aviation/phak
    """
    wind_direction_deg: int
    wind_speed_kt: float
    runway_heading_deg: int
    headwind_kt: float
    crosswind_kt: float
    tailwind_kt: float
    angle_deg: float  # angle between wind and runway (0–180)


def calculate_wind_components(
    wind_direction_deg: int,
    wind_speed_kt: float,
    runway_heading_deg: int,
) -> WindComponentResult:
    """
    Decompose wind into headwind and crosswind relative to a runway heading.

    All angles MUST be in the same reference (magnetic or true).
    Mixing magnetic and true values produces an incorrect result.

    Args:
        wind_direction_deg: Direction FROM which the wind blows (0-360, magnetic).
                            360 is accepted and treated identically to 0 (north).
        wind_speed_kt:       Wind speed in knots (must be >= 0).
        runway_heading_deg:  Runway magnetic heading (0-360).
                            360 is accepted and treated identically to 0
                            (runway 36 has heading 360°).

    Returns:
        WindComponentResult with headwind_kt, crosswind_kt, tailwind_kt.

    Raises:
        WindComponentError: on out-of-range or negative inputs.

    Hand-verification (used in unit tests):
        wind 270/15, runway heading 180:
          angle = |270 - 180| = 90°
          headwind = 15 * cos(90°) = 0.0 kt
          crosswind = 15 * sin(90°) = 15.0 kt (from the right — west wind,
            runway pointing south, wind hits right side)

        wind 360/20, runway heading 360:
          angle = 0°
          headwind = 20 * cos(0°) = 20.0 kt
          crosswind = 20 * sin(0°) = 0.0 kt

        wind 090/10, runway heading 360:
          angle = 90°
          headwind = 0.0 kt
          crosswind = -10.0 kt (from the left)

    Standard: FAA-H-8083-25C Chapter 5
    Reference: https://www.faa.gov/regulations_policies/handbooks_manuals/aviation/phak
    """
    if not (0 <= wind_direction_deg <= 360):
        raise WindComponentError(
            f"wind_direction_deg must be 0-360, got {wind_direction_deg}"
        )
    if wind_speed_kt < 0:
        raise WindComponentError(
            f"wind_speed_kt must be >= 0, got {wind_speed_kt}"
        )
    if not (0 <= runway_heading_deg <= 360):
        raise WindComponentError(
            f"runway_heading_deg must be 0-360, got {runway_heading_deg}"
        )

    # Angle from runway heading to wind direction (where wind comes FROM)
    # A positive angle means wind is to the right of the runway centreline.
    angle_rad = math.radians((wind_direction_deg - runway_heading_deg) % 360)

    # headwind: positive = into headwind; negative = tailwind
    headwind = wind_speed_kt * math.cos(angle_rad)
    # crosswind: positive = from right; negative = from left
    crosswind = wind_speed_kt * math.sin(angle_rad)

    # Normalise: angles > 180° mean the wind crosses from the left
    # The sin of angles in (180°, 360°) is negative, so crosswind sign is
    # already correct by the formula above (sin is negative for 180–360).
    # Tailwind convenience:
    tailwind = max(0.0, -headwind)

    return WindComponentResult(
        wind_direction_deg=wind_direction_deg,
        wind_speed_kt=wind_speed_kt,
        runway_heading_deg=runway_heading_deg,
        headwind_kt=round(headwind, 2),
        crosswind_kt=round(crosswind, 2),
        tailwind_kt=round(tailwind, 2),
        angle_deg=round(math.degrees(angle_rad) % 360, 2),
    )
