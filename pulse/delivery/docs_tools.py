"""Google Docs MCP tool wrappers for the hosted server.

Maps architecture tool names to ``HostedMcpClient`` REST calls. Idempotency for
``docs_find_section_by_heading`` is tracked client-side in ``data/docs_delivery_*.json``.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from pulse.data_paths import docs_delivery_path
from pulse.delivery.delivery_io import load_docs_delivery_record, save_docs_delivery_record
from pulse.delivery.errors import DeliveryError
from pulse.delivery.mcp_client import HostedMcpClient
from pulse.delivery.models import AppendSectionResult, DocsDeliveryRecord
from pulse.render.models import DocPayload

logger = logging.getLogger(__name__)

DOC_URL_TEMPLATE = "https://docs.google.com/document/d/{doc_id}/edit"


def docs_get_document(
    document_id: str,
    *,
    client: HostedMcpClient,
) -> dict[str, Any]:
    """Fetch doc metadata and existing headings.

    Not exposed by the current hosted REST API (``POST /append_to_doc`` only).
    """
    _ = (document_id, client)
    raise DeliveryError(
        "docs_get_document is not available on the hosted MCP server; "
        "use client-side docs_delivery records for idempotency."
    )


def docs_get_heading_link(document_id: str, heading: str) -> str:
    """Return a browser URL for the target Google Doc.

    The hosted server appends plain text only; heading-specific anchors are not
    available without a Docs read API, so we link to the document edit view.
    """
    _ = heading
    return DOC_URL_TEMPLATE.format(doc_id=document_id)


def docs_find_section_by_heading(
    run_id: str,
    heading: str,
    *,
    data_root: Path | None = None,
) -> DocsDeliveryRecord | None:
    """Lookup a prior section delivery by exact heading text (client-side idempotency)."""
    record = load_docs_delivery_record(docs_delivery_path(run_id, data_root))
    if record is None:
        return None
    if record.heading != heading:
        return None
    return record


def build_append_text(heading: str, content: str) -> str:
    return f"{heading}\n\n{content.rstrip()}\n\n"


def docs_append_section(
    payload: DocPayload,
    *,
    client: HostedMcpClient,
    data_root: Path | None = None,
    force: bool = False,
) -> AppendSectionResult:
    """Append heading + plain-text content via hosted MCP ``POST /append_to_doc``."""
    _validate_doc_id(payload.document_id)

    existing = None if force else docs_find_section_by_heading(
        payload.run_id,
        payload.heading,
        data_root=data_root,
    )
    if existing is not None:
        logger.info(
            "Docs section already delivered for run_id=%s (inserted=false)",
            payload.run_id,
        )
        return AppendSectionResult(
            run_id=payload.run_id,
            heading=payload.heading,
            section_anchor_url=existing.section_anchor_url,
            inserted=False,
            document_id=payload.document_id,
        )

    append_text = build_append_text(payload.heading, payload.content)
    response = client.append_to_doc(payload.document_id, append_text)
    status = str(response.get("status", "")).lower()
    if status != "success":
        raise DeliveryError(f"append_to_doc failed: {response!r}")

    section_url = docs_get_heading_link(payload.document_id, payload.heading)
    record = DocsDeliveryRecord(
        run_id=payload.run_id,
        heading=payload.heading,
        document_id=payload.document_id,
        section_anchor_url=section_url,
        content_hash=payload.content_hash,
    )
    save_docs_delivery_record(docs_delivery_path(payload.run_id, data_root), record)
    logger.info("Appended docs section for run_id=%s", payload.run_id)
    return AppendSectionResult(
        run_id=payload.run_id,
        heading=payload.heading,
        section_anchor_url=section_url,
        inserted=True,
        document_id=payload.document_id,
    )


def _validate_doc_id(doc_id: str) -> None:
    if not doc_id.strip():
        raise DeliveryError("groww.google.doc_id is empty.")
    if "REPLACE_WITH" in doc_id:
        raise DeliveryError(
            "groww.google.doc_id is still a placeholder; set a real Google Doc ID before delivery."
        )
