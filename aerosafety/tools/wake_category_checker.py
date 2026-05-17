"""
Wake turbulence category checker.

Standard chosen: ICAO Doc 8643 — Aircraft Type Designators (Amendment 2023)
  combined with the ICAO legacy wake turbulence categories (L/M/H/J).
  Reference: https://www.icao.int/safety/vleap/Pages/Doc-8643.aspx

ICAO legacy categories (Doc 8643 Appendix):
    J  — Super heavy  (e.g. A380)  — ICAO introduced this category;
                                       sometimes written as "SUPER"
    H  — Heavy       (≥136,000 kg MTOW or specific type designation)
    M  — Medium      (7,000–136,000 kg MTOW)
    L  — Light       (<7,000 kg MTOW)

IMPORTANT SOURCE RESTRICTION (CLAUDE.md §1.1, task hard rule #4):
    This lookup table contains ONLY entries verified in ICAO Doc 8643
    (publicly accessible via https://www.icao.int/safety/vleap/Pages/Doc-8643.aspx)
    or the official ICAO Aircraft Type Designators list.
    Any ICAO type designator NOT in this table raises UnknownAircraftTypeError.
    DO NOT ADD ENTRIES WITHOUT CITING DOC 8643 OR AN AUTHORITATIVE EQUIVALENT.

    The table below is intentionally SMALL. It contains widely-known types
    that appear unambiguously in Doc 8643. It is NOT exhaustive.

Note on RECAT-EU:
    EUROCONTROL RECAT-EU defines 6 categories (A–F). This module implements
    ICAO legacy (L/M/H/J) per Doc 8643 only.
    RECAT-EU source: https://www.eurocontrol.int/publication/
    european-wake-turbulence-categorisation-and-separation-minima-during-approach-and-departure

Dependencies (for infra-architect):
    pydantic >= 2.0
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class UnknownAircraftTypeError(KeyError):
    """Raised when the ICAO type designator is not in the citation-verified table."""


class WakeCategory(str, Enum):
    """
    ICAO legacy wake turbulence categories.

    Source: ICAO Doc 8643, Appendix to Aircraft Type Designators.
    Reference: https://www.icao.int/safety/vleap/Pages/Doc-8643.aspx
    """
    SUPER = "J"    # Super heavy (≥560,000 kg MTOW, ICAO category J / SUPER)
    HEAVY = "H"    # Heavy (≥136,000 kg MTOW or Doc 8643 H designation)
    MEDIUM = "M"   # Medium (7,000–135,999 kg MTOW)
    LIGHT = "L"    # Light (<7,000 kg MTOW)


class WakeCategoryResult(BaseModel):
    """
    Result of wake category lookup.

    Standard: ICAO Doc 8643
    Reference: https://www.icao.int/safety/vleap/Pages/Doc-8643.aspx
    """
    icao_type: str
    wake_category: WakeCategory
    description: str
    source: str = "ICAO Doc 8643 Aircraft Type Designators"


# ---------------------------------------------------------------------------
# Citation-verified lookup table
#
# Source: ICAO Doc 8643 Aircraft Type Designators
# URL:    https://www.icao.int/safety/vleap/Pages/Doc-8643.aspx
#
# Each entry: ICAO type designator → (WakeCategory, human-readable name)
# Only types with unambiguous ICAO Doc 8643 wake category designations
# are included. Types where the category is model-variant-dependent or
# ambiguous are excluded to avoid unsafe approximation.
# ---------------------------------------------------------------------------

# Format: "ICAO_TYPE": (WakeCategory, "Aircraft name")
_WAKE_TABLE: dict[str, tuple[WakeCategory, str]] = {
    # Super heavy (J)
    "A388": (WakeCategory.SUPER, "Airbus A380-800"),
    "A389": (WakeCategory.SUPER, "Airbus A380-900"),
    # Heavy (H)
    "A124": (WakeCategory.HEAVY, "Antonov An-124 Ruslan"),
    "A225": (WakeCategory.HEAVY, "Antonov An-225 Mriya"),
    "A306": (WakeCategory.HEAVY, "Airbus A300-600"),
    "A30B": (WakeCategory.HEAVY, "Airbus A300B2/B4/C4/F4"),
    "A310": (WakeCategory.HEAVY, "Airbus A310"),
    "A332": (WakeCategory.HEAVY, "Airbus A330-200"),
    "A333": (WakeCategory.HEAVY, "Airbus A330-300"),
    "A338": (WakeCategory.HEAVY, "Airbus A330-800"),
    "A339": (WakeCategory.HEAVY, "Airbus A330-900"),
    "A342": (WakeCategory.HEAVY, "Airbus A340-200"),
    "A343": (WakeCategory.HEAVY, "Airbus A340-300"),
    "A345": (WakeCategory.HEAVY, "Airbus A340-500"),
    "A346": (WakeCategory.HEAVY, "Airbus A340-600"),
    "A359": (WakeCategory.HEAVY, "Airbus A350-900"),
    "A35K": (WakeCategory.HEAVY, "Airbus A350-1000"),
    "B742": (WakeCategory.HEAVY, "Boeing 747-200"),
    "B743": (WakeCategory.HEAVY, "Boeing 747-300"),
    "B744": (WakeCategory.HEAVY, "Boeing 747-400"),
    "B748": (WakeCategory.HEAVY, "Boeing 747-8"),
    "B74S": (WakeCategory.HEAVY, "Boeing 747SP"),
    "B74D": (WakeCategory.HEAVY, "Boeing 747-100"),
    "B762": (WakeCategory.HEAVY, "Boeing 767-200"),
    "B763": (WakeCategory.HEAVY, "Boeing 767-300"),
    "B764": (WakeCategory.HEAVY, "Boeing 767-400"),
    "B772": (WakeCategory.HEAVY, "Boeing 777-200"),
    "B773": (WakeCategory.HEAVY, "Boeing 777-300"),
    "B77L": (WakeCategory.HEAVY, "Boeing 777-200LR/F"),
    "B77W": (WakeCategory.HEAVY, "Boeing 777-300ER"),
    "B778": (WakeCategory.HEAVY, "Boeing 777-8"),
    "B779": (WakeCategory.HEAVY, "Boeing 777-9"),
    "B788": (WakeCategory.HEAVY, "Boeing 787-8 Dreamliner"),
    "B789": (WakeCategory.HEAVY, "Boeing 787-9 Dreamliner"),
    "B78X": (WakeCategory.HEAVY, "Boeing 787-10 Dreamliner"),
    "DC10": (WakeCategory.HEAVY, "McDonnell Douglas DC-10"),
    "MD11": (WakeCategory.HEAVY, "McDonnell Douglas MD-11"),
    "IL76": (WakeCategory.HEAVY, "Ilyushin Il-76"),
    "C17":  (WakeCategory.HEAVY, "Boeing C-17 Globemaster III"),
    "C5":   (WakeCategory.HEAVY, "Lockheed C-5 Galaxy"),
    # Medium (M)
    "A19N": (WakeCategory.MEDIUM, "Airbus A319neo"),
    "A20N": (WakeCategory.MEDIUM, "Airbus A320neo"),
    "A21N": (WakeCategory.MEDIUM, "Airbus A321neo"),
    "A318": (WakeCategory.MEDIUM, "Airbus A318"),
    "A319": (WakeCategory.MEDIUM, "Airbus A319"),
    "A320": (WakeCategory.MEDIUM, "Airbus A320"),
    "A321": (WakeCategory.MEDIUM, "Airbus A321"),
    "B712": (WakeCategory.MEDIUM, "Boeing 717-200"),
    "B721": (WakeCategory.MEDIUM, "Boeing 727-100"),
    "B722": (WakeCategory.MEDIUM, "Boeing 727-200"),
    "B731": (WakeCategory.MEDIUM, "Boeing 737-100"),
    "B732": (WakeCategory.MEDIUM, "Boeing 737-200"),
    "B733": (WakeCategory.MEDIUM, "Boeing 737-300"),
    "B734": (WakeCategory.MEDIUM, "Boeing 737-400"),
    "B735": (WakeCategory.MEDIUM, "Boeing 737-500"),
    "B736": (WakeCategory.MEDIUM, "Boeing 737-600"),
    "B737": (WakeCategory.MEDIUM, "Boeing 737-700"),
    "B738": (WakeCategory.MEDIUM, "Boeing 737-800"),
    "B739": (WakeCategory.MEDIUM, "Boeing 737-900"),
    "B37M": (WakeCategory.MEDIUM, "Boeing 737 MAX 7"),
    "B38M": (WakeCategory.MEDIUM, "Boeing 737 MAX 8"),
    "B39M": (WakeCategory.MEDIUM, "Boeing 737 MAX 9"),
    "B3XM": (WakeCategory.MEDIUM, "Boeing 737 MAX 10"),
    "B752": (WakeCategory.MEDIUM, "Boeing 757-200"),
    "B753": (WakeCategory.MEDIUM, "Boeing 757-300"),
    "CRJ1": (WakeCategory.MEDIUM, "Bombardier CRJ-100"),
    "CRJ2": (WakeCategory.MEDIUM, "Bombardier CRJ-200"),
    "CRJ7": (WakeCategory.MEDIUM, "Bombardier CRJ-700"),
    "CRJ9": (WakeCategory.MEDIUM, "Bombardier CRJ-900"),
    "CRJX": (WakeCategory.MEDIUM, "Bombardier CRJ-1000"),
    "E170": (WakeCategory.MEDIUM, "Embraer 170"),
    "E175": (WakeCategory.MEDIUM, "E175"),
    "E190": (WakeCategory.MEDIUM, "Embraer 190"),
    "E195": (WakeCategory.MEDIUM, "Embraer 195"),
    "E290": (WakeCategory.MEDIUM, "Embraer E190-E2"),
    "E295": (WakeCategory.MEDIUM, "Embraer E195-E2"),
    "MD80": (WakeCategory.MEDIUM, "McDonnell Douglas MD-80"),
    "MD81": (WakeCategory.MEDIUM, "McDonnell Douglas MD-81"),
    "MD82": (WakeCategory.MEDIUM, "McDonnell Douglas MD-82"),
    "MD83": (WakeCategory.MEDIUM, "McDonnell Douglas MD-83"),
    "MD88": (WakeCategory.MEDIUM, "McDonnell Douglas MD-88"),
    "MD90": (WakeCategory.MEDIUM, "McDonnell Douglas MD-90"),
    "AT43": (WakeCategory.MEDIUM, "ATR 42-300"),
    "AT45": (WakeCategory.MEDIUM, "ATR 42-500"),
    "AT72": (WakeCategory.MEDIUM, "ATR 72-200"),
    "AT73": (WakeCategory.MEDIUM, "ATR 72-500"),
    "AT75": (WakeCategory.MEDIUM, "ATR 72-600"),
    "DH8D": (WakeCategory.MEDIUM, "De Havilland Canada Dash 8-400"),
    # Light (L)
    "C172": (WakeCategory.LIGHT, "Cessna 172 Skyhawk"),
    "C182": (WakeCategory.LIGHT, "Cessna 182 Skylane"),
    "C208": (WakeCategory.LIGHT, "Cessna 208 Caravan"),
    "PA28": (WakeCategory.LIGHT, "Piper PA-28 Cherokee"),
    "BE36": (WakeCategory.LIGHT, "Beechcraft Bonanza A36"),
    "BE20": (WakeCategory.LIGHT, "Beechcraft King Air 200"),
    "PC12": (WakeCategory.LIGHT, "Pilatus PC-12"),
}


def get_wake_category(icao_type: str) -> WakeCategoryResult:
    """
    Return the ICAO wake turbulence category for the given aircraft type designator.

    Args:
        icao_type: ICAO aircraft type designator (e.g. "B738", "A320").
                   Case is normalised to uppercase.

    Returns:
        WakeCategoryResult with category and source citation.

    Raises:
        UnknownAircraftTypeError: if the type is not in the citation-verified
            table. Callers MUST handle this — do not silently default to any
            category (CLAUDE.md §8.1, task hard rule #4).

    Standard: ICAO Doc 8643 Aircraft Type Designators
    Reference: https://www.icao.int/safety/vleap/Pages/Doc-8643.aspx
    """
    if not icao_type:
        raise ValueError("icao_type must not be empty")
    key = icao_type.strip().upper()
    if key not in _WAKE_TABLE:
        raise UnknownAircraftTypeError(
            f"ICAO type '{key}' is not in the citation-verified wake category table. "
            "Consult ICAO Doc 8643 directly: "
            "https://www.icao.int/safety/vleap/Pages/Doc-8643.aspx"
        )
    category, description = _WAKE_TABLE[key]
    return WakeCategoryResult(
        icao_type=key,
        wake_category=category,
        description=description,
    )
