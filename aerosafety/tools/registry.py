"""
Tool registry with JSON-schema descriptors for agent introspection.

Compatible with OpenAI function-calling schema and Anthropic tool-use schema.
Reference (OpenAI):   https://platform.openai.com/docs/guides/function-calling
Reference (Anthropic): https://docs.anthropic.com/en/docs/tool-use

Each tool descriptor follows the format:
{
  "name": str,
  "description": str,
  "parameters": { ...JSON Schema object... },
  "returns": { ...JSON Schema object... },
  "standard": str,           # cited aviation standard
  "mock": bool,              # True if this is a stub implementation
}

Dependencies (for infra-architect):
    pydantic >= 2.0
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ToolDescriptor(BaseModel):
    """JSON-schema descriptor for a single tool."""
    name: str
    description: str
    parameters: dict[str, Any]
    returns: dict[str, Any]
    standard: str
    mock: bool = False


# ---------------------------------------------------------------------------
# Tool descriptors
# ---------------------------------------------------------------------------

_TOOLS: list[ToolDescriptor] = [
    ToolDescriptor(
        name="parse_metar",
        description=(
            "Parse a raw METAR string conforming to WMO FM 15-XVI. "
            "Returns structured METARObservation with wind, visibility, sky, "
            "temperature, dewpoint, and altimeter. "
            "Raises METARParseError on malformed input."
        ),
        parameters={
            "type": "object",
            "properties": {
                "raw": {
                    "type": "string",
                    "description": "Raw METAR string, e.g. 'METAR KLAX 101953Z 27015KT ...'",
                },
            },
            "required": ["raw"],
        },
        returns={
            "type": "object",
            "description": "METARObservation pydantic model serialised as JSON",
            "properties": {
                "station_id": {"type": "string"},
                "observation_time": {"type": "string", "format": "date-time"},
                "auto": {"type": "boolean"},
                "wind": {"type": ["object", "null"]},
                "visibility_m": {"type": ["integer", "null"]},
                "weather": {"type": "array", "items": {"type": "string"}},
                "sky": {"type": "array"},
                "temp_c": {"type": ["integer", "null"]},
                "dewpoint_c": {"type": ["integer", "null"]},
                "altimeter_inhg": {"type": ["number", "null"]},
                "altimeter_hpa": {"type": ["integer", "null"]},
            },
        },
        standard="WMO No. 306 Vol. I.1, FM 15-XVI METAR — https://library.wmo.int/records/item/35713",
    ),
    ToolDescriptor(
        name="parse_taf",
        description=(
            "Parse a raw TAF string conforming to WMO FM 51-XVI. "
            "Returns structured TAFObservation including validity period, "
            "base conditions, and FM/BECMG/TEMPO/PROB change groups. "
            "Raises TAFParseError on malformed input."
        ),
        parameters={
            "type": "object",
            "properties": {
                "raw": {
                    "type": "string",
                    "description": "Raw TAF string",
                },
            },
            "required": ["raw"],
        },
        returns={
            "type": "object",
            "description": "TAFObservation pydantic model serialised as JSON",
            "properties": {
                "station_id": {"type": "string"},
                "issue_time": {"type": "string", "format": "date-time"},
                "valid_from": {"type": "string", "format": "date-time"},
                "valid_to": {"type": "string", "format": "date-time"},
                "base_conditions": {"type": "object"},
                "change_groups": {"type": "array"},
            },
        },
        standard="WMO No. 306 Vol. I.1, FM 51-XVI TAF — https://library.wmo.int/records/item/35713",
    ),
    ToolDescriptor(
        name="calculate_wind_components",
        description=(
            "Decompose wind into headwind, crosswind, and tailwind components "
            "relative to a runway heading. All angles must be in the same "
            "magnetic/true reference. Returns headwind_kt (positive=headwind, "
            "negative=tailwind), crosswind_kt (positive=from right, negative=from left), "
            "and tailwind_kt (convenience, always ≥ 0). "
            "Raises WindComponentError on out-of-range input."
        ),
        parameters={
            "type": "object",
            "properties": {
                "wind_direction_deg": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 359,
                    "description": "Direction FROM which the wind blows (magnetic degrees)",
                },
                "wind_speed_kt": {
                    "type": "number",
                    "minimum": 0,
                    "description": "Wind speed in knots",
                },
                "runway_heading_deg": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 359,
                    "description": "Runway magnetic heading",
                },
            },
            "required": ["wind_direction_deg", "wind_speed_kt", "runway_heading_deg"],
        },
        returns={
            "type": "object",
            "properties": {
                "headwind_kt": {"type": "number"},
                "crosswind_kt": {"type": "number"},
                "tailwind_kt": {"type": "number"},
                "angle_deg": {"type": "number"},
            },
        },
        standard="FAA-H-8083-25C Chapter 5 — https://www.faa.gov/regulations_policies/handbooks_manuals/aviation/phak",
    ),
    ToolDescriptor(
        name="parse_notam",
        description=(
            "Parse an ICAO-format NOTAM string. "
            "Extracts Q-line (FIR, NOTAM code, scope), A/B/C/D/E/F/G fields, "
            "effective UTC window, and affected runway/taxiway identifiers. "
            "Raises NOTAMParseError on malformed input."
        ),
        parameters={
            "type": "object",
            "properties": {
                "raw": {
                    "type": "string",
                    "description": "Raw ICAO NOTAM string",
                },
            },
            "required": ["raw"],
        },
        returns={
            "type": "object",
            "properties": {
                "series": {"type": "string"},
                "number": {"type": "string"},
                "location": {"type": "string"},
                "effective_from": {"type": ["string", "null"], "format": "date-time"},
                "effective_to": {"type": ["string", "null"], "format": "date-time"},
                "permanent": {"type": "boolean"},
                "text": {"type": "string"},
                "affected_runways": {"type": "array", "items": {"type": "string"}},
                "affected_taxiways": {"type": "array", "items": {"type": "string"}},
            },
        },
        standard=(
            "ICAO Annex 15, 16th ed., 2018 — https://www.icao.int/safety/information-management/Pages/Annex15.aspx; "
            "FAA Order JO 7930.2S — https://www.faa.gov/regulations_policies/orders_notices"
        ),
    ),
    ToolDescriptor(
        name="check_time_window",
        description=(
            "Determine whether a UTC datetime falls within an active time window "
            "(e.g. NOTAM effective period, TAF validity). "
            "Returns ACTIVE / INACTIVE / EXPIRED / PERMANENT. "
            "Raises AmbiguousTimezoneError if any datetime is naive or non-UTC."
        ),
        parameters={
            "type": "object",
            "properties": {
                "query_time": {
                    "type": "string",
                    "format": "date-time",
                    "description": "UTC datetime to check (must be timezone-aware ISO 8601)",
                },
                "window_start": {
                    "type": "string",
                    "format": "date-time",
                    "description": "UTC start of the active window",
                },
                "window_end": {
                    "type": ["string", "null"],
                    "format": "date-time",
                    "description": "UTC end of the active window, or null for PERMANENT",
                },
            },
            "required": ["query_time", "window_start"],
        },
        returns={
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["ACTIVE", "INACTIVE", "EXPIRED", "PERMANENT"],
                },
                "seconds_until_start": {"type": ["number", "null"]},
                "seconds_until_end": {"type": ["number", "null"]},
            },
        },
        standard="ICAO Annex 15, 16th ed., 2018 §3.6 — https://www.icao.int/safety/information-management/Pages/Annex15.aspx",
    ),
    ToolDescriptor(
        name="calculate_horizontal_separation",
        description=(
            "Compute great-circle horizontal separation between two WGS-84 positions "
            "using the haversine formula. Returns distance in nautical miles and km. "
            "Raises SeparationError on out-of-range coordinates."
        ),
        parameters={
            "type": "object",
            "properties": {
                "lat1_deg": {"type": "number", "minimum": -90, "maximum": 90},
                "lon1_deg": {"type": "number", "minimum": -180, "maximum": 180},
                "lat2_deg": {"type": "number", "minimum": -90, "maximum": 90},
                "lon2_deg": {"type": "number", "minimum": -180, "maximum": 180},
            },
            "required": ["lat1_deg", "lon1_deg", "lat2_deg", "lon2_deg"],
        },
        returns={
            "type": "object",
            "properties": {
                "distance_nm": {"type": "number"},
                "distance_km": {"type": "number"},
            },
        },
        standard="FAA Order JO 7110.65Z — https://www.faa.gov/air_traffic/publications/atpubs/atc_html/",
    ),
    ToolDescriptor(
        name="calculate_vertical_separation",
        description=(
            "Compute vertical separation between two altitudes in feet (MSL). "
            "Returns absolute separation. Raises SeparationError on implausible altitudes."
        ),
        parameters={
            "type": "object",
            "properties": {
                "altitude1_ft": {"type": "number", "description": "Altitude 1 in feet MSL"},
                "altitude2_ft": {"type": "number", "description": "Altitude 2 in feet MSL"},
            },
            "required": ["altitude1_ft", "altitude2_ft"],
        },
        returns={
            "type": "object",
            "properties": {
                "separation_ft": {"type": "number"},
            },
        },
        standard="FAA Order JO 7110.65Z Chapter 5 §5-5-1 — https://www.faa.gov/air_traffic/publications/atpubs/atc_html/",
    ),
    ToolDescriptor(
        name="get_wake_category",
        description=(
            "Return the ICAO legacy wake turbulence category (L/M/H/J) for a given "
            "ICAO aircraft type designator per ICAO Doc 8643. "
            "Raises UnknownAircraftTypeError if the type is not in the "
            "citation-verified table — callers MUST handle this exception."
        ),
        parameters={
            "type": "object",
            "properties": {
                "icao_type": {
                    "type": "string",
                    "description": "ICAO aircraft type designator, e.g. 'B738', 'A320'",
                },
            },
            "required": ["icao_type"],
        },
        returns={
            "type": "object",
            "properties": {
                "icao_type": {"type": "string"},
                "wake_category": {"type": "string", "enum": ["L", "M", "H", "J"]},
                "description": {"type": "string"},
                "source": {"type": "string"},
            },
        },
        standard="ICAO Doc 8643 Aircraft Type Designators — https://www.icao.int/safety/vleap/Pages/Doc-8643.aspx",
    ),
    ToolDescriptor(
        name="check_mel",
        description=(
            "*** MOCK IMPLEMENTATION — NOT REAL MEL DATA *** "
            "Stub MEL checker that returns a 'CONSULT AIRCRAFT MEL' placeholder. "
            "Real MEL data is aircraft-type-specific and proprietary. "
            "The result always has mock=True and status='UNKNOWN'. "
            "MUST NOT be used for real dispatch decisions."
        ),
        parameters={
            "type": "object",
            "properties": {
                "aircraft_type": {
                    "type": "string",
                    "description": "ICAO type designator",
                },
                "system_or_item": {
                    "type": "string",
                    "description": "Inoperative system or MEL item number",
                },
            },
            "required": ["aircraft_type", "system_or_item"],
        },
        returns={
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["UNKNOWN"]},
                "mock": {"type": "boolean", "const": True},
                "action_required": {"type": "string"},
            },
        },
        standard="FAA Order 8900.1 Vol. 4 Ch. 4 — https://fsims.faa.gov/wdocs/8900.1/",
        mock=True,
    ),
    ToolDescriptor(
        name="check_weather_minima",
        description=(
            "Check whether observed METAR conditions meet ILS approach minima "
            "for CAT I / CAT II / CAT III-A / CAT III-B / CAT III-C. "
            "Uses FAA AIM §5-4-7 generic baseline minimums. "
            "Returns GO / MARGINAL / NO_GO with explanation. "
            "Verify against published IAP for specific airport/runway."
        ),
        parameters={
            "type": "object",
            "properties": {
                "metar": {
                    "type": "object",
                    "description": "METARObservation object from parse_metar",
                },
                "approach_category": {
                    "type": "string",
                    "enum": ["CAT_I", "CAT_II", "CAT_III_A", "CAT_III_B", "CAT_III_C"],
                },
            },
            "required": ["metar", "approach_category"],
        },
        returns={
            "type": "object",
            "properties": {
                "decision": {"type": "string", "enum": ["GO", "MARGINAL", "NO_GO"]},
                "limiting_factor": {"type": "string"},
                "ceiling_ok": {"type": ["boolean", "null"]},
                "visibility_ok": {"type": ["boolean", "null"]},
                "disclaimer": {"type": "string"},
            },
        },
        standard="FAA AIM §5-4-7 — https://www.faa.gov/air_traffic/publications/atpubs/aim_html/",
    ),
]


# ---------------------------------------------------------------------------
# Registry interface
# ---------------------------------------------------------------------------

def list_tools() -> list[ToolDescriptor]:
    """Return all registered tool descriptors."""
    return list(_TOOLS)


def get_tool(name: str) -> ToolDescriptor:
    """
    Return the descriptor for a named tool.

    Raises KeyError if the tool name is not found.
    """
    for t in _TOOLS:
        if t.name == name:
            return t
    raise KeyError(f"No tool named '{name}' in registry")


def to_openai_functions() -> list[dict]:
    """
    Export all tools as OpenAI function-calling format descriptors.

    Reference: https://platform.openai.com/docs/guides/function-calling
    """
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters,
            },
        }
        for t in _TOOLS
    ]


def to_anthropic_tools() -> list[dict]:
    """
    Export all tools as Anthropic tool-use format descriptors.

    Reference: https://docs.anthropic.com/en/docs/tool-use
    """
    return [
        {
            "name": t.name,
            "description": t.description,
            "input_schema": t.parameters,
        }
        for t in _TOOLS
    ]
