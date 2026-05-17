"""
Unit tests for wake_category_checker.py

Standard: ICAO Doc 8643 Aircraft Type Designators
Reference: https://www.icao.int/safety/vleap/Pages/Doc-8643.aspx
"""

import pytest

from aerosafety.tools.wake_category_checker import (
    UnknownAircraftTypeError,
    WakeCategory,
    get_wake_category,
)


class TestWakeCategoryKnownTypes:
    def test_a380_is_super(self):
        """A388 (A380-800) → J (Super heavy)."""
        result = get_wake_category("A388")
        assert result.wake_category == WakeCategory.SUPER

    def test_b744_is_heavy(self):
        """B744 (747-400) → H (Heavy)."""
        result = get_wake_category("B744")
        assert result.wake_category == WakeCategory.HEAVY

    def test_b738_is_medium(self):
        """B738 (737-800) → M (Medium)."""
        result = get_wake_category("B738")
        assert result.wake_category == WakeCategory.MEDIUM

    def test_a320_is_medium(self):
        """A320 → M (Medium)."""
        result = get_wake_category("A320")
        assert result.wake_category == WakeCategory.MEDIUM

    def test_c172_is_light(self):
        """C172 (Cessna 172) → L (Light)."""
        result = get_wake_category("C172")
        assert result.wake_category == WakeCategory.LIGHT

    def test_b772_is_heavy(self):
        """B772 (777-200) → H (Heavy)."""
        result = get_wake_category("B772")
        assert result.wake_category == WakeCategory.HEAVY

    def test_case_normalisation(self):
        """Lowercase input 'b738' should work identically to 'B738'."""
        result = get_wake_category("b738")
        assert result.wake_category == WakeCategory.MEDIUM

    def test_source_field_present(self):
        """Result must cite ICAO Doc 8643."""
        result = get_wake_category("A320")
        assert "ICAO Doc 8643" in result.source

    def test_b789_is_heavy(self):
        """B789 (787-9) → H."""
        result = get_wake_category("B789")
        assert result.wake_category == WakeCategory.HEAVY

    def test_crj9_is_medium(self):
        """CRJ9 (CRJ-900) → M."""
        result = get_wake_category("CRJ9")
        assert result.wake_category == WakeCategory.MEDIUM


class TestWakeCategoryUnknown:
    def test_unknown_type_raises(self):
        """Type not in table must raise UnknownAircraftTypeError, never return a default."""
        with pytest.raises(UnknownAircraftTypeError):
            get_wake_category("ZZZZ")

    def test_fictional_type_raises(self):
        with pytest.raises(UnknownAircraftTypeError):
            get_wake_category("FAKE")

    def test_empty_type_raises(self):
        with pytest.raises(ValueError):
            get_wake_category("")
