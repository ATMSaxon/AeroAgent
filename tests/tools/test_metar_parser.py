"""
Unit tests for metar_parser.py

Hand-computed expected values are derived directly from WMO FM 15-XVI token
grammar. Each test case documents the expected values and how they were derived.

Standard: WMO No. 306 Vol. I.1, FM 15-XVI METAR
Reference: https://library.wmo.int/records/item/35713
"""

import pytest

from aerosafety.tools.metar_parser import (
    METARParseError,
    SkyCoverEnum,
    parse_metar,
)


class TestMETARBasicParsing:
    def test_full_us_metar(self):
        """
        METAR KLAX 101953Z 27015G25KT 10SM BKN035 OVC080 18/08 A2985

        Hand-computed expected values:
          - station: KLAX
          - wind direction: 270°, speed 15 kt, gust 25 kt
          - visibility: 10 SM = 10 × 1609.344 = 16093 m
          - sky: BKN035 → BKN at 3500 ft; OVC080 → OVC at 8000 ft
          - temp: 18°C, dewpoint: 8°C
          - altimeter: A2985 → 2985/100 = 29.85 inHg
        """
        raw = "METAR KLAX 101953Z 27015G25KT 10SM BKN035 OVC080 18/08 A2985"
        obs = parse_metar(raw)
        assert obs.station_id == "KLAX"
        assert obs.wind is not None
        assert obs.wind.direction_deg == 270
        assert obs.wind.speed_kt == 15
        assert obs.wind.gust_kt == 25
        # 10 SM → 10 × 1609.344 = 16093.44 → rounded to 16093
        assert obs.visibility_m == 16093
        assert len(obs.sky) == 2
        assert obs.sky[0].cover == SkyCoverEnum.BKN
        assert obs.sky[0].height_ft == 3500
        assert obs.sky[1].cover == SkyCoverEnum.OVC
        assert obs.sky[1].height_ft == 8000
        assert obs.temp_c == 18
        assert obs.dewpoint_c == 8
        assert abs(obs.altimeter_inhg - 29.85) < 0.001

    def test_icao_metar_with_qnh(self):
        """
        METAR EGLL 101920Z 09008KT 9999 FEW022 SCT045 13/07 Q1014

        Hand-computed:
          - wind: 090° / 8 kt (no gust)
          - visibility: 9999 m (≥10 km, WMO code)
          - sky: FEW022 at 2200 ft, SCT045 at 4500 ft
          - temp: 13°C, dewpoint: 7°C
          - altimeter_hpa: 1014 hPa
        """
        raw = "METAR EGLL 101920Z 09008KT 9999 FEW022 SCT045 13/07 Q1014"
        obs = parse_metar(raw)
        assert obs.station_id == "EGLL"
        assert obs.wind.direction_deg == 90
        assert obs.wind.speed_kt == 8
        assert obs.wind.gust_kt is None
        assert obs.visibility_m == 9999
        assert obs.sky[0].cover == SkyCoverEnum.FEW
        assert obs.sky[0].height_ft == 2200
        assert obs.sky[1].cover == SkyCoverEnum.SCT
        assert obs.sky[1].height_ft == 4500
        assert obs.temp_c == 13
        assert obs.dewpoint_c == 7
        assert obs.altimeter_hpa == 1014
        assert obs.altimeter_inhg is None

    def test_cavok(self):
        """
        METAR YSSY 101000Z 15010KT CAVOK 22/12 Q1020

        CAVOK: Ceiling And Visibility OK — visibility ≥10 km, no cloud
        below 5000 ft, no wx. Encoded as visibility_m=9999 and sky CAVOK.
        """
        raw = "METAR YSSY 101000Z 15010KT CAVOK 22/12 Q1020"
        obs = parse_metar(raw)
        assert obs.visibility_m == 9999
        assert any(s.cover == SkyCoverEnum.CAVOK for s in obs.sky)

    def test_vrb_wind(self):
        """VRB03KT — variable wind 3 kt, no direction."""
        raw = "METAR KLGA 100953Z VRB03KT 10SM CLR 20/10 A2995"
        obs = parse_metar(raw)
        assert obs.wind.variable is True
        assert obs.wind.direction_deg is None
        assert obs.wind.speed_kt == 3

    def test_auto_flag(self):
        """AUTO flag should be detected."""
        raw = "METAR KORD 101253Z AUTO 25012KT 7SM -RA BKN030 15/10 A2990"
        obs = parse_metar(raw)
        assert obs.auto is True

    def test_sub_sm_visibility(self):
        """
        1/4SM: 0.25 × 1609.344 = 402.336 → 402 m

        This tests fractional statute mile visibility common in US low-vis METARs.
        """
        raw = "METAR KORD 101253Z 25012KT 1/4SM FG OVC002 10/09 A2985"
        obs = parse_metar(raw)
        # 1/4 SM = 0.25 × 1609.344 = 402.336 → 402 m
        assert obs.visibility_m == 402

    def test_negative_temperature(self):
        """M05/M08 → temp=-5°C, dewpoint=-8°C."""
        raw = "METAR CYYZ 101800Z 31015KT 9999 OVC015 M05/M08 Q0995"
        obs = parse_metar(raw)
        assert obs.temp_c == -5
        assert obs.dewpoint_c == -8

    def test_present_weather(self):
        """-RA should appear in weather list (light rain)."""
        raw = "METAR KBOS 101753Z 20010KT 5SM -RA OVC025 15/12 A2992"
        obs = parse_metar(raw)
        assert "-RA" in obs.weather

    def test_rvr_captured(self):
        """RVR groups should be captured verbatim."""
        raw = "METAR KJFK 100553Z 04003KT 1/8SM FG R04R/0600FT OVC002 08/08 A2980"
        obs = parse_metar(raw)
        assert any("R04R" in r for r in obs.rvr)

    def test_clr_sky(self):
        """CLR means no clouds below 12,000 ft (US ASOS)."""
        raw = "METAR KPHX 101953Z 18005KT 10SM CLR 35/05 A2990"
        obs = parse_metar(raw)
        assert obs.sky[0].cover == SkyCoverEnum.CLR

    def test_mps_wind_converted_to_kt(self):
        """
        01010MPS → 10 m/s × 1.94384 = 19.44 → 19 kt

        MPS (metres per second) is the unit used in some ICAO regions.
        """
        raw = "METAR UUDD 101200Z 01010MPS 9999 BKN030 15/10 Q1012"
        obs = parse_metar(raw)
        assert obs.wind.unit == "KT"
        assert obs.wind.speed_kt == 19  # round(10 × 1.94384)

    def test_missing_station_raises(self):
        """Too-short input must raise METARParseError."""
        with pytest.raises(METARParseError):
            parse_metar("KLAX")

    def test_invalid_station_raises(self):
        """Non-ICAO station ID must raise METARParseError."""
        with pytest.raises(METARParseError):
            parse_metar("METAR K1AX 101953Z 27015KT 10SM CLR 18/08 A2985")

    def test_remarks_captured(self):
        """Everything after RMK should appear in remarks."""
        raw = "METAR KLAX 101953Z 27015KT 10SM CLR 22/10 A2990 RMK AO2 SLP132"
        obs = parse_metar(raw)
        assert "AO2" in obs.remarks
        assert "SLP132" in obs.remarks
