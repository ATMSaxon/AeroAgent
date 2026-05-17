"""
Unit tests for time_window_checker.py

All datetime values are UTC-aware. Hand-computed expected statuses are
documented per test case.

Standard: ICAO Annex 15, 16th edition, 2018 §3.6
Reference: https://www.icao.int/safety/information-management/Pages/Annex15.aspx
"""

import pytest
from datetime import datetime, timedelta, timezone

from aerosafety.tools.time_window_checker import (
    AmbiguousTimezoneError,
    WindowStatus,
    check_time_window,
)

UTC = timezone.utc

# Window: 2024-01-10 10:00 UTC → 2024-01-10 14:00 UTC
WINDOW_START = datetime(2024, 1, 10, 10, 0, tzinfo=UTC)
WINDOW_END   = datetime(2024, 1, 10, 14, 0, tzinfo=UTC)


class TestTimeWindowActive:
    def test_query_inside_window(self):
        """2024-01-10 12:00 UTC is inside [10:00, 14:00) → ACTIVE."""
        q = datetime(2024, 1, 10, 12, 0, tzinfo=UTC)
        result = check_time_window(q, WINDOW_START, WINDOW_END)
        assert result.status == WindowStatus.ACTIVE
        assert result.seconds_until_start is None
        # seconds_until_end = (14:00 - 12:00) = 7200 s
        assert result.seconds_until_end == 7200.0

    def test_query_at_window_start(self):
        """Exactly at window start is ACTIVE (inclusive start)."""
        result = check_time_window(WINDOW_START, WINDOW_START, WINDOW_END)
        assert result.status == WindowStatus.ACTIVE

    def test_query_one_second_before_end(self):
        """One second before window end is still ACTIVE."""
        q = WINDOW_END - timedelta(seconds=1)
        result = check_time_window(q, WINDOW_START, WINDOW_END)
        assert result.status == WindowStatus.ACTIVE
        assert result.seconds_until_end == 1.0


class TestTimeWindowInactive:
    def test_query_before_window(self):
        """
        2024-01-10 09:59 UTC is before window start 10:00 → INACTIVE.
        seconds_until_start = 60 s.
        """
        q = datetime(2024, 1, 10, 9, 59, tzinfo=UTC)
        result = check_time_window(q, WINDOW_START, WINDOW_END)
        assert result.status == WindowStatus.INACTIVE
        assert result.seconds_until_start == 60.0
        assert result.seconds_until_end is None

    def test_query_far_before_window(self):
        q = datetime(2024, 1, 10, 0, 0, tzinfo=UTC)
        result = check_time_window(q, WINDOW_START, WINDOW_END)
        assert result.status == WindowStatus.INACTIVE
        # 10 hours = 36000 seconds
        assert result.seconds_until_start == 36000.0


class TestTimeWindowExpired:
    def test_query_at_window_end(self):
        """
        Exactly at window end is EXPIRED (exclusive end).
        Hand-computed: [start, end) interval, so query == end → EXPIRED.
        """
        result = check_time_window(WINDOW_END, WINDOW_START, WINDOW_END)
        assert result.status == WindowStatus.EXPIRED

    def test_query_after_window(self):
        q = datetime(2024, 1, 10, 14, 1, tzinfo=UTC)
        result = check_time_window(q, WINDOW_START, WINDOW_END)
        assert result.status == WindowStatus.EXPIRED
        assert result.seconds_until_end is None


class TestTimeWindowPermanent:
    def test_permanent_notam_active(self):
        """window_end=None + query after start → PERMANENT."""
        q = datetime(2024, 6, 1, 12, 0, tzinfo=UTC)
        start = datetime(2024, 1, 1, 0, 0, tzinfo=UTC)
        result = check_time_window(q, start, None)
        assert result.status == WindowStatus.PERMANENT

    def test_permanent_notam_not_yet_active(self):
        """window_end=None + query before start → INACTIVE."""
        q = datetime(2023, 12, 31, 23, 0, tzinfo=UTC)
        start = datetime(2024, 1, 1, 0, 0, tzinfo=UTC)
        result = check_time_window(q, start, None)
        assert result.status == WindowStatus.INACTIVE


class TestTimeZoneSafety:
    def test_naive_query_time_raises(self):
        """Naive datetime (no tzinfo) must raise AmbiguousTimezoneError."""
        naive = datetime(2024, 1, 10, 12, 0)  # no tzinfo!
        with pytest.raises(AmbiguousTimezoneError):
            check_time_window(naive, WINDOW_START, WINDOW_END)

    def test_naive_window_start_raises(self):
        q = datetime(2024, 1, 10, 12, 0, tzinfo=UTC)
        naive_start = datetime(2024, 1, 10, 10, 0)  # no tzinfo!
        with pytest.raises(AmbiguousTimezoneError):
            check_time_window(q, naive_start, WINDOW_END)

    def test_non_utc_timezone_raises(self):
        """Non-UTC timezone (e.g. UTC-5) must raise AmbiguousTimezoneError."""
        from datetime import timezone as tz
        eastern = tz(timedelta(hours=-5))
        local_time = datetime(2024, 1, 10, 7, 0, tzinfo=eastern)  # = 12:00 UTC
        with pytest.raises(AmbiguousTimezoneError):
            check_time_window(local_time, WINDOW_START, WINDOW_END)

    def test_window_end_before_start_raises(self):
        """window_end before window_start must raise ValueError."""
        q = datetime(2024, 1, 10, 12, 0, tzinfo=UTC)
        with pytest.raises(ValueError):
            check_time_window(q, WINDOW_END, WINDOW_START)  # reversed!
