from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pulse.ingestion.models import EmailMode

SECTION_ANCHOR_URL_PLACEHOLDER = "{{SECTION_ANCHOR_URL}}"


@dataclass(frozen=True)
class DocPayload:
    """Plain-text Docs MCP append payload (no rich formatting)."""

    document_id: str
    heading: str
    content: str
    run_id: str
    content_hash: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "heading": self.heading,
            "content": self.content,
            "run_id": self.run_id,
            "content_hash": self.content_hash,
        }


@dataclass(frozen=True)
class EmailPayload:
    to: list[str]
    subject: str
    html_body: str
    text_body: str
    run_id: str
    mode: EmailMode
    content_hash: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "to": list(self.to),
            "subject": self.subject,
            "html_body": self.html_body,
            "text_body": self.text_body,
            "run_id": self.run_id,
            "mode": self.mode,
            "content_hash": self.content_hash,
        }
