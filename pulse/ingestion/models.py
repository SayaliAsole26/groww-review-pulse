from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

ProductName = Literal["groww"]
ReviewSource = Literal["playstore"]
EmailMode = Literal["draft", "send"]


@dataclass(frozen=True)
class Review:
    """Raw review from Google Play Store."""

    review_id: str
    text: str
    rating: int
    timestamp: datetime
    version: str | None
    source: ReviewSource = "playstore"


@dataclass(frozen=True)
class CleanReview:
    """Normalized review after preprocessing and PII scrubbing."""

    review_id: str
    text: str
    rating: int
    timestamp: datetime
    version: str | None
    source: ReviewSource = "playstore"


@dataclass(frozen=True)
class RunContext:
    """Execution context for a single pulse run."""

    run_id: str
    product: ProductName
    iso_week: str
    timezone: str
    review_window_weeks: int
    started_at: datetime


@dataclass(frozen=True)
class Theme:
    """Clustered theme with validated quotes and action ideas."""

    rank: int
    title: str
    summary: str
    quotes: list[str]
    action_ideas: list[str]
    review_count: int
    sample_review_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class PulseReport:
    """Structured report produced by the reasoning pipeline."""

    run_id: str
    product: ProductName
    period_label: str
    themes: list[Theme]
    generated_at: datetime
    review_count: int = 0
