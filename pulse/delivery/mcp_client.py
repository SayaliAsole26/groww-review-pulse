from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any

from pulse.delivery.errors import DeliveryError, McpAuthError

logger = logging.getLogger(__name__)

DEFAULT_SERVER_URL = "https://mcp-server-production-725c.up.railway.app"
REQUEST_TIMEOUT_SECONDS = 60.0


class HostedMcpClient:
    """HTTP client for the hosted Google MCP server (FastAPI REST API)."""

    def __init__(self, server_url: str, *, api_key: str | None = None) -> None:
        self.server_url = server_url.rstrip("/")
        self.api_key = (api_key or "").strip() or None

    def health(self) -> dict[str, str]:
        """GET / — verify the server is reachable."""
        return self._request_json("GET", "/")

    def append_to_doc(self, doc_id: str, content: str) -> dict[str, Any]:
        """POST /append_to_doc — append plain text to a Google Doc."""
        payload = {"doc_id": doc_id, "content": content}
        return self._request_json("POST", "/append_to_doc", payload=payload)

    def create_email_draft(self, to: str, subject: str, body: str) -> dict[str, Any]:
        """POST /create_email_draft — create a Gmail draft (plain-text body)."""
        payload = {"to": to, "subject": subject, "body": body}
        return self._request_json("POST", "/create_email_draft", payload=payload)

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{self.server_url}{path}"
        headers = {"Accept": "application/json"}
        data: bytes | None = None

        if method.upper() == "POST":
            headers["Content-Type"] = "application/json"
            if self.api_key:
                headers["X-API-Key"] = self.api_key
            data = json.dumps(payload or {}).encode("utf-8")

        request = urllib.request.Request(url, data=data, headers=headers, method=method.upper())
        try:
            with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = _read_error_body(exc)
            if exc.code == 401:
                raise McpAuthError(f"Hosted MCP rejected API key: {detail}") from exc
            raise DeliveryError(f"Hosted MCP {method} {path} failed ({exc.code}): {detail}") from exc
        except urllib.error.URLError as exc:
            raise DeliveryError(f"Could not reach hosted MCP at {self.server_url}: {exc}") from exc

        if not body.strip():
            return {}
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError as exc:
            raise DeliveryError(f"Hosted MCP returned invalid JSON from {path}") from exc
        if not isinstance(parsed, dict):
            raise DeliveryError(f"Hosted MCP returned unexpected response type from {path}")
        return parsed


def _read_error_body(exc: urllib.error.HTTPError) -> str:
    try:
        raw = exc.read().decode("utf-8")
    except OSError:
        return str(exc.reason)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return raw or str(exc.reason)
    if isinstance(data, dict):
        detail = data.get("detail")
        if isinstance(detail, str):
            return detail
        return json.dumps(detail)
    return raw
