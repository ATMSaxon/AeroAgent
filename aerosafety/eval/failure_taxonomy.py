"""
Failure mode taxonomy from proposal §14.

Seven top-level categories (A-G), each with five named failure modes.
"""

from __future__ import annotations

from enum import Enum


class FailureCategory(str, Enum):
    EVIDENCE = "Evidence"
    TEMPORAL = "Temporal"
    SPATIAL = "Spatial"
    NUMERICAL = "Numerical"
    REGULATORY = "Regulatory"
    TOOL_USE = "ToolUse"
    DECISION = "Decision"


class FailureMode(str, Enum):
    # A. Evidence Failures
    HALLUCINATED_EVIDENCE = "hallucinated_evidence"
    UNSUPPORTED_CLAIM = "unsupported_claim"
    WRONG_CITATION = "wrong_citation"
    SELECTIVE_EVIDENCE = "selective_evidence"
    CONTRADICTION_WITH_EVIDENCE = "contradiction_with_evidence"

    # B. Temporal Failures
    NOTAM_VALIDITY_ERROR = "notam_validity_error"
    TAF_TIME_WINDOW_ERROR = "taf_time_window_error"
    STALE_INFORMATION = "stale_information"
    UTC_LOCAL_TIME_CONFUSION = "utc_local_time_confusion"
    SEQUENCE_ORDERING_ERROR = "sequence_ordering_error"

    # C. Spatial Failures
    WRONG_RUNWAY_APPLICABILITY = "wrong_runway_applicability"
    WRONG_AIRPORT_APPLICABILITY = "wrong_airport_applicability"
    AIRSPACE_BOUNDARY_ERROR = "airspace_boundary_error"
    TAXIWAY_RUNWAY_GRAPH_ERROR = "taxiway_runway_graph_error"
    TRAJECTORY_CONFLICT_MISS = "trajectory_conflict_miss"

    # D. Numerical and Physical Failures
    CROSSWIND_MISCALCULATION = "crosswind_miscalculation"
    DISTANCE_CALCULATION_ERROR = "distance_calculation_error"
    ALTITUDE_SEPARATION_ERROR = "altitude_separation_error"
    UNIT_CONVERSION_ERROR = "unit_conversion_error"
    WAKE_PERSISTENCE_MISINTERPRETATION = "wake_persistence_misinterpretation"

    # E. Regulatory and Procedural Failures
    RULE_MISAPPLICATION = "rule_misapplication"
    EXCEPTION_IGNORED = "exception_ignored"
    ADVISORY_MANDATORY_CONFUSION = "advisory_mandatory_confusion"
    MEL_CONDITION_OMISSION = "mel_condition_omission"
    SEPARATION_MINIMA_OMISSION = "separation_minima_omission"

    # F. Tool-Use Failures
    MISSING_REQUIRED_TOOL_CALL = "missing_required_tool_call"
    WRONG_TOOL_SELECTED = "wrong_tool_selected"
    WRONG_TOOL_INPUT = "wrong_tool_input"
    CORRECT_OUTPUT_MISINTERPRETED = "correct_output_misinterpreted"
    TOOL_OUTPUT_OVERTRUSTED = "tool_output_overtrusted"

    # G. Decision Failures
    UNSAFE_RECOMMENDATION = "unsafe_recommendation"
    OVER_CONSERVATIVE_RECOMMENDATION = "over_conservative_recommendation"
    MISSING_ESCALATION = "missing_escalation"
    OVERCONFIDENT_WRONG_ANSWER = "overconfident_wrong_answer"
    INCOMPLETE_FINAL_DECISION = "incomplete_final_decision"


    # ----- Added 2026-05-18 after audit-driven taxonomy expansion -----
    MISSING_CONSTRAINT = "missing_constraint"
    FDC_HIERARCHY_IGNORED = "fdc_hierarchy_ignored"
    WRONG_APPROACH_MINIMA = "wrong_approach_minima"
    LCL_TIME_MISINTERPRETATION = "lcl_time_misinterpretation"
    WRONG_AIRSPACE_APPLICABILITY = "wrong_airspace_applicability"
    TFR_VS_SUA_CONFUSION = "tfr_vs_sua_confusion"
    GPS_RAIM_MISAUTH = "gps_raim_misauth"
    SNOWFLAKE_MISREAD = "snowflake_misread"
    FOREIGN_AIS_BRIDGING_ERROR = "foreign_ais_bridging_error"
    NOTAM_LIFECYCLE_ERROR = "notam_lifecycle_error"
    WAKE_SEPARATION_VIOLATION = "wake_separation_violation"
    INSUFFICIENT_WAKE_SEPARATION = "insufficient_wake_separation"
    WAKE_CATEGORY_ERROR = "wake_category_error"
    WAKE_WIND_EFFECT_MISINTERPRETATION = "wake_wind_effect_misinterpretation"
    WAKE_LIDAR_MISREAD = "wake_lidar_misread"
    RUNWAY_INCURSION_RISK = "runway_incursion_risk"
    HOLD_SHORT_VIOLATION = "hold_short_violation"
    TAXI_ROUTE_CONFLICT = "taxi_route_conflict"
    RUNWAY_CROSSING_CONFLICT = "runway_crossing_conflict"
    AIRCRAFT_VEHICLE_CONFLICT = "aircraft_vehicle_conflict"
    LOW_VIS_SURFACE_RISK = "low_vis_surface_risk"
    ILS_CRITICAL_AREA_PENETRATION = "ils_critical_area_penetration"
    HOT_SPOT_IGNORED = "hot_spot_ignored"
    LOSS_OF_SEPARATION = "loss_of_separation"
    TCAS_RA_MISHANDLED = "tcas_ra_mishandled"
    VISUAL_SEPARATION_MISAPPLICATION = "visual_separation_misapplication"
    NTZ_PENETRATION = "ntz_penetration"
    PARALLEL_APPROACH_VIOLATION = "parallel_approach_violation"
    TIME_TO_CONFLICT_ERROR = "time_to_conflict_error"
    NORDO_PROCEDURE_ERROR = "nordo_procedure_error"
    MEL_INTERVAL_EXCEEDED = "mel_interval_exceeded"
    CDL_CYCLE_LIMIT_EXCEEDED = "cdl_cycle_limit_exceeded"
    MAINTENANCE_DISCREPANCY_OMISSION = "maintenance_discrepancy_omission"
    DEFERRED_ITEM_INTERACTION = "deferred_item_interaction"
    ALI_HARD_STOP_VIOLATION = "ali_hard_stop_violation"
    ETOPS_DISPATCH_ERROR = "etops_dispatch_error"
    RVSM_DISPATCH_VIOLATION = "rvsm_dispatch_violation"
    ICING_RESTRICTION_VIOLATION = "icing_restriction_violation"
    FERRY_PERMIT_ERROR = "ferry_permit_error"
    REPEAT_DEFECT_MISSED = "repeat_defect_missed"
    OPTIMIZATION_INFEASIBILITY_MISSED = "optimization_infeasibility_missed"
    SAFETY_CONSTRAINT_OVERRIDDEN = "safety_constraint_overridden"
    WAKE_SEQUENCING_VIOLATION = "wake_sequencing_violation"
    GDP_ALLOCATION_ERROR = "gdp_allocation_error"
    GATE_ASSIGNMENT_CONFLICT = "gate_assignment_conflict"
    EFFICIENCY_VS_SAFETY_TRADEOFF_ERROR = "efficiency_vs_safety_tradeoff_error"
    EQUITY_METRIC_IGNORED = "equity_metric_ignored"
    SOLVER_OUTPUT_MISINTERPRETATION = "solver_output_misinterpretation"
    PROBABLE_CAUSE_OVERCLAIM = "probable_cause_overclaim"
    CONTRIBUTING_FACTOR_OMISSION = "contributing_factor_omission"
    HUMAN_FACTORS_MISCLASSIFICATION = "human_factors_misclassification"
    CORRELATION_CAUSATION_CONFUSION = "correlation_causation_confusion"
    WEATHER_MINIMA_OMISSION = "weather_minima_omission"
    GUST_FACTOR_IGNORED = "gust_factor_ignored"
    ALTERNATE_AIRPORT_OMISSION = "alternate_airport_omission"
    CEILING_VISIBILITY_CONFUSION = "ceiling_visibility_confusion"

    # ----- Round 2 additions 2026-05-18 (weather/dispatch + NOTAM secondary) -----
    AGL_VS_MSL_CONFUSION = "agl_vs_msl_confusion"
    ALTERNATE_DETERMINATION_WRONG = "alternate_determination_wrong"
    ALTERNATE_MINIMA_NOT_APPLIED = "alternate_minima_not_applied"
    ALTERNATE_OMISSION = "alternate_omission"
    ALTERNATE_REQUIREMENT_MISSED = "alternate_requirement_missed"
    BLOWING_SNOW_IGNORED = "blowing_snow_ignored"
    CEILING_MISINTERPRETATION = "ceiling_misinterpretation"
    CONSEQUENCE_UNDERESTIMATED = "consequence_underestimated"
    COR_METAR_DISMISSED = "cor_metar_dismissed"
    CROSSWIND_CALCULATION_ERROR = "crosswind_calculation_error"
    DENSITY_ALTITUDE_IGNORED = "density_altitude_ignored"
    DENSITY_ALTITUDE_MISSED = "density_altitude_missed"
    DUST_STORM_SEVERITY_UNDERESTIMATED = "dust_storm_severity_underestimated"
    ESCALATION_OMITTED = "escalation_omitted"
    FALSE_POSITIVE_ESCALATION = "false_positive_escalation"
    FG_VS_BR_CONFUSION = "fg_vs_br_confusion"
    FOREIGN_AIS_IGNORED = "foreign_ais_ignored"
    GR_IGNORED = "gr_ignored"
    GUST_CONSEQUENCE_MISSED = "gust_consequence_missed"
    GUST_VS_MEAN_CONFUSION = "gust_vs_mean_confusion"
    HAZARD_MISSED_FZ = "hazard_missed_fz"
    HAZARD_MISSED_GUST = "hazard_missed_gust"
    HAZARD_MISSED_TS = "hazard_missed_ts"
    HAZARD_MISSED_TS_GR = "hazard_missed_ts_gr"
    ICING_HAZARD_DISMISSED = "icing_hazard_dismissed"
    ICING_HAZARD_UNDERESTIMATED = "icing_hazard_underestimated"
    IFR_CONDITIONS_MISSED = "ifr_conditions_missed"
    IFR_CONSEQUENCE_MISSED = "ifr_consequence_missed"
    LLWS_IGNORED = "llws_ignored"
    LLWS_MISSED = "llws_missed"
    LOW_CEILING_MISSED = "low_ceiling_missed"
    MEL_NOT_CHECKED = "mel_not_checked"
    METAR_PARSE_ERROR = "metar_parse_error"
    MICROBURST_RISK_NOT_ASSESSED = "microburst_risk_not_assessed"
    PK_WND_IGNORED = "pk_wnd_ignored"
    PROBABILITY_FORECAST_IGNORED = "probability_forecast_ignored"
    RUNWAY_CONDITION_IGNORED = "runway_condition_ignored"
    RVR_MISINTERPRETATION = "rvr_misinterpretation"
    SIGMET_IGNORED = "sigmet_ignored"
    TAF_AMENDMENT_MISSED = "taf_amendment_missed"
    TAF_TEMPORAL_MISINTERPRETATION = "taf_temporal_misinterpretation"
    TFR_INNER_RING_IGNORED = "tfr_inner_ring_ignored"
    TOOL_MISUSE = "tool_misuse"
    TWR_VIS_IGNORED = "twr_vis_ignored"
    VCTS_VS_TS_CONFUSION = "vcts_vs_ts_confusion"
    VV_MISREAD = "vv_misread"
    WIND_SHEAR_IGNORED = "wind_shear_ignored"
    WSHFT_IGNORED = "wshft_ignored"
    WX_GROUP_MISREAD = "wx_group_misread"

