from __future__ import annotations

import re
from difflib import SequenceMatcher

WHITESPACE_RE = re.compile(r"\s+")


def normalize_for_match(text: str) -> str:
    """Collapse whitespace for quote substring matching."""
    return WHITESPACE_RE.sub(" ", text).strip().lower()


def quote_in_sources(quote: str, sources: list[str], *, fuzzy_threshold: float = 0.9) -> bool:
    """Return True if quote is found verbatim (or fuzzy) in union of sources."""
    normalized_quote = normalize_for_match(quote)
    if not normalized_quote:
        return False

    combined = normalize_for_match(" ".join(sources))
    if normalized_quote in combined:
        return True

    if fuzzy_threshold <= 0:
        return False

    for source in sources:
        normalized_source = normalize_for_match(source)
        if not normalized_source:
            continue
        if normalized_quote in normalized_source:
            return True
        ratio = SequenceMatcher(None, normalized_quote, normalized_source).ratio()
        if ratio >= fuzzy_threshold:
            return True
    return False


def filter_valid_quotes(
    quotes: list[str],
    sources: list[str],
    *,
    fuzzy_threshold: float = 0.9,
) -> list[str]:
    """Keep only quotes that pass validation against source texts."""
    return [
        quote
        for quote in quotes
        if quote_in_sources(quote, sources, fuzzy_threshold=fuzzy_threshold)
    ]
