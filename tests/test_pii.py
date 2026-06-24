from __future__ import annotations

from pulse.preprocess.pii import PiiSettings, scrub_text


def test_scrub_email() -> None:
    text = "Contact me at user@example.com for support please thanks"
    assert "[EMAIL]" in scrub_text(text)
    assert "user@example.com" not in scrub_text(text)


def test_scrub_phone() -> None:
    text = "Call me on +91 9876543210 if the app fails again tomorrow"
    assert "[PHONE]" in scrub_text(text)


def test_scrub_pan() -> None:
    text = "My PAN ABCDE1234F was rejected during KYC verification process"
    assert "[ID]" in scrub_text(text)


def test_scrub_url_redact_mode() -> None:
    text = "Visit https://evil.example/phish for more details about this issue"
    assert scrub_text(text, PiiSettings(url_mode="redact")) == (
        "Visit [URL] for more details about this issue"
    )


def test_scrub_url_domain_mode() -> None:
    text = "Visit https://support.groww.in/help for account related issues today"
    result = scrub_text(text, PiiSettings(url_mode="domain"))
    assert "support.groww.in" in result
    assert "https://" not in result
