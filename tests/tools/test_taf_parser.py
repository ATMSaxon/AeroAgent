"""
Unit tests for taf_parser.py

Standard: WMO No. 306 Vol. I.1, FM 51-XVI TAF
Reference: https://library.wmo.int/records/item/35713
"""

import pytest
from aerosafety.tools.taf_parser import (
    TAFParseError,
    ChangeIndicator,
    parse_taf,
)


class TestTAFBasicParsing:
    def test_simple_taf(self):
        """
        TAF KLAX 101720Z 1018/1118 27015KT P6SM SKC

        Hand-computed:
          - valid from: day 10, hour 18 UTC
          - valid to:   day 11, hour 18 UTC
          - base wind: 270°/15 kt
          - base visibility: >6 SM (P6SM encoded, not parsed as exact metres here)
          - SKC: sky clear
        """
        raw = "TAF KLAX 101720Z 1018/1118 27015KT P6SM SKC"
        taf = parse_taf(raw)
        assert taf.station_id == "KLAX"
        assert taf.valid_from.day == 10
        assert taf.valid_from.hour == 18
        assert taf.valid_to.day == 11
        assert taf.valid_to.hour == 18
        assert taf.base_conditions.wind is not None
        assert taf.base_conditions.wind.direction_deg == 270
        assert taf.base_conditions.wind.speed_kt == 15

    def test_taf_with_fm_group(self):
        """
        TAF EGLL 101200Z 1012/1112 09010KT 9999 FEW025
             FM101800 18020KT CAVOK

        Hand-computed: one FM group starting day 10, 18:00 UTC.
        """
        raw = (
            "TAF EGLL 101200Z 1012/1112 09010KT 9999 FEW025 "
            "FM101800 18020KT CAVOK"
        )
        taf = parse_taf(raw)
        assert taf.station_id == "EGLL"
        assert len(taf.change_groups) == 1
        grp = taf.change_groups[0]
        assert grp.indicator == ChangeIndicator.FM
        assert grp.valid_from.hour == 18
        assert grp.conditions.wind.direction_deg == 180
        assert grp.conditions.wind.speed_kt == 20
        assert grp.conditions.visibility_m == 9999

    def test_taf_with_becmg(self):
        """
        TAF KSFO 101800Z 1018/1118 26015KT 9999 SCT030
             BECMG 1022/1024 28008KT

        BECMG group with validity window 1022–1024 (day 10 22:00 to day 10 24:00 UTC).
        """
        raw = (
            "TAF KSFO 101800Z 1018/1118 26015KT 9999 SCT030 "
            "BECMG 1022/1024 28008KT"
        )
        taf = parse_taf(raw)
        assert len(taf.change_groups) == 1
        grp = taf.change_groups[0]
        assert grp.indicator == ChangeIndicator.BECMG
        assert grp.valid_from.hour == 22
        # WMO hour 24 → midnight next day; valid_to.hour == 0 (next day)
        assert grp.valid_to.hour == 0
        assert grp.conditions.wind.direction_deg == 280
        assert grp.conditions.wind.speed_kt == 8

    def test_taf_with_tempo(self):
        """
        TEMPO group with rain and reduced visibility.
        """
        raw = (
            "TAF KORD 101800Z 1018/1118 27015KT 9999 SKC "
            "TEMPO 1020/1023 5SM -RA BKN020"
        )
        taf = parse_taf(raw)
        grp = taf.change_groups[0]
        assert grp.indicator == ChangeIndicator.TEMPO
        assert "-RA" in grp.conditions.weather

    def test_taf_with_prob30(self):
        """PROB30 TEMPO group."""
        raw = (
            "TAF EGLL 101200Z 1012/1112 09010KT 9999 FEW025 "
            "PROB30 TEMPO 1014/1018 3000 -RASN BKN010"
        )
        taf = parse_taf(raw)
        grp = taf.change_groups[0]
        assert grp.indicator == ChangeIndicator.PROB30

    def test_taf_amd_flag(self):
        """AMD flag should be detected."""
        raw = "TAF AMD KLAX 101720Z 1018/1118 27015KT 9999 SKC"
        taf = parse_taf(raw)
        assert taf.amd is True
        assert taf.cor is False

    def test_invalid_station_raises(self):
        """Non-ICAO station raises TAFParseError."""
        with pytest.raises(TAFParseError):
            parse_taf("TAF K1AX 101720Z 1018/1118 27015KT 9999 SKC")

    def test_too_short_raises(self):
        """Extremely short string raises TAFParseError."""
        with pytest.raises(TAFParseError):
            parse_taf("TAF")
