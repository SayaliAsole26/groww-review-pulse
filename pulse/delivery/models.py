from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AppendSectionResult:
    run_id: str
    heading: str
    section_anchor_url: str
    inserted: bool
    document_id: str


@dataclass(frozen=True)
class DocsDeliveryRecord:
    run_id: str
    heading: str
    document_id: str
    section_anchor_url: str
    content_hash: str


@dataclass(frozen=True)
class EmailDeliveryResult:
    run_id: str
    subject: str
    recipients: list[str]
    draft_ids: list[str]
    message_ids: list[str]
    mode: str
    created: bool
    section_anchor_url: str


@dataclass(frozen=True)
class GmailDeliveryRecord:
    run_id: str
    subject: str
    recipients: list[str]
    draft_ids: list[str]
    message_ids: list[str]
    mode: str
    section_anchor_url: str
    content_hash: str
