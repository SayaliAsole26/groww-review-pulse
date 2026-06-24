from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from pulse.data_paths import default_data_root, raw_reviews_path
from pulse.ingestion.errors import CacheError
from pulse.ingestion.models import Review


def _review_to_dict(review: Review) -> dict[str, Any]:
    data = asdict(review)
    data["timestamp"] = review.timestamp.isoformat()
    return data


def _review_from_dict(data: dict[str, Any]) -> Review:
    timestamp_raw = data.get("timestamp")
    if not isinstance(timestamp_raw, str):
        raise CacheError("Review record missing timestamp.")

    return Review(
        review_id=str(data["review_id"]),
        text=str(data.get("text", "")),
        rating=int(data["rating"]),
        timestamp=datetime.fromisoformat(timestamp_raw),
        version=data.get("version") if data.get("version") is not None else None,
        source="playstore",
    )


def _metadata_matches(
    metadata: dict[str, Any],
    *,
    run_id: str,
    package_id: str,
    review_window_weeks: int,
) -> bool:
    return (
        metadata.get("run_id") == run_id
        and metadata.get("package_id") == package_id
        and metadata.get("review_window_weeks") == review_window_weeks
    )


def save_reviews_cache(
    path: Path,
    *,
    reviews: list[Review],
    run_id: str,
    package_id: str,
    review_window_weeks: int,
    window_start: datetime,
    window_end: datetime,
) -> None:
    """Atomically persist all raw reviews for the run to ``reviews_raw.json``."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "metadata": {
            "run_id": run_id,
            "package_id": package_id,
            "review_window_weeks": review_window_weeks,
            "window_start": window_start.isoformat(),
            "window_end": window_end.isoformat(),
            "fetched_at": datetime.now(tz=window_start.tzinfo).isoformat(),
            "count": len(reviews),
        },
        "reviews": [_review_to_dict(review) for review in reviews],
    }
    temp_path = path.with_suffix(".json.tmp")
    with temp_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    temp_path.replace(path)


def load_reviews_cache(
    path: Path,
    *,
    run_id: str,
    package_id: str,
    review_window_weeks: int,
) -> list[Review] | None:
    """Load raw reviews when metadata matches; return None on cache miss."""
    if not path.is_file():
        return None

    try:
        with path.open(encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise CacheError(f"Could not read cache file: {path}") from exc

    if not isinstance(payload, dict):
        raise CacheError(f"Invalid cache format: {path}")

    metadata = payload.get("metadata")
    reviews_raw = payload.get("reviews")
    if not isinstance(metadata, dict) or not isinstance(reviews_raw, list):
        raise CacheError(f"Invalid cache format: {path}")

    if not _metadata_matches(
        metadata,
        run_id=run_id,
        package_id=package_id,
        review_window_weeks=review_window_weeks,
    ):
        return None

    return [_review_from_dict(item) for item in reviews_raw]


__all__ = ["default_data_root", "load_reviews_cache", "raw_reviews_path", "save_reviews_cache"]
