"""Gmail MCP tool wrappers for the hosted server.

Maps architecture tool names to ``HostedMcpClient`` REST calls. Idempotency for
``gmail_find_by_idempotency_key`` is tracked client-side in ``data/gmail_delivery_*.json``.
The hosted server accepts plain-text bodies only via ``POST /create_email_draft``.
"""

from __future__ import annotations

import logging
from pathlib import Path

from pulse.data_paths import gmail_delivery_path
from pulse.delivery.delivery_io import load_gmail_delivery_record, save_gmail_delivery_record
from pulse.delivery.errors import DeliveryError
from pulse.delivery.mcp_client import HostedMcpClient
from pulse.delivery.models import EmailDeliveryResult, GmailDeliveryRecord
from pulse.ingestion.models import EmailMode
from pulse.render.models import EmailPayload, SECTION_ANCHOR_URL_PLACEHOLDER

logger = logging.getLogger(__name__)

PULSE_RUN_ID_HEADER = "X-Pulse-Run-Id"


def gmail_find_by_idempotency_key(
    run_id: str,
    *,
    data_root: Path | None = None,
) -> GmailDeliveryRecord | None:
    """Return a prior email delivery record for this run (client-side idempotency)."""
    return load_gmail_delivery_record(gmail_delivery_path(run_id, data_root))


def apply_section_anchor_url(payload: EmailPayload, section_anchor_url: str) -> EmailPayload:
    """Replace CTA placeholder with the Doc section URL in email bodies."""
    return EmailPayload(
        to=list(payload.to),
        subject=payload.subject,
        html_body=payload.html_body.replace(SECTION_ANCHOR_URL_PLACEHOLDER, section_anchor_url),
        text_body=payload.text_body.replace(SECTION_ANCHOR_URL_PLACEHOLDER, section_anchor_url),
        run_id=payload.run_id,
        mode=payload.mode,
        content_hash=payload.content_hash,
    )


def build_email_body(text_body: str, run_id: str) -> str:
    """Plain-text body for hosted MCP, including run idempotency marker."""
    body = text_body.rstrip()
    return f"{body}\n\n[{PULSE_RUN_ID_HEADER}: {run_id}]\n"


def gmail_create_draft(
    to: str,
    subject: str,
    body: str,
    *,
    client: HostedMcpClient,
) -> tuple[str, str]:
    """Create one Gmail draft via hosted MCP; return (draft_id, message_id)."""
    response = client.create_email_draft(to, subject, body)
    status = str(response.get("status", "")).lower()
    if status != "success":
        raise DeliveryError(f"create_email_draft failed for {to!r}: {response!r}")
    return _extract_draft_ids(response)


def gmail_send_message(
    payload: EmailPayload,
    *,
    client: HostedMcpClient,
    section_anchor_url: str,
    mode: EmailMode | None = None,
    data_root: Path | None = None,
    force: bool = False,
) -> EmailDeliveryResult:
    """Create draft or send teaser email via hosted MCP.

    Current hosted server supports draft creation only (``POST /create_email_draft``).
    """
    effective_mode = mode or payload.mode
    if effective_mode == "send":
        raise DeliveryError(
            "Hosted MCP server only supports draft mode via POST /create_email_draft. "
            "Use --email-mode draft or set groww.email.default_mode: draft."
        )

    prepared = apply_section_anchor_url(payload, section_anchor_url)
    existing = None if force else gmail_find_by_idempotency_key(prepared.run_id, data_root=data_root)
    if existing is not None and existing.content_hash == prepared.content_hash:
        logger.info(
            "Email already delivered for run_id=%s (created=false)",
            prepared.run_id,
        )
        return EmailDeliveryResult(
            run_id=prepared.run_id,
            subject=existing.subject,
            recipients=list(existing.recipients),
            draft_ids=list(existing.draft_ids),
            message_ids=list(existing.message_ids),
            mode=existing.mode,
            created=False,
            section_anchor_url=existing.section_anchor_url,
        )

    if not prepared.to:
        raise DeliveryError("EmailPayload.to must contain at least one recipient.")

    body = build_email_body(prepared.text_body, prepared.run_id)
    draft_ids: list[str] = []
    message_ids: list[str] = []
    for recipient in prepared.to:
        draft_id, message_id = gmail_create_draft(
            recipient,
            prepared.subject,
            body,
            client=client,
        )
        draft_ids.append(draft_id)
        message_ids.append(message_id)

    record = GmailDeliveryRecord(
        run_id=prepared.run_id,
        subject=prepared.subject,
        recipients=list(prepared.to),
        draft_ids=draft_ids,
        message_ids=message_ids,
        mode=effective_mode,
        section_anchor_url=section_anchor_url,
        content_hash=prepared.content_hash,
    )
    save_gmail_delivery_record(gmail_delivery_path(prepared.run_id, data_root), record)
    logger.info("Created Gmail draft(s) for run_id=%s", prepared.run_id)
    return EmailDeliveryResult(
        run_id=prepared.run_id,
        subject=prepared.subject,
        recipients=list(prepared.to),
        draft_ids=draft_ids,
        message_ids=message_ids,
        mode=effective_mode,
        created=True,
        section_anchor_url=section_anchor_url,
    )


def _extract_draft_ids(response: dict[str, object]) -> tuple[str, str]:
    result = response.get("result")
    if not isinstance(result, dict):
        raise DeliveryError(f"create_email_draft response missing result: {response!r}")
    draft_id = str(result.get("id", "")).strip()
    message_raw = result.get("message")
    message_id = ""
    if isinstance(message_raw, dict):
        message_id = str(message_raw.get("id", "")).strip()
    if not draft_id and not message_id:
        raise DeliveryError(f"create_email_draft response missing draft/message id: {response!r}")
    return draft_id or message_id, message_id or draft_id
