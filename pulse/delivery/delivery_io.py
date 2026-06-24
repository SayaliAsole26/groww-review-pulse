from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pulse.delivery.errors import DeliveryError
from pulse.delivery.models import DocsDeliveryRecord, GmailDeliveryRecord


def save_docs_delivery_record(path: Path, record: DocsDeliveryRecord) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "run_id": record.run_id,
        "heading": record.heading,
        "document_id": record.document_id,
        "section_anchor_url": record.section_anchor_url,
        "content_hash": record.content_hash,
    }
    temp_path = path.with_suffix(".json.tmp")
    with temp_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    temp_path.replace(path)


def load_docs_delivery_record(path: Path) -> DocsDeliveryRecord | None:
    if not path.is_file():
        return None
    try:
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise DeliveryError(f"Could not read docs delivery record: {path}") from exc
    if not isinstance(data, dict):
        raise DeliveryError(f"Invalid docs delivery record: {path}")
    return _record_from_dict(data)


def _record_from_dict(data: dict[str, Any]) -> DocsDeliveryRecord:
    return DocsDeliveryRecord(
        run_id=str(data.get("run_id", "")),
        heading=str(data.get("heading", "")),
        document_id=str(data.get("document_id", "")),
        section_anchor_url=str(data.get("section_anchor_url", "")),
        content_hash=str(data.get("content_hash", "")),
    )


def save_gmail_delivery_record(path: Path, record: GmailDeliveryRecord) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "run_id": record.run_id,
        "subject": record.subject,
        "recipients": list(record.recipients),
        "draft_ids": list(record.draft_ids),
        "message_ids": list(record.message_ids),
        "mode": record.mode,
        "section_anchor_url": record.section_anchor_url,
        "content_hash": record.content_hash,
    }
    temp_path = path.with_suffix(".json.tmp")
    with temp_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    temp_path.replace(path)


def load_gmail_delivery_record(path: Path) -> GmailDeliveryRecord | None:
    if not path.is_file():
        return None
    try:
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise DeliveryError(f"Could not read gmail delivery record: {path}") from exc
    if not isinstance(data, dict):
        raise DeliveryError(f"Invalid gmail delivery record: {path}")
    return _gmail_record_from_dict(data)


def _gmail_record_from_dict(data: dict[str, Any]) -> GmailDeliveryRecord:
    recipients_raw = data.get("recipients")
    draft_ids_raw = data.get("draft_ids")
    message_ids_raw = data.get("message_ids")
    return GmailDeliveryRecord(
        run_id=str(data.get("run_id", "")),
        subject=str(data.get("subject", "")),
        recipients=[str(item) for item in recipients_raw] if isinstance(recipients_raw, list) else [],
        draft_ids=[str(item) for item in draft_ids_raw] if isinstance(draft_ids_raw, list) else [],
        message_ids=[str(item) for item in message_ids_raw] if isinstance(message_ids_raw, list) else [],
        mode=str(data.get("mode", "draft")),
        section_anchor_url=str(data.get("section_anchor_url", "")),
        content_hash=str(data.get("content_hash", "")),
    )
