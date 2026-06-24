from __future__ import annotations

import os
from pathlib import Path
from pulse.config import AppConfig
from pulse.delivery.docs_tools import (
    build_append_text,
    docs_append_section,
    docs_find_section_by_heading,
    docs_get_heading_link,
)
from pulse.delivery.errors import DeliveryError
from pulse.delivery.mcp_client import HostedMcpClient
from pulse.delivery.models import AppendSectionResult
from pulse.render.models import DocPayload

__all__ = [
    "build_append_text",
    "build_client",
    "check_mcp_health",
    "deliver_doc_payload",
    "docs_append_section",
    "docs_find_section_by_heading",
    "docs_get_heading_link",
]


def build_client(config: AppConfig) -> HostedMcpClient:
    return HostedMcpClient(
        config.pulse.mcp.server_url,
        api_key=os.environ.get("MCP_API_KEY", "").strip() or None,
    )


def check_mcp_health(client: HostedMcpClient) -> dict[str, str]:
    """Verify hosted MCP server is up (`GET /`)."""
    response = client.health()
    status = str(response.get("status", "")).lower()
    if status != "ok":
        raise DeliveryError(f"Hosted MCP health check failed: {response!r}")
    return {str(k): str(v) for k, v in response.items()}


def deliver_doc_payload(
    payload: DocPayload,
    config: AppConfig,
    *,
    data_root: Path | None = None,
    force: bool = False,
    client: HostedMcpClient | None = None,
) -> AppendSectionResult:
    """Health-check hosted MCP and append the doc payload."""
    mcp_client = client or build_client(config)
    check_mcp_health(mcp_client)
    return docs_append_section(
        payload,
        client=mcp_client,
        data_root=data_root,
        force=force,
    )
