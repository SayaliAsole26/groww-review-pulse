from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from pulse.data_paths import raw_reviews_path
from pulse.ingestion.cache import load_reviews_cache, save_reviews_cache
from pulse.ingestion.errors import PlayStoreFetchError, TooFewReviewsError
from pulse.ingestion.models import Review
from pulse.ingestion.playstore import fetch_reviews_from_playstore, stable_review_id
from pulse.ingestion.window import review_timestamp_in_window, review_window_bounds

IST = ZoneInfo("Asia/Kolkata")


def _dt(year: int, month: int, day: int, hour: int = 12) -> datetime:
    return datetime(year, month, day, hour, tzinfo=IST)


def _review(review_id: str, day: int, text: str = "ok") -> Review:
    return Review(
        review_id=review_id,
        text=text,
        rating=4,
        timestamp=_dt(2026, 6, day),
        version="1.0",
        source="playstore",
    )


def test_review_window_bounds_twelve_weeks() -> None:
    start, end = review_window_bounds("2026-W26", 12, "Asia/Kolkata")
    assert start == datetime(2026, 4, 6, 0, 0, tzinfo=IST)
    assert end.day == 28 and end.month == 6 and end.year == 2026


def test_review_timestamp_in_window_inclusive() -> None:
    start, end = review_window_bounds("2026-W26", 4, "Asia/Kolkata")
    assert review_timestamp_in_window(start, start, end)
    assert review_timestamp_in_window(end, start, end)


def test_stable_review_id_deterministic() -> None:
    ts = _dt(2026, 6, 1)
    assert stable_review_id("hello", ts, 5) == stable_review_id("hello", ts, 5)


def test_cache_roundtrip_and_metadata_mismatch(tmp_path: Path) -> None:
    start, end = review_window_bounds("2026-W26", 12, "Asia/Kolkata")
    reviews = [_review("r1", 10)]
    path = raw_reviews_path(tmp_path)
    save_reviews_cache(
        path,
        reviews=reviews,
        run_id="groww:2026-W26",
        package_id="com.nextbillion.groww",
        review_window_weeks=12,
        window_start=start,
        window_end=end,
    )
    loaded = load_reviews_cache(
        path,
        run_id="groww:2026-W26",
        package_id="com.nextbillion.groww",
        review_window_weeks=12,
    )
    assert loaded is not None
    assert len(loaded) == 1
    assert loaded[0].review_id == "r1"

    stale = load_reviews_cache(
        path,
        run_id="groww:2026-W26",
        package_id="com.nextbillion.groww",
        review_window_weeks=8,
    )
    assert stale is None


def _mock_fetch_factory(pages: list[list[dict]]):
    calls = {"index": 0}

    def fetch_page(
        package_id: str,
        *,
        lang: str,
        country: str,
        sort: object,
        count: int,
        continuation_token: object | None,
    ) -> tuple[list[dict], object | None]:
        _ = (package_id, lang, country, sort, count, continuation_token)
        index = calls["index"]
        if index >= len(pages):
            return [], None
        calls["index"] = index + 1
        token = f"token-{index + 1}" if index + 1 < len(pages) else None
        return pages[index], token

    return fetch_page


def test_fetch_filters_by_window_and_dedupes(tmp_path: Path) -> None:
    pages = [
        [
            {
                "reviewId": "a",
                "content": "new",
                "score": 5,
                "at": _dt(2026, 6, 20),
                "reviewCreatedVersion": "2",
            },
            {
                "reviewId": "a",
                "content": "dup",
                "score": 5,
                "at": _dt(2026, 6, 19),
                "reviewCreatedVersion": "2",
            },
            {
                "reviewId": "old",
                "content": "too old",
                "score": 1,
                "at": _dt(2026, 1, 1),
                "reviewCreatedVersion": "1",
            },
        ]
    ]

    reviews = fetch_reviews_from_playstore(
        package_id="com.nextbillion.groww",
        iso_week="2026-W26",
        review_window_weeks=12,
        timezone="Asia/Kolkata",
        min_reviews_for_run=1,
        data_root=tmp_path,
        request_delay_seconds=0,
        fetch_page=_mock_fetch_factory(pages),
    )
    assert len(reviews) == 1
    assert reviews[0].review_id == "a"
    assert reviews[0].text == "new"

    cached = load_reviews_cache(
        raw_reviews_path(tmp_path),
        run_id="groww:2026-W26",
        package_id="com.nextbillion.groww",
        review_window_weeks=12,
    )
    assert cached is not None
    assert len(cached) == 1


