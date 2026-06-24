from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from pulse.ingestion.errors import CacheError
from pulse.ingestion.models import PulseReport, Theme


def save_report(path: Path, report: PulseReport) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = _report_to_dict(report)
    temp_path = path.with_suffix(".json.tmp")
    with temp_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    temp_path.replace(path)


def load_report(path: Path) -> PulseReport:
    if not path.is_file():
        raise CacheError(f"Report not found: {path}")
    try:
        with path.open(encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise CacheError(f"Could not read report: {path}") from exc
    if not isinstance(payload, dict):
        raise CacheError(f"Invalid report format: {path}")
    return _report_from_dict(payload)


def _theme_to_dict(theme: Theme) -> dict[str, Any]:
    return asdict(theme)


def _theme_from_dict(data: dict[str, Any]) -> Theme:
    return Theme(
        rank=int(data["rank"]),
        title=str(data.get("title", "")),
        summary=str(data.get("summary", "")),
        quotes=[str(q) for q in data.get("quotes", [])],
        action_ideas=[str(a) for a in data.get("action_ideas", [])],
        review_count=int(data.get("review_count", 0)),
        sample_review_ids=[str(rid) for rid in data.get("sample_review_ids", [])],
    )


def _report_to_dict(report: PulseReport) -> dict[str, Any]:
    return {
        "run_id": report.run_id,
        "product": report.product,
        "period_label": report.period_label,
        "themes": [_theme_to_dict(theme) for theme in report.themes],
        "generated_at": report.generated_at.isoformat(),
        "review_count": report.review_count,
    }


def _report_from_dict(data: dict[str, Any]) -> PulseReport:
    themes_raw = data.get("themes")
    if not isinstance(themes_raw, list):
        raise CacheError("Report missing themes list.")
    generated_at_raw = data.get("generated_at")
    if not isinstance(generated_at_raw, str):
        raise CacheError("Report missing generated_at.")
    return PulseReport(
        run_id=str(data["run_id"]),
        product="groww",
        period_label=str(data.get("period_label", "")),
        themes=[_theme_from_dict(item) for item in themes_raw if isinstance(item, dict)],
        generated_at=datetime.fromisoformat(generated_at_raw),
        review_count=int(data.get("review_count", 0)),
    )