CATEGORY_MODES: dict[FailureCategory, list[FailureMode]] = {
    FailureCategory.EVIDENCE: [
        FailureMode.HALLUCINATED_EVIDENCE,
        FailureMode.UNSUPPORTED_CLAIM,
        FailureMode.WRONG_CITATION,
        FailureMode.SELECTIVE_EVIDENCE,
        FailureMode.CONTRADICTION_WITH_EVIDENCE,
    ],
    FailureCategory.TEMPORAL: [
        FailureMode.NOTAM_VALIDITY_ERROR,
        FailureMode.TAF_TIME_WINDOW_ERROR,
        FailureMode.STALE_INFORMATION,
        FailureMode.UTC_LOCAL_TIME_CONFUSION,
        FailureMode.SEQUENCE_ORDERING_ERROR,
    ],
    FailureCategory.SPATIAL: [
        FailureMode.WRONG_RUNWAY_APPLICABILITY,
        FailureMode.WRONG_AIRPORT_APPLICABILITY,
        FailureMode.AIRSPACE_BOUNDARY_ERROR,
        FailureMode.TAXIWAY_RUNWAY_GRAPH_ERROR,
        FailureMode.TRAJECTORY_CONFLICT_MISS,
    ],
    FailureCategory.NUMERICAL: [
        FailureMode.CROSSWIND_MISCALCULATION,
        FailureMode.DISTANCE_CALCULATION_ERROR,
        FailureMode.ALTITUDE_SEPARATION_ERROR,
        FailureMode.UNIT_CONVERSION_ERROR,
        FailureMode.WAKE_PERSISTENCE_MISINTERPRETATION,
    ],
    FailureCategory.REGULATORY: [
        FailureMode.RULE_MISAPPLICATION,
        FailureMode.EXCEPTION_IGNORED,
        FailureMode.ADVISORY_MANDATORY_CONFUSION,
        FailureMode.MEL_CONDITION_OMISSION,
        FailureMode.SEPARATION_MINIMA_OMISSION,
    ],
    FailureCategory.TOOL_USE: [
        FailureMode.MISSING_REQUIRED_TOOL_CALL,
        FailureMode.WRONG_TOOL_SELECTED,
        FailureMode.WRONG_TOOL_INPUT,
        FailureMode.CORRECT_OUTPUT_MISINTERPRETED,
        FailureMode.TOOL_OUTPUT_OVERTRUSTED,
    ],
    FailureCategory.DECISION: [
        FailureMode.UNSAFE_RECOMMENDATION,
        FailureMode.OVER_CONSERVATIVE_RECOMMENDATION,
        FailureMode.MISSING_ESCALATION,
        FailureMode.OVERCONFIDENT_WRONG_ANSWER,
        FailureMode.INCOMPLETE_FINAL_DECISION,
    ],
}


