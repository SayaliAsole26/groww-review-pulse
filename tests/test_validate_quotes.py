from __future__ import annotations

from pulse.reasoning.validate_quotes import filter_valid_quotes, quote_in_sources


def test_quote_exact_substring() -> None:
    sources = ["The app freezes during market hours and is very frustrating"]
    assert quote_in_sources("app freezes during market hours", sources)


def test_quote_fuzzy_whitespace() -> None:
    sources = ["The app  freezes during market hours"]
    assert quote_in_sources("The app freezes during market hours", sources, fuzzy_threshold=0.9)


def test_quote_rejects_hallucination() -> None:
    sources = ["Good app for beginners who want to invest safely"]
    assert not quote_in_sources("Terrible app never use again", sources)


def test_filter_valid_quotes() -> None:
    sources = ["Support takes days to reply and does not solve the issue"]
    quotes = [
        "Support takes days to reply",
        "Made up quote that does not exist",
    ]
    valid = filter_valid_quotes(quotes, sources)
    assert valid == ["Support takes days to reply"]
