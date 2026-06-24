from __future__ import annotations

import logging
from pathlib import Path

from pulse.ingestion.errors import TooFewReviewsError
from pulse.ingestion.models import CleanReview, Review
from pulse.preprocess.cache import (
    load_processed_reviews,
    normalized_reviews_path,
    save_processed_reviews,
)
from pulse.preprocess.normalize import NormalizeStats, PreprocessSettings, normalize_reviews
from pulse.preprocess.pii import PiiSettings, scrub_reviews

logger = logging.getLogger(__name__)


def preprocess_reviews_for_run(
    *,
    run_id: str,
    reviews: list[Review],
    settings: PreprocessSettings,
    pii_settings: PiiSettings,
    min_reviews_for_run: int,
    force_refresh: bool = False,
    data_root: Path | None = None,
) -> tuple[list[CleanReview], NormalizeStats]:
    """Normalize, PII-scrub, and persist to ``data/reviews_normalized.json``."""
    from pulse.data_paths import default_data_root

    root = data_root or default_data_root()
    cache_path = normalized_reviews_path(root)

    if not force_refresh:
        cached = load_processed_reviews(
            cache_path,
            run_id=run_id,
            settings=settings,
            pii_settings=pii_settings,
        )
        if cached is not None:
            logger.info("Loaded %s processed reviews from cache (%s)", len(cached), cache_path)
            if len(cached) < min_reviews_for_run:
                raise TooFewReviewsError(len(cached), min_reviews_for_run)
            stats = NormalizeStats(
                input_count=-1,
                output_count=len(cached),
                dropped_short=0,
                dropped_emoji=0,
                dropped_script=0,
            )
            return cached, stats

    normalized, stats = normalize_reviews(reviews, settings)
    cleaned = scrub_reviews(normalized, pii_settings)
    logger.info(
        "Normalized reviews: kept=%s dropped_short=%s dropped_emoji=%s dropped_script=%s",
        stats.output_count,
        stats.dropped_short,
        stats.dropped_emoji,
        stats.dropped_script,
    )

    if len(cleaned) < min_reviews_for_run:
        raise TooFewReviewsError(len(cleaned), min_reviews_for_run)

    save_processed_reviews(
        cache_path,
        reviews=cleaned,
        run_id=run_id,
        settings=settings,
        pii_settings=pii_settings,
        input_count=stats.input_count,
    )
    logger.info("Saved %s processed reviews to %s", len(cleaned), cache_path)
    return cleaned, stats
