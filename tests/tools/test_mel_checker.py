"""
Unit tests for mel_checker.py (MOCK IMPLEMENTATION)

These tests verify that the stub behaves correctly and honestly:
- Returns mock=True always
- Returns status="UNKNOWN" always
- Never claims operational authority
- Raises on empty input

Standard cited: FAA Order 8900.1 Vol. 4 Ch. 4
Reference: https://fsims.faa.gov/wdocs/8900.1/
"""

import pytest

from aerosafety.tools.mel_checker import MELCheckResult, check_mel


class TestMELCheckerMockBehavior:
    def test_always_returns_mock_true(self):
        """Stub MUST always return mock=True (CLAUDE.md §1.2)."""
        result = check_mel("B738", "28-00-01")
        assert result.mock is True

    def test_always_returns_unknown_status(self):
        """Status must always be UNKNOWN — stub has no real MEL data."""
        result = check_mel("A320", "fuel pump")
        assert result.status == "UNKNOWN"

    def test_action_required_mentions_mel(self):
        """Action field must direct to the actual MEL."""
        result = check_mel("B737", "APU")
        assert "MEL" in result.action_required.upper()

    def test_message_mentions_proprietary(self):
        """Message should acknowledge the proprietary nature of MEL data."""
        result = check_mel("B744", "left engine")
        assert any(
            word in result.message.lower()
            for word in ("proprietary", "operator", "mock", "approved")
        )

    def test_empty_aircraft_type_raises(self):
        """Empty aircraft_type must raise ValueError (CLAUDE.md §8.1)."""
        with pytest.raises(ValueError):
            check_mel("", "fuel pump")

    def test_empty_system_raises(self):
        """Empty system_or_item must raise ValueError."""
        with pytest.raises(ValueError):
            check_mel("B738", "")

    def test_result_is_pydantic_model(self):
        """Result must be a MELCheckResult pydantic model."""
        result = check_mel("B752", "flaps")
        assert isinstance(result, MELCheckResult)

    def test_aircraft_type_normalised(self):
        """Input aircraft type should be uppercased in result."""
        result = check_mel("b738", "nav light")
        assert result.aircraft_type == "B738"
