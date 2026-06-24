from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from pulse.ingestion.models import ProductName

ISO_WEEK_PATTERN = re.compile(r"^(\d{4})-W(\d{2})$")
GROWW_PACKAGE_ID = "com.nextbillion.groww"
DEFAULT_TIMEZONE = "Asia/Kolkata"


class RunIdError(ValueError):
    """Invalid ISO week or run identifier."""


def parse_iso_week(iso_week: str) -> tuple[int, int]:
    """Parse ``2026-W25`` into ISO year and week number."""
    match = ISO_WEEK_PATTERN.match(iso_week.strip())
    if not match:
        raise RunIdError(f"Invalid ISO week format: {iso_week!r}. Expected YYYY-Www.")

    year = int(match.group(1))
    week = int(match.group(2))
    if week < 1 or week > 53:
        raise RunIdError(f"ISO week out of range: {iso_week!r}.")

    # Validate calendar week exists (e.g. reject 2021-W53 if invalid)
    try:
        date.fromisocalendar(year, week, 1)
    except ValueError as exc:
        raise RunIdError(f"Invalid ISO week: {iso_week!r}.") from exc

    return year, week


def format_iso_week(year: int, week: int) -> str:
    return f"{year}-W{week:02d}"


def current_iso_week_in_timezone(timezone: str = DEFAULT_TIMEZONE) -> tuple[int, int]:
    """Return ISO (year, week) for *now* in the given timezone."""
    now = datetime.now(ZoneInfo(timezone))
    iso = now.isocalendar()
    return iso.year, iso.week


def make_run_id(product: ProductName, year: int, week: int) -> str:
    return f"{product}:{format_iso_week(year, week)}"


def run_id_from_iso_week(product: ProductName, iso_week: str) -> str:
    year, week = parse_iso_week(iso_week)
    return make_run_id(product, year, week)


def sanitize_run_id_for_path(run_id: str) -> str:
    """Filesystem-safe directory name for ``run_id`` (Windows disallows ``:``)."""
    return run_id.replace(":", "_")


def iso_week_from_run_id(run_id: str) -> str:
    """Extract ``2026-W25`` from ``groww:2026-W25``."""
    if ":" not in run_id:
        raise RunIdError(f"Invalid run_id format: {run_id!r}.")
    _, iso_week = run_id.split(":", 1)
    parse_iso_week(iso_week)
    return iso_week


def iso_week_date_range(
    iso_week: str,
    timezone: str = DEFAULT_TIMEZONE,
) -> tuple[date, date]:
    """Return Monday–Sunday dates for an ISO week (calendar dates in local terms)."""
    year, week = parse_iso_week(iso_week)
    monday = date.fromisocalendar(year, week, 1)
    sunday = monday + timedelta(days=6)
    _ = ZoneInfo(timezone)  # reserved for future IST-boundary helpers
    return monday, sunday


def resolve_run_id(
    product: ProductName,
    iso_week: str | None = None,
    timezone: str = DEFAULT_TIMEZONE,
) -> str:
    """Build run_id from explicit ISO week or the current week in *timezone*."""
    if iso_week is None:
        year, week = current_iso_week_in_timezone(timezone)
        return make_run_id(product, year, week)
    return run_id_from_iso_week(product, iso_week)
