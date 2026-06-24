from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from pulse.config import load_config
from pulse.data_paths import gmail_delivery_path
from pulse.delivery.errors import DeliveryError
from pulse.delivery.gmail_delivery import (
    apply_section_anchor_url,
    build_email_body,
    deliver_email_payload,
    gmail_find_by_idempotency_key,
    gmail_send_message,
    resolve_section_anchor_url,
)
from pulse.ingestion.models import EmailMode
from pulse.render.models import EmailPayload, SECTION_ANCHOR_URL_PLACEHOLDER


@pytest.fixture
def sample_email_payload() -> EmailPayload:
    return EmailPayload(
        to=["lead@example.com"],
        subject="Groww Weekly Review Pulse — Week 2026-W25",
        html_body=f'<a href="{SECTION_ANCHOR_URL_PLACEHOLDER}">Read full report</a>',
        text_body=f"Read full report -> {SECTION_ANCHOR_URL_PLACEHOLDER}",
        run_id="groww:2026-W25",
        mode="draft",
        content_hash="emailhash123",
    )


def test_apply_section_anchor_url(sample_email_payload: EmailPayload) -> None:
    url = "https://docs.google.com/document/d/abc/edit"
    updated = apply_section_anchor_url(sample_email_payload, url)
    assert SECTION_ANCHOR_URL_PLACEHOLDER not in updated.text_body
    assert SECTION_ANCHOR_URL_PLACEHOLDER not in updated.html_body
    assert url in updated.text_body
    assert url in updated.html_body


def test_build_email_body_includes_run_id_header() -> None:
    body = build_email_body("Hello", "groww:2026-W25")
    assert "[X-Pulse-Run-Id: groww:2026-W25]" in body


def test_gmail_send_message_creates_draft(
    sample_email_payload: EmailPayload,
    tmp_path: object,
) -> None:
    from pathlib import Path

    client = MagicMock()
    client.create_email_draft.return_value = {
        "status": "success",
        "result": {"id": "draft-1", "message": {"id": "msg-1"}},
    }

    result = gmail_send_message(
        sample_email_payload,
        client=client,
        section_anchor_url="https://docs.google.com/document/d/abc/edit",
        data_root=Path(str(tmp_path)),
    )

    assert result.created is True
    assert result.draft_ids == ["draft-1"]
    assert result.message_ids == ["msg-1"]
    client.create_email_draft.assert_called_once()
    args = client.create_email_draft.call_args[0]
    assert args[0] == "lead@example.com"
    assert "[X-Pulse-Run-Id: groww:2026-W25]" in args[2]


def test_gmail_send_message_is_idempotent(
    sample_email_payload: EmailPayload,
    tmp_path: object,
) -> None:
    from pathlib import Path

    data_root = Path(str(tmp_path))
    client = MagicMock()
    client.create_email_draft.return_value = {
        "status": "success",
        "result": {"id": "draft-1", "message": {"id": "msg-1"}},
    }
    url = "https://docs.google.com/document/d/abc/edit"

    first = gmail_send_message(
        sample_email_payload,
        client=client,
        section_anchor_url=url,
        data_root=data_root,
    )
    second = gmail_send_message(
        sample_email_payload,
        client=client,
        section_anchor_url=url,
        data_root=data_root,
    )

    assert first.created is True
    assert second.created is False
    client.create_email_draft.assert_called_once()
    assert gmail_find_by_idempotency_key("groww:2026-W25", data_root=data_root) is not None


def test_gmail_send_message_rejects_send_mode(sample_email_payload: EmailPayload) -> None:
    client = MagicMock()
    with pytest.raises(DeliveryError, match="only supports draft mode"):
        gmail_send_message(
            sample_email_payload,
            client=client,
            section_anchor_url="https://docs.google.com/document/d/abc/edit",
            mode="send",
        )


def test_resolve_section_anchor_url_from_docs_record(tmp_path: object) -> None:
    from pathlib import Path

    from pulse.delivery.delivery_io import save_docs_delivery_record
    from pulse.delivery.models import DocsDeliveryRecord
    from pulse.data_paths import docs_delivery_path

    data_root = Path(str(tmp_path))
    save_docs_delivery_record(
        docs_delivery_path("groww:2026-W25", data_root),
        DocsDeliveryRecord(
            run_id="groww:2026-W25",
            heading="## Groww — Week 2026-W25",
            document_id="abc",
            section_anchor_url="https://docs.google.com/document/d/abc/edit",
            content_hash="x",
        ),
    )
    url = resolve_section_anchor_url("groww:2026-W25", data_root=data_root)
    assert url.endswith("/abc/edit")


def test_deliver_email_payload_checks_health(
    sample_email_payload: EmailPayload,
    tmp_path: object,
) -> None:
    from pathlib import Path

    config = load_config()
    client = MagicMock()
    client.health.return_value = {"status": "ok", "message": "running"}
    client.create_email_draft.return_value = {
        "status": "success",
        "result": {"id": "draft-1", "message": {"id": "msg-1"}},
    }

    deliver_email_payload(
        sample_email_payload,
        config,
        client=client,
        section_anchor_url="https://docs.google.com/document/d/abc/edit",
        data_root=Path(str(tmp_path)),
    )
    client.health.assert_called_once()