def test_fetch_uses_cache_without_force_refresh(tmp_path: Path) -> None:
    pages = [
        [
            {
                "reviewId": "only",
                "content": "cached",
                "score": 4,
                "at": _dt(2026, 6, 15),
            }
        ]
    ]
    fetch_page = _mock_fetch_factory(pages)

    first = fetch_reviews_from_playstore(
        package_id="com.nextbillion.groww",
        iso_week="2026-W25",
        review_window_weeks=12,
        timezone="Asia/Kolkata",
        min_reviews_for_run=1,
        data_root=tmp_path,
        request_delay_seconds=0,
        fetch_page=fetch_page,
    )
    assert len(first) == 1

    # Broken fetch would fail if called again
    def broken_fetch(*args: object, **kwargs: object) -> tuple[list[dict], None]:
        raise RuntimeError("should not fetch")

    second = fetch_reviews_from_playstore(
        package_id="com.nextbillion.groww",
        iso_week="2026-W25",
        review_window_weeks=12,
        timezone="Asia/Kolkata",
        min_reviews_for_run=1,
        data_root=tmp_path,
        request_delay_seconds=0,
        fetch_page=broken_fetch,
    )
    assert len(second) == 1


def test_fetch_too_few_reviews_raises(tmp_path: Path) -> None:
    pages: list[list[dict]] = [[]]
    with pytest.raises(TooFewReviewsError) as exc:
        fetch_reviews_from_playstore(
            package_id="com.nextbillion.groww",
            iso_week="2026-W26",
            review_window_weeks=12,
            timezone="Asia/Kolkata",
            min_reviews_for_run=50,
            enforce_min_reviews=True,
            data_root=tmp_path,
            request_delay_seconds=0,
            fetch_page=_mock_fetch_factory(pages),
        )
    assert exc.value.count == 0
    assert exc.value.minimum == 50


def test_fetch_retries_then_raises(tmp_path: Path) -> None:
    attempts = {"count": 0}

    def flaky_fetch(*args: object, **kwargs: object) -> tuple[list[dict], None]:
        attempts["count"] += 1
        raise ConnectionError("network down")

    with pytest.raises(PlayStoreFetchError):
        fetch_reviews_from_playstore(
            package_id="com.nextbillion.groww",
            iso_week="2026-W26",
            review_window_weeks=12,
            timezone="Asia/Kolkata",
            min_reviews_for_run=1,
            data_root=tmp_path,
            request_delay_seconds=0,
            max_retries=3,
            retry_base_seconds=0,
            fetch_page=flaky_fetch,
        )
    assert attempts["count"] == 3


def test_force_refresh_bypasses_cache(tmp_path: Path) -> None:
    pages_v1 = [
        [{"reviewId": "v1", "content": "one", "score": 3, "at": _dt(2026, 6, 10)}]
    ]
    pages_v2 = [
        [{"reviewId": "v2", "content": "two", "score": 4, "at": _dt(2026, 6, 11)}]
    ]
    call = {"n": 0}

    def switching_fetch(
        package_id: str,
        *,
        lang: str,
        country: str,
        sort: object,
        count: int,
        continuation_token: object | None,
    ) -> tuple[list[dict], None]:
        _ = (package_id, lang, country, sort, count, continuation_token)
        call["n"] += 1
        pages = pages_v1 if call["n"] == 1 else pages_v2
        return pages[0], None

    fetch_reviews_from_playstore(
        package_id="com.nextbillion.groww",
        iso_week="2026-W24",
        review_window_weeks=12,
        timezone="Asia/Kolkata",
        min_reviews_for_run=1,
        data_root=tmp_path,
        request_delay_seconds=0,
        fetch_page=switching_fetch,
    )
    refreshed = fetch_reviews_from_playstore(
        package_id="com.nextbillion.groww",
        iso_week="2026-W24",
        review_window_weeks=12,
        timezone="Asia/Kolkata",
        min_reviews_for_run=1,
        data_root=tmp_path,
        request_delay_seconds=0,
        force_refresh=True,
        fetch_page=switching_fetch,
    )
    assert refreshed[0].review_id == "v2"
