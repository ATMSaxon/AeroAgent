"""
Time-window checker: determines whether a given UTC datetime falls within
an active NOTAM or TAF validity window.

Standard: ICAO Annex 15, 16th edition, 2018 — §3.6 (NOTAM validity)
Reference: https://www.icao.int/safety/information-management/Pages/Annex15.aspx

TIMEZONE SAFETY (critical — CLAUDE.md §8.1, CLAUDE.md §8.3):
    This module is UTC-only. Any naive (timezone-unaware) datetime is
    REJECTED with an explicit AmbiguousTimezoneError.
    Callers MUST pass timezone-aware datetime objects with UTC tzinfo.
    Passing local times without a timezone is a common and dangerous error
    (see ICAO Annex 15 §3.6.2: all NOTAM times are expressed in UTC).

Dependencies (for infra-architect):
    pydantic >= 2.0
    (datetime is stdlib)
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class AmbiguousTimezoneError(ValueError):
    """
    Raised when a datetime without UTC tzinfo is passed.

    ICAO Annex 15 §3.6.2 mandates UTC for all NOTAM times.
    Using local time without explicit UTC conversion is a safety hazard.
    """


class WindowStatus(str, Enum):
    ACTIVE = "ACTIVE"       # query time falls within the window
    INACTIVE = "INACTIVE"   # query time is before the window starts
    EXPIRED = "EXPIRED"     # query time is after the window ends
    PERMANENT = "PERMANENT" # NOTAM has no end time (PERM)


class TimeWindowResult(BaseModel):
    """
    Result of a time-window check.

    Standard: ICAO Annex 15, 16th edition, 2018 — §3.6
    Reference: https://www.icao.int/safety/information-management/Pages/Annex15.aspx
    """
    query_time_utc: datetime
    window_start_utc: datetime
    window_end_utc: datetime | None
    status: WindowStatus
    seconds_until_start: float | None = None  # None if already started
    seconds_until_end: float | None = None    # None if no end or already expired


def _require_utc(dt: datetime, param_name: str) -> None:
    """Raise AmbiguousTimezoneError if dt is naive or non-UTC."""
    if dt.tzinfo is None:
        raise AmbiguousTimezoneError(
            f"Parameter '{param_name}' is a naive datetime (no timezone). "
            "ICAO Annex 15 §3.6.2 requires UTC. "
            "Wrap with datetime(..., tzinfo=timezone.utc) or use datetime.now(timezone.utc)."
        )
    if dt.utcoffset().total_seconds() != 0:
        raise AmbiguousTimezoneError(
            f"Parameter '{param_name}' has a non-UTC timezone offset "
            f"({dt.utcoffset()}). Convert to UTC before calling this function."
        )


def check_time_window(
    query_time: datetime,
    window_start: datetime,
    window_end: datetime | None = None,
) -> TimeWindowResult:
    """
    Determine whether query_time falls within [window_start, window_end).

    All datetimes MUST be UTC-aware. Naive datetimes raise AmbiguousTimezoneError.

    Args:
        query_time:   The moment to check (MUST be UTC-aware).
        window_start: Start of the active window (MUST be UTC-aware).
        window_end:   End of the active window (MUST be UTC-aware), or None
                      for PERMANENT NOTAMs with no expiry.

    Returns:
        TimeWindowResult with ACTIVE / INACTIVE / EXPIRED / PERMANENT status.

    Raises:
        AmbiguousTimezoneError: if any datetime is naive or non-UTC.
        ValueError:             if window_end is before window_start.

    Standard: ICAO Annex 15, 16th edition, 2018 — §3.6
    Reference: https://www.icao.int/safety/information-management/Pages/Annex15.aspx

    Hand-verification (used in unit tests):
        window 2024-01-10 10:00Z to 2024-01-10 14:00Z
          query 2024-01-10 12:00Z → ACTIVE
          query 2024-01-10 09:59Z → INACTIVE (seconds_until_start = 60)
          query 2024-01-10 14:00Z → EXPIRED  (boundary is exclusive)
          query 2024-01-10 14:01Z → EXPIRED
    """
    _require_utc(query_time, "query_time")
    _require_utc(window_start, "window_start")
    if window_end is not None:
        _require_utc(window_end, "window_end")
        if window_end < window_start:
            raise ValueError(
                f"window_end ({window_end.isoformat()}) is before "
                f"window_start ({window_start.isoformat()})"
            )

    if window_end is None:
        # PERMANENT — active from window_start onwards
        if query_time >= window_start:
            status = WindowStatus.PERMANENT
            secs_until_start = None
            secs_until_end = None
        else:
            status = WindowStatus.INACTIVE
            secs_until_start = (window_start - query_time).total_seconds()
            secs_until_end = None
    elif query_time < window_start:
        status = WindowStatus.INACTIVE
        secs_until_start = (window_start - query_time).total_seconds()
        secs_until_end = None
    elif query_time >= window_end:
        status = WindowStatus.EXPIRED
        secs_until_start = None
        secs_until_end = None
    else:
        status = WindowStatus.ACTIVE
        secs_until_start = None
        secs_until_end = (window_end - query_time).total_seconds()

    return TimeWindowResult(
        query_time_utc=query_time,
        window_start_utc=window_start,
        window_end_utc=window_end,
        status=status,
        seconds_until_start=secs_until_start,
        seconds_until_end=secs_until_end,
    )
