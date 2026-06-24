from __future__ import annotations

import hashlib
import json
from datetime import date

from pulse.config import GrowwConfig, PulseConfig
from pulse.ingestion.models import PulseReport
from pulse.render.models import DocPayload
from pulse.run_id import iso_week_from_run_id, iso_week_date_range

EM_DASH = "\u2014"
EN_DASH = "\u2013"


def format_section_heading(
    display_name: str,
    iso_week: str,
    *,
    timezone: str,
) -> str:
    """Build the idempotency-critical Docs section heading."""
    monday, sunday = iso_week_date_range(iso_week, timezone)
    date_range = f"{_format_day_month(monday)} {EN_DASH} {_format_day_month_year(sunday)}"
    return f"## {display_name} {EM_DASH} Week {iso_week} ({date_range})"


def build_doc_payload(
    report: PulseReport,
    *,
    groww: GrowwConfig,
    pulse: PulseConfig,
) -> DocPayload:
    """Convert a PulseReport into a plain-text Docs MCP append payload."""
    iso_week = iso_week_from_run_id(report.run_id)
    heading = format_section_heading(
        groww.display_name,
        iso_week,
        timezone=pulse.timezone,
    )
    content = build_doc_content(report, pulse)
    content_hash = _content_hash(heading, content)
    return DocPayload(
        document_id=groww.doc_id,
        heading=heading,
        content=content,
        run_id=report.run_id,
        content_hash=content_hash,
    )


def build_doc_content(report: PulseReport, pulse: PulseConfig) -> str:
    """Render the weekly report as plain text (no rich formatting)."""
    sections = [
        f"Period: {report.period_label}",
        "",
        "Top themes",
        "",
        *_theme_lines(report),
        "",
        "Real user quotes",
        "",
        *_quote_lines(report),
        "",
        "Action ideas",
        "",
        *_action_lines(report),
        "",
        _footer_text(report, pulse),
    ]
    return "\n".join(sections)


def _theme_lines(report: PulseReport) -> list[str]:
    return [
        (
            f"{index}. {theme.title} {EN_DASH} {theme.summary} "
            f"({theme.review_count} reviews)"
        )
        for index, theme in enumerate(report.themes, start=1)
    ]


def _quote_lines(report: PulseReport) -> list[str]:
    return [f'- "{quote}"' for quote in _collect_quotes(report)]


def _action_lines(report: PulseReport) -> list[str]:
    lines: list[str] = []
    index = 1
    for theme in report.themes:
        if not theme.action_ideas:
            continue
        lines.append(f"{index}. {theme.title} {EN_DASH} {theme.action_ideas[0]}")
        index += 1
    return lines


def _collect_quotes(report: PulseReport) -> list[str]:
    seen: set[str] = set()
    quotes: list[str] = []
    for theme in report.themes:
        for quote in theme.quotes:
            normalized = quote.strip()
            if normalized and normalized not in seen:
                seen.add(normalized)
                quotes.append(normalized)
    return quotes


def _footer_text(report: PulseReport, pulse: PulseConfig) -> str:
    generated = report.generated_at.astimezone()
    return (
        f"Reviews analyzed: {report.review_count} | "
        f"Window: {pulse.review_window_weeks} weeks | "
        f"Generated: {generated.strftime('%d %b %Y %H:%M %Z')}"
    )


def _format_day_month(value: date) -> str:
    return f"{value.day} {value.strftime('%b')}"


def _format_day_month_year(value: date) -> str:
    return f"{value.day} {value.strftime('%b')} {value.year}"


def _content_hash(heading: str, content: str) -> str:
    canonical = {"heading": heading, "content": content}
    payload = json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
