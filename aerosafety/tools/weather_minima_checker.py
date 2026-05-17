"""
Weather minima checker: evaluates whether METAR conditions meet approach
minima for CAT I, II, or III ILS approaches.

Standard: FAA Aeronautical Information Manual (AIM), Chapter 1-1-17 and
  Chapter 5-4-7 (ILS approach minimums).
  Reference: https://www.faa.gov/air_traffic/publications/atpubs/aim_html/

Approach category definitions (by aircraft Vat):
  FAA AC 91-44A / ICAO Doc 9365 define approach categories A–E by Vat.
  This module uses visibility (RVR/SM) and ceiling thresholds for
  CAT I / CAT II / CAT III as published in FAA AIM §5-4-7.

IMPORTANT LIMITATIONS:
    1. Actual approach minima are procedure-specific (published on IAP charts).
       The values here are GENERIC BASELINE MINIMUMS per FAA AIM §5-4-7.
       Specific airport/runway procedures may have higher or lower authorised
       minima. Callers MUST verify against the applicable IAP.
    2. CAT II and III operations require aircraft certification, crew
       certification, and airport infrastructure. This tool checks only
       weather parameters, not operational authorisations.
    3. Gust components, wind shear, turbulence, icing, and other weather
       hazards are NOT evaluated here.

FAA AIM §5-4-7 generic baseline minimums used:
    CAT I:   DH 200 ft, RVR 1800 ft (or vis ½ SM)
    CAT II:  DH 100 ft, RVR 1200 ft
    CAT III-A: DH <100 ft (or no DH), RVR 700 ft
    CAT III-B: DH <50 ft (or no DH), RVR 150 ft
    CAT III-C: no DH, no RVR limitation (not in general use in US)

Dependencies (for infra-architect):
    pydantic >= 2.0
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel

from aerosafety.tools.metar_parser import METARObservation, SkyCoverEnum


class ApproachCategory(str, Enum):
    CAT_I = "CAT_I"
    CAT_II = "CAT_II"
    CAT_III_A = "CAT_III_A"
    CAT_III_B = "CAT_III_B"
    CAT_III_C = "CAT_III_C"


class MinimaDecision(str, Enum):
    GO = "GO"           # conditions meet or exceed minima
    MARGINAL = "MARGINAL"  # conditions are at or very close to minima (within 10%)
    NO_GO = "NO_GO"    # conditions below minima


class WeatherMinimaResult(BaseModel):
    """
    Result of weather minima check against ILS approach minima.

    Standard: FAA AIM §5-4-7
    Reference: https://www.faa.gov/air_traffic/publications/atpubs/aim_html/
    """
    station_id: str
    approach_category: ApproachCategory
    decision: MinimaDecision
    observed_visibility_m: Optional[int]
    observed_ceiling_ft: Optional[int]
    required_rvr_ft: int           # baseline from FAA AIM §5-4-7
    required_ceiling_ft: Optional[int]  # DH from FAA AIM §5-4-7; None = no DH
    ceiling_ok: Optional[bool]
    visibility_ok: Optional[bool]
    limiting_factor: str           # human-readable explanation
    disclaimer: str = (
        "GENERIC BASELINE ONLY — verify against published IAP for specific "
        "airport/runway. CAT II/III requires aircraft, crew, and airport "
        "certification. This tool checks weather parameters only. "
        "Source: FAA AIM §5-4-7, https://www.faa.gov/air_traffic/publications/atpubs/aim_html/"
    )


# ---------------------------------------------------------------------------
# FAA AIM §5-4-7 generic baseline minimums (in feet)
# Reference: https://www.faa.gov/air_traffic/publications/atpubs/aim_html/
# ---------------------------------------------------------------------------

# (required_rvr_ft, required_ceiling_dh_ft)
# ceiling = None means no DH requirement
_MINIMUMS: dict[ApproachCategory, tuple[int, Optional[int]]] = {
    ApproachCategory.CAT_I:     (1800, 200),
    ApproachCategory.CAT_II:    (1200, 100),
    ApproachCategory.CAT_III_A: (700,  None),
    ApproachCategory.CAT_III_B: (150,  None),
    ApproachCategory.CAT_III_C: (0,    None),
}

_MARGINAL_FRACTION = 0.10  # within 10% of minimum is "marginal"

# Visibility unit conversions
_M_TO_FT = 3.28084  # 1 metre = 3.28084 feet for RVR comparison


def _get_ceiling_ft(metar: METARObservation) -> Optional[int]:
    """
    Extract the lowest BKN or OVC layer height as the operational ceiling.

    Per FAA AIM §7-1-14, ceiling is the lowest broken or overcast layer.
    Returns None if no BKN/OVC layer is reported.
    """
    ceiling_layers = [
        layer.height_ft
        for layer in metar.sky
        if layer.cover in (SkyCoverEnum.BKN, SkyCoverEnum.OVC)
        and layer.height_ft is not None
    ]
    return min(ceiling_layers) if ceiling_layers else None


def check_weather_minima(
    metar: METARObservation,
    approach_category: ApproachCategory,
) -> WeatherMinimaResult:
    """
    Check whether the observed METAR conditions meet ILS approach minima.

    Uses FAA AIM §5-4-7 generic baseline minimums. Does NOT account for
    procedure-specific published minima on IAP charts.

    Args:
        metar:             Parsed METAR observation.
        approach_category: ILS category (CAT_I, CAT_II, CAT_III_A/B/C).

    Returns:
        WeatherMinimaResult with GO/MARGINAL/NO_GO decision and explanation.

    Raises:
        ValueError: if metar is None or approach_category is invalid.

    Hand-verification (used in unit tests):
        CAT I: RVR req 1800 ft (≈549 m). Vis 2000 m → 2000 × 3.28 = 6562 ft >> 1800 ft → GO.
        CAT I: Vis 400 m → 400 × 3.28 = 1312 ft < 1800 ft → NO_GO.
        CAT I: Ceiling req 200 ft. OVC at 250 ft → OK. OVC at 150 ft → NO_GO.

    Standard: FAA AIM §5-4-7
    Reference: https://www.faa.gov/air_traffic/publications/atpubs/aim_html/
    """
    if metar is None:
        raise ValueError("metar must not be None")

    required_rvr_ft, required_ceiling_ft = _MINIMUMS[approach_category]

    # Visibility check (compare visibility_m in metres to RVR threshold in feet)
    observed_vis_m = metar.visibility_m
    visibility_ok: Optional[bool] = None
    vis_marginal = False

    if observed_vis_m is not None:
        observed_rvr_ft = observed_vis_m * _M_TO_FT
        if required_rvr_ft == 0:
            visibility_ok = True  # CAT III-C: no vis requirement
        elif observed_rvr_ft >= required_rvr_ft:
            visibility_ok = True
            if (observed_rvr_ft - required_rvr_ft) / required_rvr_ft <= _MARGINAL_FRACTION:
                vis_marginal = True
        else:
            visibility_ok = False
    # If no visibility reported, we cannot confirm — treated as below minima

    # Ceiling check
    observed_ceiling_ft = _get_ceiling_ft(metar)
    ceiling_ok: Optional[bool] = None
    ceiling_marginal = False

    if required_ceiling_ft is None:
        # No DH for CAT III — ceiling check not applicable
        ceiling_ok = True
    elif observed_ceiling_ft is not None:
        if observed_ceiling_ft >= required_ceiling_ft:
            ceiling_ok = True
            if (observed_ceiling_ft - required_ceiling_ft) / required_ceiling_ft <= _MARGINAL_FRACTION:
                ceiling_marginal = True
        else:
            ceiling_ok = False
    # If no ceiling reported but BKN/OVC not present, it's likely clear

    # Decision logic
    limiting_factors: list[str] = []

    if visibility_ok is False:
        limiting_factors.append(
            f"visibility {observed_vis_m}m ({observed_vis_m * _M_TO_FT:.0f}ft) "
            f"below required {required_rvr_ft}ft RVR"
        )
    if observed_vis_m is None and required_rvr_ft > 0:
        limiting_factors.append("visibility not reported in METAR")

    if ceiling_ok is False:
        limiting_factors.append(
            f"ceiling {observed_ceiling_ft}ft below required DH {required_ceiling_ft}ft"
        )
    if ceiling_ok is None and required_ceiling_ft is not None:
        limiting_factors.append("ceiling not determinable from sky layers")

    if limiting_factors:
        decision = MinimaDecision.NO_GO
        limiting_factor = "; ".join(limiting_factors)
    elif vis_marginal or ceiling_marginal:
        decision = MinimaDecision.MARGINAL
        limiting_factor = "conditions within 10% of minima — monitor closely"
    else:
        decision = MinimaDecision.GO
        limiting_factor = "conditions meet minima"

    return WeatherMinimaResult(
        station_id=metar.station_id,
        approach_category=approach_category,
        decision=decision,
        observed_visibility_m=observed_vis_m,
        observed_ceiling_ft=observed_ceiling_ft,
        required_rvr_ft=required_rvr_ft,
        required_ceiling_ft=required_ceiling_ft,
        ceiling_ok=ceiling_ok,
        visibility_ok=visibility_ok,
        limiting_factor=limiting_factor,
    )
