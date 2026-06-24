from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import yaml

from pulse.ingestion.models import EmailMode, ProductName
from pulse.run_id import GROWW_PACKAGE_ID

DEFAULT_MCP_SERVER_URL = "https://mcp-server-production-725c.up.railway.app"


class ConfigError(ValueError):
    """Configuration file is missing or invalid."""


@dataclass(frozen=True)
class GrowwConfig:
    product: ProductName
    display_name: str
    package_id: str
    doc_id: str
    doc_title: str
    email_recipients: list[str]
    email_default_mode: EmailMode


@dataclass(frozen=True)
class EmbeddingConfig:
    model: str
    batch_size: int


@dataclass(frozen=True)
class ClusteringConfig:
    umap_n_neighbors: int
    umap_n_components: int
    hdbscan_min_cluster_size: int
    hdbscan_min_samples: int
    top_k_themes: int
    two_band: bool
    max_cluster_fraction: float
    max_excerpt_reviews: int
    max_excerpt_chars: int


@dataclass(frozen=True)
class LlmConfig:
    provider: str
    model: str
    max_tokens_per_run: int
    max_tokens_per_cluster: int
    temperature: float


@dataclass(frozen=True)
class ScheduleConfig:
    cron: str


@dataclass(frozen=True)
class PreprocessConfig:
    min_words: int
    reject_non_latin_script: bool
    reject_emoji: bool
    pii_url_mode: Literal["redact", "domain"]


@dataclass(frozen=True)
class McpConfig:
    server_url: str


@dataclass(frozen=True)
class PulseConfig:
    review_window_weeks: int
    min_reviews_for_run: int
    preprocess: PreprocessConfig
    embeddings: EmbeddingConfig
    clustering: ClusteringConfig
    llm: LlmConfig
    timezone: str
    schedule: ScheduleConfig
    mcp: McpConfig


@dataclass(frozen=True)
class AppConfig:
    groww: GrowwConfig
    pulse: PulseConfig
    config_dir: Path


def find_project_root(start: Path | None = None) -> Path:
    """Locate repository root by walking up for ``pyproject.toml``."""
    current = (start or Path.cwd()).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "pyproject.toml").is_file():
            return candidate
    raise ConfigError("Could not find project root (pyproject.toml).")


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ConfigError(f"Config file not found: {path}")
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ConfigError(f"Config file must be a mapping: {path}")
    return data


