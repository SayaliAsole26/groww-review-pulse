"""Hosted Google MCP delivery (Docs + Gmail)."""

from pulse.delivery.docs_delivery import (
    build_client,
    check_mcp_health,
    deliver_doc_payload,
)
from pulse.delivery.docs_tools import (
    build_append_text,
    docs_append_section,
    docs_find_section_by_heading,
    docs_get_document,
    docs_get_heading_link,
)
from pulse.delivery.gmail_delivery import deliver_email_payload, resolve_section_anchor_url
from pulse.delivery.gmail_tools import (
    apply_section_anchor_url,
    build_email_body,
    gmail_create_draft,
    gmail_find_by_idempotency_key,
    gmail_send_message,
)
from pulse.delivery.mcp_client import HostedMcpClient

__all__ = [
    "HostedMcpClient",
    "apply_section_anchor_url",
    "build_append_text",
    "build_client",
    "build_email_body",
    "check_mcp_health",
    "deliver_doc_payload",
    "deliver_email_payload",
    "docs_append_section",
    "docs_find_section_by_heading",
    "docs_get_document",
    "docs_get_heading_link",
    "gmail_create_draft",
    "gmail_find_by_idempotency_key",
    "gmail_send_message",
    "resolve_section_anchor_url",
]
