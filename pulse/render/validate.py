from __future__ import annotations

from pulse.render.errors import RenderError
from pulse.render.models import DocPayload


def validate_doc_payload(payload: DocPayload) -> None:
    """Validate a plain-text Docs MCP append payload."""
    if not payload.document_id.strip():
        raise RenderError("DocPayload.document_id must be non-empty.")
    if not payload.heading.startswith("## "):
        raise RenderError("DocPayload.heading must start with '## '.")
    if not payload.run_id.strip():
        raise RenderError("DocPayload.run_id must be non-empty.")
    if not payload.content.strip():
        raise RenderError("DocPayload.content must be non-empty.")
