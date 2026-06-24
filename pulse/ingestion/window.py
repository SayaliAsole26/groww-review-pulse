from __future__ import annotations

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from pulse.run_id import iso_week_date_range, parse_iso_week


def review_window_bounds(
    iso_week: str,
    review_window_weeks: int,
    timezone: str,
) -> tuple[datetime, datetime]:
    """
    Return inclusive [start, end] for the rolling review window.

    The window spans ``review_window_weeks`` ISO weeks ending on the Sunday of
    ``iso_week``, interpreted in ``timezone`` (typically Asia/Kolkata).
    """
    if review_window_weeks < 1:
        raise ValueError("review_window_weeks must be at least 1.")

    parse_iso_week(iso_week)
    monday, sunday = iso_week_date_range(iso_week, timezone)
    tz = ZoneInfo(timezone)

    window_start_date = monday - timedelta(weeks=review_window_weeks - 1)
    window_start = datetime.combine(window_start_date, time.min, tzinfo=tz)
    window_end = datetime.combine(sunday + timedelta(days=1), time.min, tzinfo=tz) - timedelta(
        microseconds=1
    )
    return window_start, window_end


def review_timestamp_in_window(
    timestamp: datetime,
    window_start: datetime,
    window_end: datetime,
) -> bool:
    """Return whether ``timestamp`` falls within the inclusive window."""
    if timestamp.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware.")
    return window_start <= timestamp <= window_end
