from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from pulse.config import load_config
from pulse.run_id import (
    format_iso_week,
    make_run_id,
    parse_iso_week,
    resolve_run_id,
    run_id_from_iso_week,
)


def test_load_config_groww_package_and_defaults() -> None:
    config = load_config()
    assert config.groww.product == "groww"
    assert config.groww.package_id == "com.nextbillion.groww"
    assert config.pulse.review_window_weeks == 12
    assert config.pulse.min_reviews_for_run == 50
    assert config.pulse.preprocess.min_words == 8
    assert config.pulse.preprocess.reject_non_latin_script is True
    assert config.pulse.preprocess.reject_emoji is True
    assert config.pulse.preprocess.pii_url_mode == "redact"
    assert config.pulse.embeddings.model == "BAAI/bge-small-en-v1.5"
    assert config.pulse.embeddings.batch_size == 64
    assert config.pulse.llm.model == "llama-3.3-70b-versatile"
    assert config.pulse.clustering.top_k_themes == 5
    assert config.pulse.timezone == "Asia/Kolkata"
    assert config.pulse.mcp.server_url.startswith("https://")


def test_run_id_from_iso_week() -> None:
    assert run_id_from_iso_week("groww", "2026-W25") == "groww:2026-W25"


def test_run_id_deterministic_for_fixed_ist_instant() -> None:
    # 2026-06-24 is Wednesday of ISO week 26 in 2026
    instant = datetime(2026, 6, 24, 10, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
    iso = instant.isocalendar()
    assert make_run_id("groww", iso.year, iso.week) == "groww:2026-W26"


def test_parse_iso_week_rejects_invalid() -> None:
    import pytest

    from pulse.run_id import RunIdError

    with pytest.raises(RunIdError):
        parse_iso_week("2026-W99")


def test_resolve_run_id_explicit_week() -> None:
    assert resolve_run_id("groww", iso_week="2026-W01", timezone="Asia/Kolkata") == "groww:2026-W01"


def test_format_iso_week_zero_pads() -> None:
    assert format_iso_week(2026, 5) == "2026-W05"


def test_parse_google_doc_id_from_url() -> None:
    from pulse.config import parse_google_doc_id

    url = "https://docs.google.com/document/d/1AbCdeFGHijklMNopQ/edit"
    assert parse_google_doc_id(url) == "1AbCdeFGHijklMNopQ"
    assert parse_google_doc_id("1AbCdeFGHijklMNopQ") == "1AbCdeFGHijklMNopQ"


def test_google_doc_id_env_overrides_yaml(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "GOOGLE_DOC_ID",
        "https://docs.google.com/document/d/envDocId123/edit",
    )
    config = load_config()
    assert config.groww.doc_id == "envDocId123"


def test_parse_email_recipients() -> None:
    from pulse.config import parse_email_recipients

    assert parse_email_recipients("a@example.com, b@example.com") == [
        "a@example.com",
        "b@example.com",
    ]


def test_pulse_email_env_overrides_yaml(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PULSE_EMAIL_RECIPIENTS", "env@example.com,other@example.com")
    monkeypatch.setenv("PULSE_EMAIL_MODE", "send")
    config = load_config()
    assert config.groww.email_recipients == ["env@example.com", "other@example.com"]
    assert config.groww.email_default_mode == "send"
