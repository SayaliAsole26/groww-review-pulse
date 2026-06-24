from __future__ import annotations

import hashlib
import logging
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from google_play_scraper import Sort
from google_play_scraper import reviews as play_reviews
from google_play_scraper.exceptions import NotFoundError

from pulse.ingestion.cache import (
    default_data_root,
    load_reviews_cache,
    raw_reviews_path,
    save_reviews_cache,
)
from pulse.ingestion.errors import PlayStoreFetchError, TooFewReviewsError
from pulse.ingestion.models import Review
from pulse.ingestion.window import review_timestamp_in_window, review_window_bounds
from pulse.run_id import iso_week_from_run_id

logger = logging.getLogger(__name__)

DEFAULT_LANG = "en"
DEFAULT_COUNTRY = "in"
DEFAULT_BATCH_SIZE = 200
DEFAULT_REQUEST_DELAY_SECONDS = 1.0
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_BASE_SECONDS = 2.0

FetchPageResult = tuple[list[dict[str, Any]], Any | None]
FetchPageFn = Callable[..., FetchPageResult]


def stable_review_id(text: str, timestamp: datetime, rating: int) -> str:
    """Fallback ID when Play Store does not provide a stable reviewId."""
    payload = f"{text}|{timestamp.isoformat()}|{rating}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _ensure_aware(timestamp: datetime, timezone: str) -> datetime:
    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=ZoneInfo(timezone))
    return timestamp


def _map_scraper_review(raw: dict[str, Any], timezone: str) -> Review | None:
    at = raw.get("at")
    if not isinstance(at, datetime):
        return None

    text = str(raw.get("content") or "").strip()
    rating = int(raw.get("score", 0))
    review_id = raw.get("reviewId")
    if not review_id:
        review_id = stable_review_id(text, at, rating)

    version = raw.get("reviewCreatedVersion")
    version_str = str(version) if version is not None else None

    return Review(
        review_id=str(review_id),
        text=text,
        rating=rating,
        timestamp=_ensure_aware(at, timezone),
        version=version_str,
        source="playstore",
    )


def _dedupe_reviews(reviews: list[Review]) -> list[Review]:
    """Keep the first occurrence per review_id (newest-first ordering)."""
    seen: dict[str, Review] = {}
    for review in reviews:
        if review.review_id not in seen:
            seen[review.review_id] = review
    return list(seen.values())


def _fetch_page_with_retry(
    fetch_page: FetchPageFn,
    *,
    package_id: str,
    lang: str,
    country: str,
    batch_size: int,
    continuation_token: Any | None,
    max_retries: int,
    retry_base_seconds: float,
) -> FetchPageResult:
    last_error: Exception | None = None
    for attempt in range(max_retries):
        try:
            return fetch_page(
                package_id,
                lang=lang,
                country=country,
                sort=Sort.NEWEST,
                count=batch_size,
                continuation_token=continuation_token,
            )
        except NotFoundError as exc:
            raise PlayStoreFetchError(
                f"Play Store app not found for package_id={package_id!r}."
            ) from exc
        except Exception as exc:
            last_error = exc
            if attempt == max_retries - 1:
                break
            sleep_seconds = retry_base_seconds * (2**attempt)
            logger.warning(
                "Play Store fetch failed (attempt %s/%s); retrying in %.1fs: %s",
                attempt + 1,
                max_retries,
                sleep_seconds,
                exc,
            )
            time.sleep(sleep_seconds)

    raise PlayStoreFetchError(
        f"Play Store fetch failed after {max_retries} attempts."
    ) from last_error


