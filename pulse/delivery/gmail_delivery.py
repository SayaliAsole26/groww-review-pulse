from __future__ import annotations

from pathlib import Path

from pulse.config import AppConfig
from pulse.data_paths import docs_delivery_path
from pulse.delivery.delivery_io import load_docs_delivery_record
from pulse.delivery.docs_delivery import build_client, check_mcp_health
from pulse.delivery.errors import DeliveryError
from pulse.delivery.gmail_tools import (
    apply_section_anchor_url,
    build_email_body,
    gmail_create_draft,
    gmail_find_by_idempotency_key,
    gmail_send_message,
)
from pulse.delivery.mcp_client import HostedMcpClient
from pulse.delivery.models import EmailDeliveryResult
from pulse.ingestion.models import EmailMode
from pulse.render.models import EmailPayload

__all__ = [
    "apply_section_anchor_url",
    "build_email_body",
    "deliver_email_payload",
    "gmail_create_draft",
    "gmail_find_by_idempotency_key",
    "gmail_send_message",
    "resolve_section_anchor_url",
]


def resolve_section_anchor_url(
    run_id: str,
    *,
    data_root: Path | None = None,
    section_anchor_url: str | None = None,
) -> str:
    if section_anchor_url:
        return section_anchor_url
    docs_record = load_docs_delivery_record(docs_delivery_path(run_id, data_root))
    if docs_record is None or not docs_record.section_anchor_url.strip():
        raise DeliveryError(
            "Docs section URL not found. Run deliver-docs first, or pass section_anchor_url."
        )
    return docs_record.section_anchor_url


def deliver_email_payload(
    payload: EmailPayload,
    config: AppConfig,
    *,
    data_root: Path | None = None,
    force: bool = False,
    mode: EmailMode | None = None,
    section_anchor_url: str | None = None,
    client: HostedMcpClient | None = None,
) -> EmailDeliveryResult:
    """Health-check hosted MCP and create Gmail draft(s) from email payload."""
    mcp_client = client or build_client(config)
    check_mcp_health(mcp_client)
    resolved_url = resolve_section_anchor_url(
        payload.run_id,
        data_root=data_root,
        section_anchor_url=section_anchor_url,
    )
    return gmail_send_message(
        payload,
        client=mcp_client,
        section_anchor_url=resolved_url,
        mode=mode,
        data_root=data_root,
        force=force,
    )
