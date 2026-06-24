from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pulse.render.errors import RenderError
from pulse.render.models import DocPayload, EmailPayload


def save_doc_payload(path: Path, payload: DocPayload) -> None:
    _save_json(path, payload.to_dict())


def save_email_payload(path: Path, payload: EmailPayload) -> None:
    _save_json(path, payload.to_dict())


def load_doc_payload(path: Path) -> DocPayload:
    data = _load_json(path)
    return _doc_payload_from_dict(data)


def load_email_payload(path: Path) -> EmailPayload:
    data = _load_json(path)
    return _email_payload_from_dict(data)


def _save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(".json.tmp")
    with temp_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    temp_path.replace(path)


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise RenderError(f"Payload not found: {path}")
    try:
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise RenderError(f"Could not read payload: {path}") from exc
    if not isinstance(data, dict):
        raise RenderError(f"Invalid payload format: {path}")
    return data


def _doc_payload_from_dict(data: dict[str, Any]) -> DocPayload:
    content = data.get("content")
    if not isinstance(content, str):
        raise RenderError("DocPayload missing content string.")
    return DocPayload(
        document_id=str(data.get("document_id", "")),
        heading=str(data.get("heading", "")),
        content=content,
        run_id=str(data.get("run_id", "")),
        content_hash=str(data.get("content_hash", "")),
    )


def _email_payload_from_dict(data: dict[str, Any]) -> EmailPayload:
    to_raw = data.get("to")
    if not isinstance(to_raw, list):
        raise RenderError("EmailPayload missing to list.")
    mode = str(data.get("mode", "draft"))
    if mode not in ("draft", "send"):
        raise RenderError("EmailPayload mode must be 'draft' or 'send'.")
    return EmailPayload(
        to=[str(item) for item in to_raw],
        subject=str(data.get("subject", "")),
        html_body=str(data.get("html_body", "")),
        text_body=str(data.get("text_body", "")),
        run_id=str(data.get("run_id", "")),
        mode=mode,  # type: ignore[arg-type]
        content_hash=str(data.get("content_hash", "")),
    )