def fetch_reviews_from_playstore(
    *,
    package_id: str,
    iso_week: str,
    review_window_weeks: int,
    timezone: str,
    min_reviews_for_run: int = 0,
    enforce_min_reviews: bool = False,
    force_refresh: bool = False,
    data_root: Path | None = None,
    lang: str = DEFAULT_LANG,
    country: str = DEFAULT_COUNTRY,
    batch_size: int = DEFAULT_BATCH_SIZE,
    request_delay_seconds: float = DEFAULT_REQUEST_DELAY_SECONDS,
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_base_seconds: float = DEFAULT_RETRY_BASE_SECONDS,
    fetch_page: FetchPageFn | None = None,
) -> list[Review]:
    """
    Fetch Groww Play Store reviews for the rolling window of ``iso_week``.

    Uses on-disk cache at ``data/reviews_raw.json`` unless
    ``force_refresh`` is True or cache metadata does not match.
    """
    from pulse.run_id import run_id_from_iso_week

    run_id = run_id_from_iso_week("groww", iso_week)
    root = data_root or default_data_root()
    cache_path = raw_reviews_path(root)

    if not force_refresh:
        cached = load_reviews_cache(
            cache_path,
            run_id=run_id,
            package_id=package_id,
            review_window_weeks=review_window_weeks,
        )
        if cached is not None:
            logger.info("Loaded %s reviews from cache (%s)", len(cached), cache_path)
            if enforce_min_reviews and len(cached) < min_reviews_for_run:
                raise TooFewReviewsError(len(cached), min_reviews_for_run)
            return cached

    window_start, window_end = review_window_bounds(iso_week, review_window_weeks, timezone)
    page_fetcher = fetch_page or play_reviews

    collected: list[Review] = []
    continuation_token: Any | None = None
    stop_pagination = False

    logger.info(
        "Fetching Play Store reviews for %s (%s to %s)",
        package_id,
        window_start.isoformat(),
        window_end.isoformat(),
    )

    while not stop_pagination:
        batch, continuation_token = _fetch_page_with_retry(
            page_fetcher,
            package_id=package_id,
            lang=lang,
            country=country,
            batch_size=batch_size,
            continuation_token=continuation_token,
            max_retries=max_retries,
            retry_base_seconds=retry_base_seconds,
        )

        if not batch:
            break

        batch_timestamps: list[datetime] = []
        for raw in batch:
            review = _map_scraper_review(raw, timezone)
            if review is None:
                continue
            batch_timestamps.append(review.timestamp)
            if review_timestamp_in_window(review.timestamp, window_start, window_end):
                collected.append(review)

        if batch_timestamps:
            oldest_in_batch = min(batch_timestamps)
            if oldest_in_batch < window_start:
                stop_pagination = True

        if continuation_token is None:
            break

        if request_delay_seconds > 0:
            time.sleep(request_delay_seconds)

    reviews = _dedupe_reviews(collected)
    reviews.sort(key=lambda review: review.timestamp, reverse=True)

    save_reviews_cache(
        cache_path,
        reviews=reviews,
        run_id=run_id,
        package_id=package_id,
        review_window_weeks=review_window_weeks,
        window_start=window_start,
        window_end=window_end,
    )
    logger.info("Saved %s reviews to cache (%s)", len(reviews), cache_path)

    if enforce_min_reviews and len(reviews) < min_reviews_for_run:
        raise TooFewReviewsError(len(reviews), min_reviews_for_run)

    return reviews


def fetch_reviews_for_run(
    *,
    run_id: str,
    package_id: str,
    review_window_weeks: int,
    timezone: str,
    min_reviews_for_run: int = 0,
    enforce_min_reviews: bool = False,
    force_refresh: bool = False,
    data_root: Path | None = None,
    **kwargs: Any,
) -> list[Review]:
    """Convenience wrapper that derives ``iso_week`` from ``run_id``."""
    iso_week = iso_week_from_run_id(run_id)
    return fetch_reviews_from_playstore(
        package_id=package_id,
        iso_week=iso_week,
        review_window_weeks=review_window_weeks,
        timezone=timezone,
        min_reviews_for_run=min_reviews_for_run,
        enforce_min_reviews=enforce_min_reviews,
        force_refresh=force_refresh,
        data_root=data_root,
        **kwargs,
    )
