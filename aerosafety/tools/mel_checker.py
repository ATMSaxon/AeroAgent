"""
MEL (Minimum Equipment List) checker.

*** MOCK IMPLEMENTATION — NOT REAL MEL DATA ***

This module is a STUB that exists to satisfy the tool registry interface.
It does NOT contain actual MEL data and MUST NOT be used for real
dispatch decisions.

WHY THIS IS A STUB:
    Real MEL data is:
    1. Aircraft-type-specific and operator-specific.
    2. Derived from the Master Minimum Equipment List (MMEL) approved by
       the aircraft certification authority (FAA, EASA, etc.).
    3. Customised per airline operations specifications (FAA OpSpecs).
    4. Proprietary — airlines do not publish their MELs publicly.
    5. Subject to continuous amendment; a static table would rapidly become stale.

    Citing standard: FAA Order 8900.1 Vol. 4, Chapter 4 — Minimum Equipment
    Lists and Configuration Deviation Lists.
    Reference: https://fsims.faa.gov/wdocs/8900.1/v04%20ac%20equipment%20&%20authorization/chapter%2004/04_004_001.htm

    ICAO Doc 9760 — Airworthiness Manual §4.2 also addresses MEL frameworks.
    Reference: https://www.icao.int/safety/airnavigation/Pages/MEL.aspx

HONEST LIMITATION:
    Any tool claiming to enforce MEL rules without operator-specific,
    FAA/EASA-approved MEL data is providing false safety assurance.
    CLAUDE.md §1.2 prohibits fake implementations disguised as real ones.

Dependencies (for infra-architect):
    pydantic >= 2.0
"""

from __future__ import annotations

from pydantic import BaseModel


class MELCheckResult(BaseModel):
    """
    Result of a MEL check query.

    MOCK IMPLEMENTATION — see module docstring.
    """
    aircraft_type: str
    system_or_item: str
    status: str = "UNKNOWN"
    message: str
    mock: bool = True
    action_required: str = "CONSULT AIRCRAFT MEL"
    source: str = (
        "MOCK IMPLEMENTATION — real MEL is aircraft-type-specific and proprietary. "
        "Consult: FAA Order 8900.1 Vol. 4 Ch. 4 / ICAO Doc 9760 §4.2 / "
        "operator-specific FAA-approved MEL."
    )


def check_mel(aircraft_type: str, system_or_item: str) -> MELCheckResult:
    """
    *** MOCK IMPLEMENTATION — returns a placeholder result only ***

    Real MEL lookup is not implemented. This function exists to allow
    agents to call a MEL checker tool and receive an explicit stub
    response that directs them to the actual MEL.

    Args:
        aircraft_type:    ICAO type designator (e.g. "B738").
        system_or_item:   Free-text description of the inoperative system
                          or MEL item number (e.g. "28-00-01" or "fuel pump").

    Returns:
        MELCheckResult with mock=True and an explicit "CONSULT AIRCRAFT MEL"
        directive. The result status is always "UNKNOWN" from this stub.

    SAFETY WARNING:
        This result MUST NOT be used to authorise dispatch. The calling
        agent MUST surface the mock=True flag and escalate to a qualified
        dispatcher and the operator's approved MEL.

    Standard (for real MEL):
        FAA Order 8900.1 Vol. 4, Chapter 4
        Reference: https://fsims.faa.gov/wdocs/8900.1/v04%20ac%20equipment%20&%20authorization/chapter%2004/04_004_001.htm
    """
    if not aircraft_type:
        raise ValueError("aircraft_type must not be empty")
    if not system_or_item:
        raise ValueError("system_or_item must not be empty")

    return MELCheckResult(
        aircraft_type=aircraft_type.strip().upper(),
        system_or_item=system_or_item.strip(),
        status="UNKNOWN",
        message=(
            f"MOCK IMPLEMENTATION: MEL status for '{system_or_item}' on "
            f"'{aircraft_type}' cannot be determined automatically. "
            "Real MEL data is aircraft-type-specific, operator-specific, and "
            "proprietary. This stub MUST NOT be used for dispatch decisions."
        ),
        action_required=(
            "CONSULT THE OPERATOR'S FAA/EASA-APPROVED MINIMUM EQUIPMENT LIST (MEL) "
            "AND QUALIFIED MAINTENANCE/DISPATCH PERSONNEL."
        ),
    )
