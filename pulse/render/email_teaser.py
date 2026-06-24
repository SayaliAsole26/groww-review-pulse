from __future__ import annotations

import hashlib
import html
import json
from typing import Sequence

from pulse.config import GrowwConfig
from pulse.ingestion.models import PulseReport
from pulse.render.models import EmailPayload, SECTION_ANCHOR_URL_PLACEHOLDER
from pulse.run_id import iso_week_from_run_id

EM_DASH = "\u2014"
MAX_TEASER_THEMES = 3


def build_email_subject(display_name: str, iso_week: str) -> str:
    return f"{display_name} Weekly Review Pulse {EM_DASH} Week {iso_week}"


def build_email_payload(
    report: PulseReport,
    *,
    groww: GrowwConfig,
    section_anchor_url: str | None = None,
) -> EmailPayload:
    """Build a short teaser email (headlines only, not the full report)."""
    iso_week = iso_week_from_run_id(report.run_id)
    subject = build_email_subject(groww.display_name, iso_week)
    cta_url = section_anchor_url or SECTION_ANCHOR_URL_PLACEHOLDER
    headlines = _teaser_headlines(report.themes)
    text_body = _build_text_body(headlines, cta_url)
    html_body = _build_html_body(headlines, cta_url)
    content_hash = _content_hash(subject, headlines)
    return EmailPayload(
        to=list(groww.email_recipients),
        subject=subject,
        html_body=html_body,
        text_body=text_body,
        run_id=report.run_id,
        mode=groww.email_default_mode,
        content_hash=content_hash,
    )


def _teaser_headlines(themes: Sequence[object]) -> list[str]:
    headlines: list[str] = []
    for theme in themes[:MAX_TEASER_THEMES]:
        title = str(getattr(theme, "title", "")).strip()
        if title:
            headlines.append(title)
    return headlines


def _build_text_body(headlines: list[str], cta_url: str) -> str:
    lines = [
        "Top themes this week:",
        "",
    ]
    lines.extend(f"- {headline}" for headline in headlines)
    lines.extend(
        [
            "",
            f"Read full report -> {cta_url}",
        ]
    )
    return "\n".join(lines)


def _build_html_body(headlines: list[str], cta_url: str) -> str:
    items = "\n".join(f"<li>{html.escape(headline)}</li>" for headline in headlines)
    safe_url = html.escape(cta_url, quote=True)
    return (
        "<p>Top themes this week:</p>\n"
        f"<ul>\n{items}\n</ul>\n"
        f'<p><a href="{safe_url}">Read full report</a></p>'
    )


def _content_hash(subject: str, headlines: list[str]) -> str:
    canonical = {"subject": subject, "headlines": headlines}
    payload = json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
