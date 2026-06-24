from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from pulse.data_paths import normalized_reviews_path
from pulse.ingestion.models import Review
from pulse.preprocess.cache import load_processed_reviews, save_processed_reviews
from pulse.preprocess.normalize import (
    PreprocessSettings,
    collapse_text,
    contains_emoji,
    contains_non_latin_script,
    normalize_reviews,
    should_keep_review,
    word_count,
)
from pulse.preprocess.pii import PiiSettings
from pulse.preprocess.pipeline import preprocess_reviews_for_run

IST = ZoneInfo("Asia/Kolkata")


def _review(text: str, review_id: str = "r1") -> Review:
    return Review(
        review_id=review_id,
        text=text,
        rating=4,
        timestamp=datetime(2026, 6, 15, tzinfo=IST),
        version="1.0",
        source="playstore",
    )


def test_word_count_requires_eight_words() -> None:
    assert word_count("one two three four five six seven") == 7
    assert word_count("one two three four five six seven eight") == 8


def test_contains_emoji() -> None:
    assert contains_emoji("Great app 👍")
    assert not contains_emoji("Great app for investing")


def test_contains_non_latin_script_rejects_hindi() -> None:
    assert contains_non_latin_script("यह ऐप बहुत अच्छा है और मुझे पसंद है")


def test_should_keep_review_short() -> None:
    settings = PreprocessSettings(min_words=8)
    keep, reason = should_keep_review("too short review here", settings)
    assert not keep
    assert reason == "short"


def test_should_keep_review_emoji() -> None:
    settings = PreprocessSettings(min_words=8)
    text = "This app is really good and helpful for beginners 👍 today"
    keep, reason = should_keep_review(text, settings)
    assert not keep
    assert reason == "emoji"


def test_should_keep_review_accepts_roman_hinglish() -> None:
    settings = PreprocessSettings(min_words=8)
    text = (
        "This application is very helpful for beginners plz download and invest "
        "in mutual funds with a simple and clean interface"
    )
    keep, reason = should_keep_review(text, settings)
    assert keep
    assert reason is None


def test_normalize_reviews_filters_batch() -> None:
    reviews = [
        _review("short text", "short"),
        _review("This app crashes often during market hours very frustrating", "ok"),
        _review("Good app 👍 for beginners who want simple investing experience today", "emoji"),
        _review("यह ऐप बहुत अच्छा है और मुझे पसंद है हमेशा से", "hindi"),
    ]
    cleaned, stats = normalize_reviews(reviews, PreprocessSettings(min_words=8))
    assert len(cleaned) == 1
    assert cleaned[0].review_id == "ok"
    assert stats.dropped_short == 1
    assert stats.dropped_emoji == 1
    assert stats.dropped_script == 1


def test_collapse_text_strips_html_entities() -> None:
    assert collapse_text("foo &amp; bar") == "foo & bar"


def test_processed_cache_roundtrip(tmp_path: object) -> None:
    from pathlib import Path

    root = Path(str(tmp_path))
    settings = PreprocessSettings(min_words=8)
    pii_settings = PiiSettings()
    reviews, _ = normalize_reviews(
        [_review("This is a valid English review with enough words to pass filter", "ok")],
        settings,
    )
    path = normalized_reviews_path(root)
    save_processed_reviews(
        path,
        reviews=reviews,
        run_id="groww:2026-W25",
        settings=settings,
        pii_settings=pii_settings,
        input_count=1,
    )
    loaded = load_processed_reviews(
        path,
        run_id="groww:2026-W25",
        settings=settings,
        pii_settings=pii_settings,
    )
    assert loaded is not None
    assert len(loaded) == 1


def test_preprocess_raises_when_too_few_remain(tmp_path: object) -> None:
    from pathlib import Path

    from pulse.ingestion.errors import TooFewReviewsError

    root = Path(str(tmp_path))
    raw = [_review("short", "s1")]
    with pytest.raises(TooFewReviewsError):
        preprocess_reviews_for_run(
            run_id="groww:2026-W26",
            reviews=raw,
            settings=PreprocessSettings(min_words=8),
            pii_settings=PiiSettings(),
            min_reviews_for_run=50,
            data_root=root,
        )
