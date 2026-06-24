from __future__ import annotations

from pathlib import Path

from pulse.config import find_project_root

RAW_REVIEWS_FILENAME = "reviews_raw.json"
NORMALIZED_REVIEWS_FILENAME = "reviews_normalized.json"


def default_data_root() -> Path:
    return find_project_root() / "data"


def raw_reviews_path(data_root: Path | None = None) -> Path:
    root = data_root or default_data_root()
    return root / RAW_REVIEWS_FILENAME


def normalized_reviews_path(data_root: Path | None = None) -> Path:
    root = data_root or default_data_root()
    return root / NORMALIZED_REVIEWS_FILENAME


def embeddings_path(run_id: str, data_root: Path | None = None) -> Path:
    safe_id = run_id.replace(":", "_")
    root = data_root or default_data_root()
    return root / f"embeddings_{safe_id}.parquet"


def report_path(run_id: str, data_root: Path | None = None) -> Path:
    safe_id = run_id.replace(":", "_")
    root = data_root or default_data_root()
    return root / f"report_{safe_id}.json"


def doc_payload_path(run_id: str, data_root: Path | None = None) -> Path:
    safe_id = run_id.replace(":", "_")
    root = data_root or default_data_root()
    return root / f"doc_payload_{safe_id}.json"


def email_payload_path(run_id: str, data_root: Path | None = None) -> Path:
    safe_id = run_id.replace(":", "_")
    root = data_root or default_data_root()
    return root / f"email_payload_{safe_id}.json"


def gmail_delivery_path(run_id: str, data_root: Path | None = None) -> Path:
    safe_id = run_id.replace(":", "_")
    root = data_root or default_data_root()
    return root / f"gmail_delivery_{safe_id}.json"


def docs_delivery_path(run_id: str, data_root: Path | None = None) -> Path:
    safe_id = run_id.replace(":", "_")
    root = data_root or default_data_root()
    return root / f"docs_delivery_{safe_id}.json"
