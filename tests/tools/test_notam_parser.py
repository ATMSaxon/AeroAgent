"""
Unit tests for notam_parser.py

Standard: ICAO Annex 15, 16th edition, 2018; FAA Order JO 7930.2S
References:
    https://www.icao.int/safety/information-management/Pages/Annex15.aspx
    https://www.faa.gov/regulations_policies/orders_notices
"""

import pytest

from aerosafety.tools.notam_parser import NOTAMParseError, parse_notam

# Minimal ICAO-format NOTAM (A-series, NOTAMN, fields A-E)
SAMPLE_NOTAM = """
A1234/24 NOTAMN
Q) KZNY/QMRLC/IV/NBO/A/000/999/4038N07356W025
A) KJFK
B) 2401101000
C) 2401101800
E) RWY 13R/31L CLOSED FOR MAINTENANCE
""".strip()

SAMPLE_NOTAM_WITH_TAXIWAY = """
A5678/24 NOTAMN
Q) KZNY/QMXLC/IV/NBO/A/000/999/4038N07356W025
A) KLGA
B) 2401151200
C) 2401151800
E) TWY A AND TWY B CLOSED. RWY 22 OPEN.
""".strip()

SAMPLE_NOTAM_PERMANENT = """
B0001/24 NOTAMN
Q) EGTT/QXXXX/IV/NBO/A/000/999/5130N00028W005
A) EGLL
B) 2401010000
C) PERM
E) NEW OBSTACLE LIGHT INSTALLED ON HANGAR 5
""".strip()

SAMPLE_NOTAM_EST = """
C0099/24 NOTAMN
Q) KZLC/QOBCE/IV/M/AE/000/200/3700N10900W050
A) KSLC
B) 2403010600
C) 2403011800EST
E) CRANE OPERATING WITHIN 5NM
""".strip()


class TestNOTAMParser:
    def test_basic_notam_fields(self):
        obs = parse_notam(SAMPLE_NOTAM)
        assert obs.series == "A"
        assert obs.number == "1234/24"
        assert obs.notam_type == "N"
        assert obs.location == "KJFK"
        assert obs.effective_from is not None
        assert obs.effective_from.year == 2024
        assert obs.effective_from.month == 1
        assert obs.effective_from.day == 10
        assert obs.effective_from.hour == 10
        assert obs.effective_from.minute == 0
        assert obs.effective_to is not None
        assert obs.effective_to.hour == 18
        assert obs.permanent is False

    def test_runway_extraction(self):
        """Runway IDs must be extracted from E text."""
        obs = parse_notam(SAMPLE_NOTAM)
        # E text: "RWY 13R/31L CLOSED FOR MAINTENANCE"
        # should find 13R and 31L
        assert "13R" in obs.affected_runways
        assert "31L" in obs.affected_runways

    def test_taxiway_extraction(self):
        """Taxiway IDs must be extracted from E text."""
        obs = parse_notam(SAMPLE_NOTAM_WITH_TAXIWAY)
        assert "A" in obs.affected_taxiways
        assert "B" in obs.affected_taxiways

    def test_runway_in_taxiway_notam(self):
        """Runway in taxiway NOTAM E text should also be found."""
        obs = parse_notam(SAMPLE_NOTAM_WITH_TAXIWAY)
        assert "22" in obs.affected_runways

    def test_permanent_notam(self):
        obs = parse_notam(SAMPLE_NOTAM_PERMANENT)
        assert obs.permanent is True
        assert obs.effective_to is None

    def test_estimated_end_time(self):
        obs = parse_notam(SAMPLE_NOTAM_EST)
        assert obs.estimated is True
        assert obs.effective_to is not None

    def test_q_line_parsed(self):
        obs = parse_notam(SAMPLE_NOTAM)
        assert obs.q_line is not None
        assert obs.q_line.fir == "KZNY"
        assert obs.q_line.notam_code == "QMRLC"

    def test_runway_and_rwy_dual_keyword(self):
        """RWY 13R AND RWY 31L (two separate RWY keywords) must both be found."""
        notam = """A9001/24 NOTAMN
Q) KZNY/QMRLC/IV/NBO/A/000/999/4038N07356W025
A) KJFK
B) 2406010000
C) 2406012359
E) RWY 13R AND RWY 31L CLOSED FOR WORK IN PROGRESS"""
        obs = parse_notam(notam)
        assert "13R" in obs.affected_runways
        assert "31L" in obs.affected_runways

    def test_missing_header_raises(self):
        with pytest.raises(NOTAMParseError):
            parse_notam("SOME RANDOM TEXT WITHOUT NOTAM HEADER")

    def test_missing_a_field_raises(self):
        bad = "A9999/24 NOTAMN\nB) 2401101000\nE) something"
        with pytest.raises(NOTAMParseError):
            parse_notam(bad)
