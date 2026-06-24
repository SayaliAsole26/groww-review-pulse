from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pulse.config import AppConfig
from pulse.ingestion.models import PulseReport
from pulse.render.doc_report import build_doc_payload
from pulse.render.email_teaser import build_email_payload
from pulse.render.models import DocPayload, EmailPayload
from pulse.render.validate import validate_doc_payload


@dataclass(frozen=True)
class RenderResult:
    doc_payload: DocPayload
    email_payload: EmailPayload


def render_report(
    report: PulseReport,
    config: AppConfig,
    *,
    section_anchor_url: str | None = None,
) -> RenderResult:
    """Build validated Doc and email payloads from a PulseReport."""
    doc_payload = build_doc_payload(
        report,
        groww=config.groww,
        pulse=config.pulse,
    )
    validate_doc_payload(doc_payload)
    email_payload = build_email_payload(
        report,
        groww=config.groww,
        section_anchor_url=section_anchor_url,
    )
    return RenderResult(doc_payload=doc_payload, email_payload=email_payload)


def render_report_for_run(
    report: PulseReport,
    config: AppConfig,
    *,
    data_root: Path | None = None,
    section_anchor_url: str | None = None,
) -> RenderResult:
    """Render and persist Doc/email payloads for a run."""
    from pulse.data_paths import doc_payload_path, email_payload_path
    from pulse.render.payload_io import save_doc_payload, save_email_payload

    result = render_report(
        report,
        config,
        section_anchor_url=section_anchor_url,
    )
    save_doc_payload(doc_payload_path(report.run_id, data_root), result.doc_payload)
    save_email_payload(email_payload_path(report.run_id, data_root), result.email_payload)
    return result
