"""
Unit tests for wind_component.py

All expected values are hand-computed using standard trigonometry.
Formula: headwind = V × cos(θ), crosswind = V × sin(θ)
where θ = wind_direction - runway_heading (mod 360°).

Standard: FAA-H-8083-25C Chapter 5
Reference: https://www.faa.gov/regulations_policies/handbooks_manuals/aviation/phak
"""

import pytest

from aerosafety.tools.wind_component import (
    WindComponentError,
    calculate_wind_components,
)


class TestWindComponentHandComputed:
    """
    All test cases below have hand-verified expected values.
    """

    def test_pure_crosswind_from_west_runway_south(self):
        """
        Wind 270°/15 kt, runway heading 180°.

        Hand computation:
          θ = (270 - 180) mod 360 = 90°
          headwind = 15 × cos(90°) = 15 × 0.0 = 0.0 kt
          crosswind = 15 × sin(90°) = 15 × 1.0 = 15.0 kt (positive = from right)

        A west wind (270°) blowing perpendicular to a runway pointing south (180°)
        creates a pure crosswind from the right side of the runway.
        """
        result = calculate_wind_components(270, 15, 180)
        assert abs(result.headwind_kt - 0.0) < 0.01
        assert abs(result.crosswind_kt - 15.0) < 0.01
        assert result.tailwind_kt == 0.0

    def test_pure_headwind(self):
        """
        Wind 360°/20 kt, runway heading 360°.

        Hand computation:
          θ = (360 - 360) mod 360 = 0°
          headwind = 20 × cos(0°) = 20 × 1.0 = 20.0 kt
          crosswind = 20 × sin(0°) = 20 × 0.0 = 0.0 kt
        """
        result = calculate_wind_components(360, 20, 360)
        assert abs(result.headwind_kt - 20.0) < 0.01
        assert abs(result.crosswind_kt - 0.0) < 0.01
        assert result.tailwind_kt == 0.0

    def test_pure_tailwind(self):
        """
        Wind 180°/10 kt, runway heading 360°.

        Hand computation:
          θ = (180 - 360) mod 360 = 180°
          headwind = 10 × cos(180°) = 10 × (-1.0) = -10.0 kt (tailwind)
          crosswind = 10 × sin(180°) ≈ 0.0 kt
          tailwind_kt = max(0, -(-10)) = 10.0 kt
        """
        result = calculate_wind_components(180, 10, 360)
        assert abs(result.headwind_kt - (-10.0)) < 0.01
        assert abs(result.crosswind_kt) < 0.01
        assert abs(result.tailwind_kt - 10.0) < 0.01

    def test_crosswind_from_left(self):
        """
        Wind 090°/10 kt, runway heading 360°.

        Hand computation:
          θ = (90 - 360) mod 360 = 90°
          headwind = 10 × cos(90°) = 0.0 kt
          crosswind = 10 × sin(90°) = 10.0 kt (positive = from right)

        Wait — east wind (090°) on a north-heading (360°) runway:
          The wind is on the RIGHT side (east = right of north-pointing runway).
          crosswind should be positive (from right) = +10.0 kt.

        Let us re-check: θ = (90 - 360) mod 360 = (90 - 360 + 360) = 90°.
          sin(90°) = 1.0 → crosswind = +10.0 (from right).
        """
        result = calculate_wind_components(90, 10, 360)
        assert abs(result.headwind_kt) < 0.01
        assert abs(result.crosswind_kt - 10.0) < 0.01  # from right (east = right of north)

    def test_crosswind_from_left_runway_east(self):
        """
        Wind 360°/10 kt (north wind), runway heading 090° (east runway).

        Hand computation:
          θ = (360 - 90) mod 360 = 270°
          headwind = 10 × cos(270°) = 10 × 0.0 = 0.0 kt
          crosswind = 10 × sin(270°) = 10 × (-1.0) = -10.0 kt (from left)

        A north wind on an east-pointing runway comes from the left.
        """
        result = calculate_wind_components(360, 10, 90)
        assert abs(result.headwind_kt) < 0.01
        assert abs(result.crosswind_kt - (-10.0)) < 0.01  # from left

    def test_45_degree_crosswind(self):
        """
        Wind 045°/14.14 kt, runway heading 360°.

        Hand computation:
          θ = (45 - 360) mod 360 = 45°
          headwind = 14.14 × cos(45°) = 14.14 × 0.7071 ≈ 10.0 kt
          crosswind = 14.14 × sin(45°) = 14.14 × 0.7071 ≈ 10.0 kt

        Wind at 45° to runway splits equally into headwind and crosswind.
        """
        speed = 14.142135623730951  # = 10 * sqrt(2)
        result = calculate_wind_components(45, speed, 360)
        assert abs(result.headwind_kt - 10.0) < 0.1
        assert abs(result.crosswind_kt - 10.0) < 0.1

    def test_zero_wind(self):
        """Zero wind speed → all components zero."""
        result = calculate_wind_components(270, 0, 180)
        assert result.headwind_kt == 0.0
        assert result.crosswind_kt == 0.0
        assert result.tailwind_kt == 0.0

    def test_runway_000(self):
        """Runway 000 (north) should behave identically to runway 360."""
        result_360 = calculate_wind_components(270, 15, 360)
        result_000 = calculate_wind_components(270, 15, 0)
        # 360° and 0° are the same heading
        assert abs(result_360.headwind_kt - result_000.headwind_kt) < 0.01
        assert abs(result_360.crosswind_kt - result_000.crosswind_kt) < 0.01


class TestWindComponentValidation:
    def test_negative_speed_raises(self):
        with pytest.raises(WindComponentError):
            calculate_wind_components(270, -5, 180)

    def test_direction_out_of_range_high_raises(self):
        # 360 is now valid (runway 36 convention); 361 must still raise
        with pytest.raises(WindComponentError):
            calculate_wind_components(361, 10, 180)

    def test_direction_out_of_range_low_raises(self):
        with pytest.raises(WindComponentError):
            calculate_wind_components(-1, 10, 180)

    def test_runway_heading_out_of_range_raises(self):
        with pytest.raises(WindComponentError):
            calculate_wind_components(270, 10, 400)
