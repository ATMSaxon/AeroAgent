"""
Unit tests for registry.py

Verifies that all 10 tools are registered, that descriptors are well-formed,
and that OpenAI / Anthropic export formats are correct.
"""

import pytest

from aerosafety.tools.registry import (
    get_tool,
    list_tools,
    to_anthropic_tools,
    to_openai_functions,
)

EXPECTED_TOOL_NAMES = {
    "parse_metar",
    "parse_taf",
    "calculate_wind_components",
    "parse_notam",
    "check_time_window",
    "calculate_horizontal_separation",
    "calculate_vertical_separation",
    "get_wake_category",
    "check_mel",
    "check_weather_minima",
}


class TestRegistryContents:
    def test_all_tools_registered(self):
        """All 10 tools must be present."""
        names = {t.name for t in list_tools()}
        assert EXPECTED_TOOL_NAMES == names

    def test_every_tool_has_description(self):
        for tool in list_tools():
            assert tool.description, f"Tool '{tool.name}' has empty description"

    def test_every_tool_has_standard_citation(self):
        """Every tool must cite an aviation standard (CLAUDE.md task hard rule #3)."""
        for tool in list_tools():
            assert tool.standard, f"Tool '{tool.name}' missing standard citation"

    def test_every_tool_has_parameters_schema(self):
        for tool in list_tools():
            assert "properties" in tool.parameters, (
                f"Tool '{tool.name}' parameters missing 'properties'"
            )

    def test_every_tool_parameters_has_required(self):
        for tool in list_tools():
            assert "required" in tool.parameters, (
                f"Tool '{tool.name}' parameters missing 'required' list"
            )

    def test_mel_tool_is_marked_mock(self):
        """MEL checker must be marked as mock (CLAUDE.md §1.2)."""
        mel = get_tool("check_mel")
        assert mel.mock is True

    def test_non_mel_tools_not_mock(self):
        """Real tools must not be marked as mock."""
        for tool in list_tools():
            if tool.name != "check_mel":
                assert tool.mock is False, f"'{tool.name}' should not be marked mock"

    def test_get_tool_known_name(self):
        tool = get_tool("parse_metar")
        assert tool.name == "parse_metar"

    def test_get_tool_unknown_raises(self):
        with pytest.raises(KeyError):
            get_tool("nonexistent_tool")


class TestOpenAIExport:
    def test_openai_format_length(self):
        """All 10 tools exported."""
        exported = to_openai_functions()
        assert len(exported) == 10

    def test_openai_format_structure(self):
        """Each entry must have type='function' and 'function' key."""
        for entry in to_openai_functions():
            assert entry["type"] == "function"
            assert "function" in entry
            fn = entry["function"]
            assert "name" in fn
            assert "description" in fn
            assert "parameters" in fn

    def test_openai_all_names_present(self):
        names = {e["function"]["name"] for e in to_openai_functions()}
        assert names == EXPECTED_TOOL_NAMES


class TestAnthropicExport:
    def test_anthropic_format_length(self):
        exported = to_anthropic_tools()
        assert len(exported) == 10

    def test_anthropic_format_structure(self):
        """Each entry must have name, description, input_schema."""
        for entry in to_anthropic_tools():
            assert "name" in entry
            assert "description" in entry
            assert "input_schema" in entry

    def test_anthropic_all_names_present(self):
        names = {e["name"] for e in to_anthropic_tools()}
        assert names == EXPECTED_TOOL_NAMES