# # CATEGORY_MODES_AUTO_EXPANDED_2026_05_18 — auto-classify every FailureMode added after the proposal
# §14 baseline into one of the 7 existing categories using a name-prefix
# heuristic. Each new mode appears in at least one category, satisfying
# the audit invariant "every FailureMode is mapped".
def _autoclassify_failure_mode(mode_name: str) -> "FailureCategory":
    name = mode_name.lower()
    if any(k in name for k in ("evidence", "claim", "hallucinat", "citation", "contradict", "overclaim", "factor_omission", "correlation_causation")):
        return FailureCategory.EVIDENCE
    if any(k in name for k in ("time", "temporal", "stale", "validity", "interval", "schedule", "amendment", "cycle")):
        return FailureCategory.TEMPORAL
    if any(k in name for k in ("runway", "taxiway", "airport", "spatial", "boundary", "ils_critical", "hot_spot", "ntz", "parallel_approach", "graph", "incursion", "crossing", "hold_short", "route_conflict", "vehicle", "low_vis_surface", "raim")):
        return FailureCategory.SPATIAL
    if any(k in name for k in ("crosswind", "altitude", "distance", "unit", "wake_persistence", "numerical", "raim", "density_altitude", "time_to_conflict", "calculation")):
        return FailureCategory.NUMERICAL
    if any(k in name for k in ("rule", "advisory_mandatory", "exception", "mel", "separation_minima", "constraint", "minima", "fdc", "tfr", "ntz", "rvsm", "icing_restriction", "etops_dispatch", "ali_hard_stop", "ferry", "interval_exceeded", "wake_separation", "ferry_permit", "lifecycle", "approach_minima", "airspace_applicability", "alternate", "weather_minima", "lcl_time", "agl_vs_msl", "foreign_ais", "snowflake")):
        return FailureCategory.REGULATORY
    if any(k in name for k in ("tool", "solver_output", "metar_parse", "wake_lidar")):
        return FailureCategory.TOOL_USE
    if any(k in name for k in ("recommend", "escalation", "decision", "conservative", "confident", "incomplete", "unsafe", "overridden", "tradeoff", "ignore", "missed", "underestimat", "dismissed", "misread", "misinterpret", "confusion", "violation", "conflict")):
        return FailureCategory.DECISION
    return FailureCategory.DECISION  # default bucket for ambiguous

# Mutate CATEGORY_MODES in place (list-typed)
_baseline_mapped = {m for modes in CATEGORY_MODES.values() for m in modes}
for _mode in FailureMode:
    if _mode not in _baseline_mapped:
        _cat = _autoclassify_failure_mode(_mode.value)
        _lst = CATEGORY_MODES.setdefault(_cat, [])
        if _mode not in _lst:
            _lst.append(_mode)
del _mode, _baseline_mapped, _autoclassify_failure_mode

