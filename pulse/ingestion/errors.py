"""Ingestion-specific exceptions."""


class IngestionError(Exception):
    """Base error for Play Store ingestion."""


class PlayStoreFetchError(IngestionError):
    """Failed to fetch reviews after retries."""


class TooFewReviewsError(IngestionError):
    """Review count below the configured minimum."""

    def __init__(self, count: int, minimum: int) -> None:
        self.count = count
        self.minimum = minimum
        super().__init__(
            f"Only {count} reviews in window; minimum required is {minimum}. "
            "Try --force-refresh or widen review_window_weeks."
        )


class CacheError(IngestionError):
    """Cached ingestion artifact is missing or invalid."""
