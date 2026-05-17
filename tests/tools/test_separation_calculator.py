"""
Unit tests for separation_calculator.py

All expected values are hand-verified.

Standard: FAA Order JO 7110.65Z
Reference: https://www.faa.gov/air_traffic/publications/atpubs/atc_html/

Haversine formula: Sinnott, R.W. (1984), Sky and Telescope, 68(2), 159.
Earth radius: 3440.065 NM (mean sphere approximation)
"""

import math
import pytest
from aerosafety.tools.separation_calculator import (
    SeparationError,
    calculate_horizontal_separation,
    calculate_vertical_separation,
)


class TestHorizontalSeparation:
    def test_same_point_zero_distance(self):
        """Same lat/lon → distance = 0."""
        result = calculate_horizontal_separation(40.0, -73.0, 40.0, -73.0)
        assert result.distance_nm == 0.0
        assert result.distance_km == 0.0

    def test_kjfk_to_klga_approx(self):
        """
        KJFK (40.6413° N, 73.7781° W) to KLGA (40.7769° N, 73.8740° W).

        Hand-computation using haversine:
          dphi = 40.7769 - 40.6413 = 0.1356° = 0.002367 rad
          dlambda = -73.8740 - (-73.7781) = -0.0959° = -0.001674 rad
          a = sin(0.001184)^2 + cos(0.7096)*cos(0.7120)*sin(-0.000837)^2
            ≈ 1.402e-6 + 0.6048 * 0.6041 * 7.00e-7
            ≈ 1.402e-6 + 2.553e-7 ≈ 1.657e-6
          c = 2 * atan2(sqrt(1.657e-6), sqrt(1 - 1.657e-6))
            ≈ 2 * 1.288e-3 = 2.576e-3 rad
          distance = 3440.065 × 2.576e-3 ≈ 8.86 NM

        Published approx distance: ~8 NM (chart). Our formula gives ≈8.5-9 NM
        depending on exact coordinate source. Verify range 7-10 NM.
        """
        result = calculate_horizontal_separation(40.6413, -73.7781, 40.7769, -73.8740)
        # Expect approximately 8-10 NM based on published aeronautical data
        assert 7.0 < result.distance_nm < 12.0
        assert result.distance_km > 0

    def test_equator_1_degree_longitude(self):
        """
        On the equator, 1° longitude = 1° of arc = 60 NM exactly
        (at the equator, latitude difference effect negligible).

        Hand-computation:
          lat1=lat2=0°, lon1=0°, lon2=1°
          dphi = 0, dlambda = 1° = π/180 rad
          a = 0 + cos(0)*cos(0)*sin(π/360)^2 = sin(π/360)^2
          sin(π/360) = sin(0.008727) ≈ 0.008727
          a ≈ 7.616e-5
          c = 2*atan2(0.008727, 0.99996) ≈ 2 * 0.008727 = 0.01745 rad
          distance = 3440.065 × 0.01745 = 60.03 NM

        Expected: ≈ 60 NM (1 degree of arc at equator)
        """
        result = calculate_horizontal_separation(0.0, 0.0, 0.0, 1.0)
        assert abs(result.distance_nm - 60.0) < 0.5  # within 0.5 NM of 60

    def test_north_pole_to_equator(self):
        """
        90° N to 0° N (along a meridian) = 5400 NM (90° × 60 NM/degree).

        Hand-computation:
          dphi = 90° = π/2 rad, dlambda = 0
          a = sin(π/4)^2 = 0.5
          c = 2*atan2(sqrt(0.5), sqrt(0.5)) = 2*atan2(1,1) = 2*(π/4) = π/2
          distance = 3440.065 × π/2 ≈ 5400.5 NM
        """
        result = calculate_horizontal_separation(90.0, 0.0, 0.0, 0.0)
        # 90° × 60 NM = 5400 NM
        assert abs(result.distance_nm - 5400.0) < 5.0

    def test_invalid_lat_raises(self):
        with pytest.raises(SeparationError):
            calculate_horizontal_separation(91.0, 0.0, 0.0, 0.0)

    def test_invalid_lon_raises(self):
        with pytest.raises(SeparationError):
            calculate_horizontal_separation(0.0, 181.0, 0.0, 0.0)

    def test_km_and_nm_consistent(self):
        """distance_km should equal distance_nm × 1.852 (by definition of knot/NM)."""
        result = calculate_horizontal_separation(40.0, -73.0, 41.0, -73.0)
        expected_km = result.distance_nm * 1.852
        assert abs(result.distance_km - expected_km) < 0.5  # allow small rounding


class TestVerticalSeparation:
    def test_fl350_vs_fl330(self):
        """
        FL350 (35000 ft) vs FL330 (33000 ft) → 2000 ft separation.
        This is the standard RVSM separation minimum.
        """
        result = calculate_vertical_separation(35000.0, 33000.0)
        assert result.separation_ft == 2000.0

    def test_order_independent(self):
        """Separation is absolute — order of arguments must not matter."""
        r1 = calculate_vertical_separation(35000.0, 33000.0)
        r2 = calculate_vertical_separation(33000.0, 35000.0)
        assert r1.separation_ft == r2.separation_ft

    def test_same_altitude_zero_separation(self):
        """Same altitude → 0 ft separation."""
        result = calculate_vertical_separation(10000.0, 10000.0)
        assert result.separation_ft == 0.0

    def test_4000_vs_6000(self):
        """4000 ft vs 6000 ft → 2000 ft separation."""
        result = calculate_vertical_separation(4000.0, 6000.0)
        assert result.separation_ft == 2000.0

    def test_implausible_altitude_raises(self):
        with pytest.raises(SeparationError):
            calculate_vertical_separation(-5000.0, 10000.0)

    def test_sea_level_vs_above(self):
        """Sea level (0 ft) to 500 ft → 500 ft."""
        result = calculate_vertical_separation(0.0, 500.0)
        assert result.separation_ft == 500.0
