from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal
from urllib.parse import urlparse

from pulse.ingestion.models import CleanReview, Review

EMAIL_RE = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
    re.IGNORECASE,
)
# Indian mobile: +91 optional, optional separators, leading 6-9 + 9 digits
PHONE_RE = re.compile(
    r"(?:\+91[\s-]?)?(?:\d[\s-]?){10}\b",
)
# PAN: 5 letters + 4 digits + 1 letter
PAN_RE = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b")
# Aadhaar-like: 4 groups of 4 digits (with optional spaces)
AADHAAR_RE = re.compile(r"\b(?:\d{4}[\s-]?){3}\d{4}\b")
URL_RE = re.compile(
    r"(https?://[^\s]+|www\.[^\s]+)",
    re.IGNORECASE,
)

PiiUrlMode = Literal["redact", "domain"]


@dataclass(frozen=True)
class PiiSettings:
    url_mode: PiiUrlMode = "redact"


def scrub_text(text: str, settings: PiiSettings | None = None) -> str:
    """Redact PII patterns from review text."""
    cfg = settings or PiiSettings()
    scrubbed = EMAIL_RE.sub("[EMAIL]", text)
    scrubbed = PHONE_RE.sub("[PHONE]", scrubbed)
    scrubbed = PAN_RE.sub("[ID]", scrubbed)
    scrubbed = AADHAAR_RE.sub("[ID]", scrubbed)
    scrubbed = URL_RE.sub(lambda m: _redact_url(m.group(0), cfg.url_mode), scrubbed)
    return scrubbed


def _redact_url(url: str, mode: PiiUrlMode) -> str:
    if mode == "domain":
        raw = url if "://" in url else f"http://{url}"
        parsed = urlparse(raw)
        host = parsed.netloc or parsed.path.split("/")[0]
        return host if host else "[URL]"
    return "[URL]"


def scrub_review(review: Review | CleanReview, settings: PiiSettings | None = None) -> CleanReview:
    """Apply PII scrubbing to a single review."""
    return CleanReview(
        review_id=review.review_id,
        text=scrub_text(review.text, settings),
        rating=review.rating,
        timestamp=review.timestamp,
        version=review.version,
        source=review.source,
    )


def scrub_reviews(
    reviews: list[CleanReview],
    settings: PiiSettings | None = None,
) -> list[CleanReview]:
    """Apply PII scrubbing to all reviews."""
    return [scrub_review(review, settings) for review in reviews]
