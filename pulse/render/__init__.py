"""Report and email rendering (Phase 3)."""

from pulse.render.doc_report import build_doc_content, build_doc_payload, format_section_heading
from pulse.render.email_teaser import build_email_payload, build_email_subject
from pulse.render.models import DocPayload, EmailPayload, SECTION_ANCHOR_URL_PLACEHOLDER
from pulse.render.pipeline import RenderResult, render_report, render_report_for_run

__all__ = [
    "DocPayload",
    "EmailPayload",
    "RenderResult",
    "SECTION_ANCHOR_URL_PLACEHOLDER",
    "build_doc_content",
    "build_doc_payload",
    "build_email_payload",
    "build_email_subject",
    "format_section_heading",
    "render_report",
    "render_report_for_run",
]
