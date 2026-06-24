from __future__ import annotations

import html
import re
from dataclasses import dataclass

from pulse.ingestion.models import CleanReview, Review

WHITESPACE_RE = re.compile(r"\s+")
EMOJI_RE = re.compile(
    "["
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F1E0-\U0001F1FF"
    "\U00002700-\U000027BF"
    "\U0001FA00-\U0001FAFF"
    "\U00002600-\U000026FF"
    "\U0001F900-\U0001F9FF"
    "]+",
    flags=re.UNICODE,
)
# Devanagari and other common non-Latin scripts on Groww reviews
NON_LATIN_SCRIPT_RE = re.compile(r"[\u0900-\u097F\u0980-\u09FF\u0A00-\u0A7F\u0B80-\u0BFF]")


@dataclass(frozen=True)
class PreprocessSettings:
    min_words: int = 8
    reject_non_latin_script: bool = True
    reject_emoji: bool = True


@dataclass(frozen=True)
class NormalizeStats:
    input_count: int
    output_count: int
    dropped_short: int
    dropped_emoji: int
    dropped_script: int

    @property
    def dropped_total(self) -> int:
        return self.dropped_short + self.dropped_emoji + self.dropped_script


def collapse_text(text: str) -> str:
    """Decode HTML entities and collapse whitespace."""
    unescaped = html.unescape(text)
    return WHITESPACE_RE.sub(" ", unescaped).strip()


def word_count(text: str) -> int:
    if not text:
        return 0
    return len(text.split())


def contains_emoji(text: str) -> bool:
    return bool(EMOJI_RE.search(text))


def contains_non_latin_script(text: str) -> bool:
    return bool(NON_LATIN_SCRIPT_RE.search(text))


def should_keep_review(text: str, settings: PreprocessSettings) -> tuple[bool, str | None]:
    """
    Return (keep, drop_reason).

    drop_reason is one of: ``short``, ``emoji``, ``script``.
    """
    if word_count(text) < settings.min_words:
        return False, "short"

    if settings.reject_emoji and contains_emoji(text):
        return False, "emoji"

    if settings.reject_non_latin_script and contains_non_latin_script(text):
        return False, "script"

    return True, None


def review_to_clean(review: Review, cleaned_text: str) -> CleanReview:
    return CleanReview(
        review_id=review.review_id,
        text=cleaned_text,
        rating=review.rating,
        timestamp=review.timestamp,
        version=review.version,
        source=review.source,
    )


def normalize_reviews(
    reviews: list[Review],
    settings: PreprocessSettings | None = None,
) -> tuple[list[CleanReview], NormalizeStats]:
    """Filter and normalize raw reviews for downstream clustering."""
    cfg = settings or PreprocessSettings()
    kept: list[CleanReview] = []
    dropped_short = 0
    dropped_emoji = 0
    dropped_script = 0

    for review in reviews:
        cleaned_text = collapse_text(review.text)
        keep, reason = should_keep_review(cleaned_text, cfg)
        if not keep:
            if reason == "short":
                dropped_short += 1
            elif reason == "emoji":
                dropped_emoji += 1
            elif reason == "script":
                dropped_script += 1
            continue
        kept.append(review_to_clean(review, cleaned_text))

    stats = NormalizeStats(
        input_count=len(reviews),
        output_count=len(kept),
        dropped_short=dropped_short,
        dropped_emoji=dropped_emoji,
        dropped_script=dropped_script,
    )
    return kept, stats