def _require_str(data: dict[str, Any], key: str, context: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{context}.{key} must be a non-empty string.")
    return value.strip()


def _require_positive_int(value: Any, name: str) -> int:
    if not isinstance(value, int) or value <= 0:
        raise ConfigError(f"{name} must be a positive integer.")
    return value


def _validate_timezone(timezone: str) -> str:
    try:
        ZoneInfo(timezone)
    except ZoneInfoNotFoundError as exc:
        raise ConfigError(f"Unknown timezone: {timezone!r}.") from exc
    return timezone


_GOOGLE_DOC_ID_PATTERN = re.compile(r"/document/d/([a-zA-Z0-9_-]+)")


def parse_google_doc_id(value: str) -> str:
    """Extract a Google Doc ID from a full URL or return a bare ID."""
    cleaned = value.strip().strip('"').strip("'")
    match = _GOOGLE_DOC_ID_PATTERN.search(cleaned)
    if match:
        return match.group(1)
    return cleaned


def _resolve_doc_id(yaml_doc_id: str) -> str:
    """Prefer GOOGLE_DOC_ID from .env over groww.yaml."""
    env_doc_id = os.environ.get("GOOGLE_DOC_ID", "").strip()
    if env_doc_id:
        return parse_google_doc_id(env_doc_id)
    return yaml_doc_id


def parse_email_recipients(value: str) -> list[str]:
    """Parse comma-separated recipient list from env or config."""
    recipients = [part.strip() for part in value.split(",")]
    return [recipient for recipient in recipients if recipient]


def _resolve_email_recipients(yaml_recipients: list[str]) -> list[str]:
    """Prefer PULSE_EMAIL_RECIPIENTS from .env over groww.yaml."""
    env_recipients = os.environ.get("PULSE_EMAIL_RECIPIENTS", "").strip()
    if env_recipients:
        recipients = parse_email_recipients(env_recipients)
        if not recipients:
            raise ConfigError("PULSE_EMAIL_RECIPIENTS must contain at least one address.")
        return recipients
    return yaml_recipients


def _resolve_email_mode(yaml_mode: EmailMode) -> EmailMode:
    """Prefer PULSE_EMAIL_MODE from .env over groww.yaml."""
    env_mode = os.environ.get("PULSE_EMAIL_MODE", "").strip().lower()
    if env_mode:
        if env_mode not in ("draft", "send"):
            raise ConfigError("PULSE_EMAIL_MODE must be 'draft' or 'send'.")
        return env_mode  # type: ignore[return-value]
    return yaml_mode


def _parse_groww(data: dict[str, Any]) -> GrowwConfig:
    product = _require_str(data, "product", "groww")
    if product != "groww":
        raise ConfigError("groww.product must be 'groww' in v1.")

    playstore = data.get("playstore")
    if not isinstance(playstore, dict):
        raise ConfigError("groww.playstore must be a mapping.")

    package_id = _require_str(playstore, "package_id", "groww.playstore")
    if package_id != GROWW_PACKAGE_ID:
        raise ConfigError(
            f"groww.playstore.package_id must be {GROWW_PACKAGE_ID!r}, got {package_id!r}."
        )

    google = data.get("google")
    if not isinstance(google, dict):
        raise ConfigError("groww.google must be a mapping.")

    doc_id = _resolve_doc_id(_require_str(google, "doc_id", "groww.google"))
    if "REPLACE_WITH" in doc_id:
        logging.getLogger(__name__).warning(
            "groww.google.doc_id is still a placeholder; set a real Doc ID before delivery."
        )

    doc_title = _require_str(google, "doc_title", "groww.google")

    email = data.get("email")
    if not isinstance(email, dict):
        raise ConfigError("groww.email must be a mapping.")

    recipients_raw = email.get("recipients")
    if not isinstance(recipients_raw, list) or not recipients_raw:
        raise ConfigError("groww.email.recipients must be a non-empty list.")
    recipients = [str(item).strip() for item in recipients_raw if str(item).strip()]
    if not recipients:
        raise ConfigError("groww.email.recipients must contain at least one address.")

    default_mode_raw = _require_str(email, "default_mode", "groww.email")
    if default_mode_raw not in ("draft", "send"):
        raise ConfigError("groww.email.default_mode must be 'draft' or 'send'.")
    default_mode: EmailMode = default_mode_raw  # type: ignore[assignment]

    return GrowwConfig(
        product="groww",
        display_name=_require_str(data, "display_name", "groww"),
        package_id=package_id,
        doc_id=doc_id,
        doc_title=doc_title,
        email_recipients=_resolve_email_recipients(recipients),
        email_default_mode=_resolve_email_mode(default_mode),
    )


def _parse_pulse(data: dict[str, Any]) -> PulseConfig:
    review_window_weeks = _require_positive_int(
        data.get("review_window_weeks"), "pulse.review_window_weeks"
    )
    min_reviews_for_run = _require_positive_int(
        data.get("min_reviews_for_run"), "pulse.min_reviews_for_run"
    )

    preprocess_raw = data.get("preprocess")
    if not isinstance(preprocess_raw, dict):
        raise ConfigError("pulse.preprocess must be a mapping.")
    min_words = _require_positive_int(preprocess_raw.get("min_words"), "pulse.preprocess.min_words")
    reject_non_latin_script = preprocess_raw.get("reject_non_latin_script", True)
    reject_emoji = preprocess_raw.get("reject_emoji", True)
    if not isinstance(reject_non_latin_script, bool):
        raise ConfigError("pulse.preprocess.reject_non_latin_script must be a boolean.")
    if not isinstance(reject_emoji, bool):
        raise ConfigError("pulse.preprocess.reject_emoji must be a boolean.")
    pii_url_mode_raw = preprocess_raw.get("pii_url_mode", "redact")
    if pii_url_mode_raw not in ("redact", "domain"):
        raise ConfigError("pulse.preprocess.pii_url_mode must be 'redact' or 'domain'.")
    preprocess = PreprocessConfig(
        min_words=min_words,
        reject_non_latin_script=reject_non_latin_script,
        reject_emoji=reject_emoji,
        pii_url_mode=pii_url_mode_raw,  # type: ignore[arg-type]
    )

    embeddings_raw = data.get("embeddings")
    if not isinstance(embeddings_raw, dict):
        raise ConfigError("pulse.embeddings must be a mapping.")
    embeddings = EmbeddingConfig(
        model=_require_str(embeddings_raw, "model", "pulse.embeddings"),
        batch_size=_require_positive_int(
            embeddings_raw.get("batch_size"), "pulse.embeddings.batch_size"
        ),
    )

    clustering_raw = data.get("clustering")
    if not isinstance(clustering_raw, dict):
        raise ConfigError("pulse.clustering must be a mapping.")
    if not isinstance(clustering_raw.get("max_cluster_fraction", 0.25), (int, float)):
        raise ConfigError("pulse.clustering.max_cluster_fraction must be a number.")
    max_cluster_fraction = float(clustering_raw.get("max_cluster_fraction", 0.25))
    if max_cluster_fraction <= 0 or max_cluster_fraction > 1:
        raise ConfigError("pulse.clustering.max_cluster_fraction must be between 0 and 1.")
    clustering = ClusteringConfig(
        umap_n_neighbors=_require_positive_int(
            clustering_raw.get("umap_n_neighbors"), "pulse.clustering.umap_n_neighbors"
        ),
        umap_n_components=_require_positive_int(
            clustering_raw.get("umap_n_components"), "pulse.clustering.umap_n_components"
        ),
        hdbscan_min_cluster_size=_require_positive_int(
            clustering_raw.get("hdbscan_min_cluster_size"),
            "pulse.clustering.hdbscan_min_cluster_size",
        ),
        hdbscan_min_samples=_require_positive_int(
            clustering_raw.get("hdbscan_min_samples"),
            "pulse.clustering.hdbscan_min_samples",
        ),
        top_k_themes=_require_positive_int(
            clustering_raw.get("top_k_themes"), "pulse.clustering.top_k_themes"
        ),
        two_band=bool(clustering_raw.get("two_band", False)),
        max_cluster_fraction=max_cluster_fraction,
        max_excerpt_reviews=_require_positive_int(
            clustering_raw.get("max_excerpt_reviews"),
            "pulse.clustering.max_excerpt_reviews",
        ),
        max_excerpt_chars=_require_positive_int(
            clustering_raw.get("max_excerpt_chars"),
            "pulse.clustering.max_excerpt_chars",
        ),
    )

    llm_raw = data.get("llm")
    if not isinstance(llm_raw, dict):
        raise ConfigError("pulse.llm must be a mapping.")

    temperature = llm_raw.get("temperature")
    if not isinstance(temperature, (int, float)) or temperature < 0 or temperature > 2:
        raise ConfigError("pulse.llm.temperature must be a number between 0 and 2.")

    llm = LlmConfig(
        provider=_require_str(llm_raw, "provider", "pulse.llm"),
        model=_require_str(llm_raw, "model", "pulse.llm"),
        max_tokens_per_run=_require_positive_int(
            llm_raw.get("max_tokens_per_run"), "pulse.llm.max_tokens_per_run"
        ),
        max_tokens_per_cluster=_require_positive_int(
            llm_raw.get("max_tokens_per_cluster"), "pulse.llm.max_tokens_per_cluster"
        ),
        temperature=float(temperature),
    )

    timezone = _validate_timezone(_require_str(data, "timezone", "pulse"))
    if timezone != "Asia/Kolkata":
        logging.getLogger(__name__).warning(
            "pulse.timezone is %r; architecture expects Asia/Kolkata for scheduling.",
            timezone,
        )

    schedule_raw = data.get("schedule")
    if not isinstance(schedule_raw, dict):
        raise ConfigError("pulse.schedule must be a mapping.")
    schedule = ScheduleConfig(cron=_require_str(schedule_raw, "cron", "pulse.schedule"))

    mcp_raw = data.get("mcp")
    if mcp_raw is None:
        mcp_raw = {}
    if not isinstance(mcp_raw, dict):
        raise ConfigError("pulse.mcp must be a mapping.")
    server_url = mcp_raw.get("server_url", DEFAULT_MCP_SERVER_URL)
    if not isinstance(server_url, str) or not server_url.strip():
        raise ConfigError("pulse.mcp.server_url must be a non-empty string.")
    mcp = McpConfig(server_url=server_url.strip().rstrip("/"))

    return PulseConfig(
        review_window_weeks=review_window_weeks,
        min_reviews_for_run=min_reviews_for_run,
        preprocess=preprocess,
        embeddings=embeddings,
        clustering=clustering,
        llm=llm,
        timezone=timezone,
        schedule=schedule,
        mcp=mcp,
    )


def load_config(config_dir: Path | None = None) -> AppConfig:
    """Load and validate Groww + pulse YAML configuration."""
    from pulse.env import load_dotenv

    load_dotenv()
    root = find_project_root()
    resolved_dir = config_dir or (root / "config")
    groww_path = resolved_dir / "groww.yaml"
    pulse_path = resolved_dir / "pulse.yaml"

    groww = _parse_groww(_load_yaml(groww_path))
    pulse = _parse_pulse(_load_yaml(pulse_path))

    return AppConfig(groww=groww, pulse=pulse, config_dir=resolved_dir.resolve())
