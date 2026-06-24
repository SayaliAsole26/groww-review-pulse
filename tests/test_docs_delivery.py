from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from pulse.config import load_config
from pulse.delivery.docs_delivery import (
    build_append_text,
    deliver_doc_payload,
    docs_append_section,
    docs_find_section_by_heading,
    docs_get_heading_link,
)
from pulse.delivery.errors import DeliveryError
from pulse.render.models import DocPayload


@pytest.fixture
def sample_doc_payload() -> DocPayload:
    return DocPayload(
        document_id="abc123doc",
        heading="## Groww — Week 2026-W25 (15 Jun – 21 Jun 2026)",
        content="Period: Last 12 weeks (rolling)\n\nTop themes\n\n1. Example",
        run_id="groww:2026-W25",
        content_hash="hash123",
    )


def test_build_append_text_includes_heading_and_content() -> None:
    text = build_append_text("## Heading", "Body line")
    assert text.startswith("## Heading\n\nBody line")
    assert text.endswith("\n\n")


def test_docs_get_heading_link() -> None:
    url = docs_get_heading_link("abc123", "## Heading")
    assert url == "https://docs.google.com/document/d/abc123/edit"


def test_docs_append_section_calls_hosted_api(
    sample_doc_payload: DocPayload,
    tmp_path: object,
) -> None:
    from pathlib import Path

    client = MagicMock()
    client.append_to_doc.return_value = {"status": "success", "result": {}}

    result = docs_append_section(
        sample_doc_payload,
        client=client,
        data_root=Path(str(tmp_path)),
    )

    assert result.inserted is True
    assert "abc123doc" in result.section_anchor_url
    client.append_to_doc.assert_called_once()
    args = client.append_to_doc.call_args[0]
    assert args[0] == "abc123doc"
    assert sample_doc_payload.heading in args[1]
    assert sample_doc_payload.content in args[1]


def test_docs_append_section_is_idempotent(
    sample_doc_payload: DocPayload,
    tmp_path: object,
) -> None:
    from pathlib import Path

    data_root = Path(str(tmp_path))
    client = MagicMock()
    client.append_to_doc.return_value = {"status": "success", "result": {}}

    first = docs_append_section(sample_doc_payload, client=client, data_root=data_root)
    second = docs_append_section(sample_doc_payload, client=client, data_root=data_root)

    assert first.inserted is True
    assert second.inserted is False
    assert second.section_anchor_url == first.section_anchor_url
    client.append_to_doc.assert_called_once()


def test_docs_find_section_by_heading(
    sample_doc_payload: DocPayload,
    tmp_path: object,
) -> None:
    from pathlib import Path

    data_root = Path(str(tmp_path))
    client = MagicMock()
    client.append_to_doc.return_value = {"status": "success", "result": {}}
    docs_append_section(sample_doc_payload, client=client, data_root=data_root)

    record = docs_find_section_by_heading(
        sample_doc_payload.run_id,
        sample_doc_payload.heading,
        data_root=data_root,
    )
    assert record is not None
    assert record.content_hash == sample_doc_payload.content_hash


def test_deliver_doc_payload_checks_health(sample_doc_payload: DocPayload) -> None:
    config = load_config()
    client = MagicMock()
    client.health.return_value = {"status": "ok", "message": "Google MCP Server is running"}
    client.append_to_doc.return_value = {"status": "success", "result": {}}

    deliver_doc_payload(sample_doc_payload, config, client=client)
    client.health.assert_called_once()


def test_deliver_doc_payload_rejects_placeholder_doc_id(
    sample_doc_payload: DocPayload,
) -> None:
    config = load_config()
    client = MagicMock()
    client.health.return_value = {"status": "ok", "message": "running"}
    bad_payload = DocPayload(
        document_id="REPLACE_WITH_STAGING_OR_PROD_DOC_ID",
        heading=sample_doc_payload.heading,
        content=sample_doc_payload.content,
        run_id=sample_doc_payload.run_id,
        content_hash=sample_doc_payload.content_hash,
    )

    with pytest.raises(DeliveryError, match="placeholder"):
        deliver_doc_payload(bad_payload, config, client=client)


def test_load_config_includes_mcp_server_url() -> None:
    config = load_config()
    assert config.pulse.mcp.server_url == "https://mcp-server-production-725c.up.railway.app"
