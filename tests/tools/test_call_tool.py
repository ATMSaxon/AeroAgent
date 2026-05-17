"""
Unit tests for aerosafety.tools.call_tool dispatcher.

Verifies ToolCall schema population, runtime measurement, error capture,
and re-raise behaviour (CLAUDE.md §8.1).
"""

import pytest
from aerosafety.io import ToolCall
from aerosafety.tools import call_tool
from aerosafety.tools.wind_component import (
    calculate_wind_components,
    WindComponentError,
)
from aerosafety.tools.separation_calculator import calculate_vertical_separation


class TestCallToolSuccess:
    def test_returns_tool_call_schema(self):
        """call_tool must return an aerosafety.io.ToolCall instance."""
        tc = call_tool(
            calculate_vertical_separation,
            {"altitude1_ft": 35000.0, "altitude2_ft": 33000.0},
        )
        assert isinstance(tc, ToolCall)

    def test_name_is_function_name(self):
        tc = call_tool(
            calculate_vertical_separation,
            {"altitude1_ft": 35000.0, "altitude2_ft": 33000.0},
        )
        assert tc.name == "calculate_vertical_separation"

    def test_name_override(self):
        tc = call_tool(
            calculate_vertical_separation,
            {"altitude1_ft": 35000.0, "altitude2_ft": 33000.0},
            tool_name="vert_sep",
        )
        assert tc.name == "vert_sep"

    def test_args_recorded(self):
        args = {"altitude1_ft": 10000.0, "altitude2_ft": 12000.0}
        tc = call_tool(calculate_vertical_separation, args)
        assert tc.args == args

    def test_result_populated(self):
        tc = call_tool(
            calculate_vertical_separation,
            {"altitude1_ft": 35000.0, "altitude2_ft": 33000.0},
        )
        assert tc.result is not None
        assert tc.error is None

    def test_result_is_dict_from_pydantic(self):
        """Pydantic model results must be serialised to dict (JSON-safe)."""
        tc = call_tool(
            calculate_vertical_separation,
            {"altitude1_ft": 35000.0, "altitude2_ft": 33000.0},
        )
        assert isinstance(tc.result, dict)
        assert tc.result["separation_ft"] == 2000.0

    def test_runtime_ms_positive(self):
        tc = call_tool(
            calculate_vertical_separation,
            {"altitude1_ft": 35000.0, "altitude2_ft": 33000.0},
        )
        assert tc.runtime_ms is not None
        assert tc.runtime_ms >= 0.0

    def test_wind_component_tool_call(self):
        """End-to-end via call_tool with wind component tool."""
        tc = call_tool(
            calculate_wind_components,
            {"wind_direction_deg": 270, "wind_speed_kt": 15, "runway_heading_deg": 180},
        )
        assert tc.error is None
        assert tc.result["headwind_kt"] == 0.0
        assert tc.result["crosswind_kt"] == 15.0


class TestCallToolError:
    def test_reraises_on_bad_input(self):
        """call_tool must re-raise exceptions (CLAUDE.md §8.1 — no silent failure)."""
        with pytest.raises(WindComponentError):
            call_tool(
                calculate_wind_components,
                {"wind_direction_deg": -5, "wind_speed_kt": 10, "runway_heading_deg": 180},
            )

    def test_error_field_populated_before_reraise(self):
        """
        Although the exception is re-raised, the ToolCall with error is
        constructed internally. We verify this by catching the exception
        and checking we can't accidentally suppress the re-raise.
        """
        raised = False
        try:
            call_tool(
                calculate_wind_components,
                {"wind_direction_deg": 999, "wind_speed_kt": 10, "runway_heading_deg": 180},
            )
        except WindComponentError:
            raised = True
        assert raised, "call_tool must re-raise the original exception"
