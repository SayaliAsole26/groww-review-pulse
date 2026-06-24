from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from pulse.data_paths import default_data_root, normalized_reviews_path
from pulse.ingestion.errors import CacheError
from pulse.ingestion.models import CleanReview
from pulse.preprocess.normalize import PreprocessSettings
from pulse.preprocess.pii import PiiSettings


def _clean_review_to_dict(review: CleanReview) -> dict[str, Any]:
    data = asdict(review)
    data["timestamp"] = review.timestamp.isoformat()
    return data


def _clean_review_from_dict(data: dict[str, Any]) -> CleanReview:
    timestamp_raw = data.get("timestamp")
    if not isinstance(timestamp_raw, str):
        raise CacheError("Processed review record missing timestamp.")

    return CleanReview(
        review_id=str(data["review_id"]),
        text=str(data.get("text", "")),
        rating=int(data["rating"]),
        timestamp=datetime.fromisoformat(timestamp_raw),
        version=data.get("version") if data.get("version") is not None else None,
        source="playstore",
    )


def _preprocess_metadata(
    settings: PreprocessSettings,
    pii_settings: PiiSettings,
) -> dict[str, Any]:
    return {
        "min_words": settings.min_words,
        "reject_non_latin_script": settings.reject_non_latin_script,
        "reject_emoji": settings.reject_emoji,
        "pii_url_mode": pii_settings.url_mode,
    }


def _metadata_matches(
    metadata: dict[str, Any],
    *,
    run_id: str,
    settings: PreprocessSettings,
    pii_settings: PiiSettings,
) -> bool:
    preprocess = metadata.get("preprocess")
    if not isinstance(preprocess, dict):
        return False
    return (
        metadata.get("run_id") == run_id
        and preprocess == _preprocess_metadata(settings, pii_settings)
    )


def save_processed_reviews(
    path: Path,
    *,
    reviews: list[CleanReview],
    run_id: str,
    settings: PreprocessSettings,
    pii_settings: PiiSettings,
    input_count: int,
) -> None:
    """Atomically persist all normalized reviews to ``reviews_normalized.json``."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "metadata": {
            "run_id": run_id,
            "preprocess": _preprocess_metadata(settings, pii_settings),
            "input_count": input_count,
            "count": len(reviews),
            "processed_at": datetime.now().astimezone().isoformat(),
        },
        "reviews": [_clean_review_to_dict(review) for review in reviews],
    }
    temp_path = path.with_suffix(".json.tmp")
    with temp_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    temp_path.replace(path)


def load_processed_reviews(
    path: Path,
    *,
    run_id: str,
    settings: PreprocessSettings,
    pii_settings: PiiSettings,
) -> list[CleanReview] | None:
    if not path.is_file():
        return None

    try:
        with path.open(encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise CacheError(f"Could not read processed cache: {path}") from exc

    if not isinstance(payload, dict):
        raise CacheError(f"Invalid processed cache format: {path}")

    metadata = payload.get("metadata")
    reviews_raw = payload.get("reviews")
    if not isinstance(metadata, dict) or not isinstance(reviews_raw, list):
        raise CacheError(f"Invalid processed cache format: {path}")

    if not _metadata_matches(metadata, run_id=run_id, settings=settings, pii_settings=pii_settings):
        return None

    return [_clean_review_from_dict(item) for item in reviews_raw]


__all__ = [
    "default_data_root",
    "load_processed_reviews",
    "normalized_reviews_path",
    "save_processed_reviews",
]
