from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from pulse.config import load_config
from pulse.data_paths import doc_payload_path, email_payload_path
from pulse.ingestion.models import PulseReport, Theme
from pulse.render.doc_report import build_doc_content, build_doc_payload, format_section_heading
from pulse.render.email_teaser import build_email_payload
from pulse.render.models import SECTION_ANCHOR_URL_PLACEHOLDER
from pulse.render.payload_io import load_doc_payload, load_email_payload
from pulse.render.pipeline import render_report
from pulse.render.validate import validate_doc_payload
from pulse.reasoning.report_io import load_report

IST = ZoneInfo("Asia/Kolkata")


@pytest.fixture
def sample_report() -> PulseReport:
    return PulseReport(
        run_id="groww:2026-W25",
        product="groww",
        period_label="Last 12 weeks (rolling)",
        themes=[
            Theme(
                rank=1,
                title="Security and Reliability Concerns",
                summary="Users report missing funds and poor support.",
                quotes=[
                    "paise fastat naka downlod karu chupe tax khup aahet balance achanak negetiv hoto",
                    "Worst customer support ever",
                ],
                action_ideas=["Audit payment processing systems."],
                review_count=118,
                sample_review_ids=["a", "b", "c"],
            ),
            Theme(
                rank=2,
                title="Poor User Experience and Technical Issues",
                summary="Users experience crashes and dashboard bugs.",
                quotes=["also many a times app laggs , get stucked in market timings"],
                action_ideas=["Review technical infrastructure."],
                review_count=127,
                sample_review_ids=["d", "e", "f"],
            ),
            Theme(
                rank=3,
                title="Recent Update Issues",
                summary="Recent redesign worsened navigation.",
                quotes=["The recent redesign has worsened the experience."],
                action_ideas=["Refine recent UI updates."],
                review_count=116,
                sample_review_ids=["g", "h", "i"],
            ),
        ],
        generated_at=datetime(2026, 6, 25, 1, 30, 29, tzinfo=IST),
        review_count=1669,
    )


def test_section_heading_format() -> None:
    heading = format_section_heading("Groww", "2026-W25", timezone="Asia/Kolkata")
    assert heading == "## Groww \u2014 Week 2026-W25 (15 Jun \u2013 21 Jun 2026)"


def test_doc_payload_is_plain_text(sample_report: PulseReport) -> None:
    config = load_config()
    payload = build_doc_payload(
        sample_report,
        groww=config.groww,
        pulse=config.pulse,
    )
    validate_doc_payload(payload)
    assert payload.heading.startswith("## Groww")
    assert "Top themes" in payload.content
    assert "Real user quotes" in payload.content
    assert "Action ideas" in payload.content
    assert "**" not in payload.content
    assert "1. Security and Reliability Concerns" in payload.content
    assert '- "Worst customer support ever"' in payload.content
    assert payload.content == build_doc_content(sample_report, config.pulse)


def test_email_teaser_is_brief_and_excludes_full_quotes(sample_report: PulseReport) -> None:
    config = load_config()
    payload = build_email_payload(sample_report, groww=config.groww)
    text_lines = [line for line in payload.text_body.splitlines() if line.strip()]

    assert payload.subject == "Groww Weekly Review Pulse \u2014 Week 2026-W25"
    assert len(text_lines) <= 15
    assert "Security and Reliability Concerns" in payload.text_body
    assert "paise fastat naka" not in payload.text_body
    assert SECTION_ANCHOR_URL_PLACEHOLDER in payload.text_body
    assert SECTION_ANCHOR_URL_PLACEHOLDER in payload.html_body
    assert "<ul>" in payload.html_body


def test_render_is_deterministic(sample_report: PulseReport) -> None:
    config = load_config()
    first = render_report(sample_report, config)
    second = render_report(sample_report, config)

    assert first.doc_payload.heading == second.doc_payload.heading
    assert first.doc_payload.content_hash == second.doc_payload.content_hash
    assert first.email_payload.content_hash == second.email_payload.content_hash


def test_render_from_saved_report(tmp_path: object, sample_report: PulseReport) -> None:
    from pathlib import Path

    from pulse.reasoning.report_io import save_report

    config = load_config()
    data_root = Path(str(tmp_path))
    report_file = data_root / "report_groww_2026-W25.json"
    save_report(report_file, sample_report)

    loaded = load_report(report_file)
    result = render_report(loaded, config)

    doc_file = doc_payload_path(loaded.run_id, data_root)
    email_file = email_payload_path(loaded.run_id, data_root)
    from pulse.render.pipeline import render_report_for_run

    render_report_for_run(loaded, config, data_root=data_root)

    saved_doc = load_doc_payload(doc_file)
    saved_email = load_email_payload(email_file)
    assert saved_doc.heading == result.doc_payload.heading
    assert saved_email.subject == result.email_payload.subject


def test_render_from_live_report_fixture() -> None:
    from pulse.config import find_project_root
    from pulse.data_paths import report_path

    report_file = report_path("groww:2026-W25", find_project_root() / "data")
    if not report_file.is_file():
        pytest.skip("Live report fixture not present.")

    config = load_config()
    report = load_report(report_file)
    result = render_report(report, config)

    validate_doc_payload(result.doc_payload)
    assert "Top themes" in result.doc_payload.content
    assert len(result.email_payload.text_body.splitlines()) <= 15
