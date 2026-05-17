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
