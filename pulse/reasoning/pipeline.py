from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from pulse.config import AppConfig
from pulse.data_paths import (
    default_data_root,
    embeddings_path,
    normalized_reviews_path,
    report_path,
)
from pulse.ingestion.models import CleanReview, PulseReport, Theme
from pulse.preprocess.cache import load_processed_reviews
from pulse.preprocess.normalize import PreprocessSettings
from pulse.preprocess.pii import PiiSettings
from pulse.reasoning.cluster import ReviewCluster, cluster_reviews
from pulse.reasoning.embed import encode_reviews
from pulse.reasoning.errors import QuoteValidationError, ReasoningError, TokenBudgetExceededError
from pulse.reasoning.report_io import save_report
from pulse.reasoning.summarize import LlmUsage, summarize_cluster
from pulse.reasoning.validate_quotes import filter_valid_quotes

logger = logging.getLogger(__name__)


def load_normalized_reviews_for_run(
    config: AppConfig,
    run_id: str,
    *,
    data_root: Path | None = None,
) -> list[CleanReview]:
    root = data_root or default_data_root()
    settings = _preprocess_settings(config)
    pii_settings = _pii_settings(config)
    reviews = load_processed_reviews(
        normalized_reviews_path(root),
        run_id=run_id,
        settings=settings,
        pii_settings=pii_settings,
    )
    if reviews is None:
        raise ReasoningError(
            f"Missing normalized reviews for {run_id}. Run: python -m pulse ingest --week ..."
        )
    return reviews


def analyze_reviews_for_run(
    config: AppConfig,
    run_id: str,
    reviews: list[CleanReview],
    *,
    data_root: Path | None = None,
    force_refresh_embeddings: bool = False,
    llm_client: object | None = None,
) -> PulseReport:
    """Full Phase 2 pipeline: embed → cluster → summarize → validate."""
    root = data_root or default_data_root()
    texts = [review.text for review in reviews]
    review_ids = [review.review_id for review in reviews]

    cache_file = embeddings_path(run_id, root)
    embeddings = encode_reviews(
        texts,
        model_name=config.pulse.embeddings.model,
        batch_size=config.pulse.embeddings.batch_size,
        cache_path=cache_file,
        review_ids=review_ids,
        force_refresh=force_refresh_embeddings,
    )

    clusters = cluster_reviews(
        reviews,
        embeddings,
        config.pulse.clustering,
        reference_time=datetime.now().astimezone(),
    )
    logger.info("Selected %s clusters for LLM summarization", len(clusters))

    usage = LlmUsage()
    themes: list[Theme] = []

    for rank, cluster in enumerate(clusters, start=1):
        theme = _summarize_cluster_with_validation(
            cluster,
            rank=rank,
            config=config,
            usage=usage,
            llm_client=llm_client,
        )
        if theme is not None:
            themes.append(theme)

    if not themes:
        raise QuoteValidationError("No valid themes remain after quote validation.")

    period = f"Last {config.pulse.review_window_weeks} weeks (rolling)"
    report = PulseReport(
        run_id=run_id,
        product="groww",
        period_label=period,
        themes=themes,
        generated_at=datetime.now().astimezone(),
        review_count=len(reviews),
    )

    out_path = report_path(run_id, root)
    save_report(out_path, report)
    logger.info(
        "Report saved to %s (themes=%s, llm_requests=%s, tokens=%s)",
        out_path,
        len(themes),
        usage.request_count,
        usage.total_tokens,
    )
    return report


def _summarize_cluster_with_validation(
    cluster: ReviewCluster,
    *,
    rank: int,
    config: AppConfig,
    usage: LlmUsage,
    llm_client: object | None,
) -> Theme | None:
    excerpt_sources = [review.text for review in cluster.excerpts]

    try:
        draft = summarize_cluster(
            cluster.excerpts,
            config=config.pulse.llm,
            usage=usage,
            strict=False,
            client=llm_client,
        )
    except TokenBudgetExceededError:
        logger.error("Token budget exhausted before cluster %s could be summarized.", rank)
        raise

    valid_quotes = filter_valid_quotes(draft.quotes, excerpt_sources)
    action_ideas = draft.action_ideas[:1]

    if not valid_quotes and usage.total_tokens < config.pulse.llm.max_tokens_per_run:
        logger.warning(
            "Quote validation failed for cluster %s; re-prompting with strict mode.",
            rank,
        )
        try:
            strict_draft = summarize_cluster(
                cluster.excerpts,
                config=config.pulse.llm,
                usage=usage,
                strict=True,
                client=llm_client,
            )
            valid_quotes = filter_valid_quotes(strict_draft.quotes, excerpt_sources)
            if valid_quotes:
                draft = strict_draft
                action_ideas = strict_draft.action_ideas[:1]
        except TokenBudgetExceededError:
            logger.warning(
                "Skipping strict re-prompt for cluster %s; token budget exhausted.",
                rank,
            )

    if not valid_quotes:
        logger.warning("Dropping cluster %s: no valid quotes after validation.", rank)
        return None

    if not draft.title:
        return None

    sample_ids = [review.review_id for review in cluster.excerpts[:3]]
    return Theme(
        rank=rank,
        title=draft.title,
        summary=draft.summary,
        quotes=valid_quotes[:3],
        action_ideas=action_ideas or ["Investigate and address this recurring feedback."],
        review_count=len(cluster.reviews),
        sample_review_ids=sample_ids,
    )


def _preprocess_settings(config: AppConfig) -> PreprocessSettings:
    p = config.pulse.preprocess
    return PreprocessSettings(
        min_words=p.min_words,
        reject_non_latin_script=p.reject_non_latin_script,
        reject_emoji=p.reject_emoji,
    )


def _pii_settings(config: AppConfig) -> PiiSettings:
    return PiiSettings(url_mode=config.pulse.preprocess.pii_url_mode)
