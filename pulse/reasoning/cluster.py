from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from datetime import datetime

import hdbscan
import numpy as np
import umap

from pulse.config import ClusteringConfig
from pulse.ingestion.models import CleanReview
from pulse.reasoning.errors import ClusteringError

logger = logging.getLogger(__name__)

RECENCY_HALF_LIFE_WEEKS = 4.0
MIN_EXCERPT_REVIEWS = 15


@dataclass(frozen=True)
class ReviewCluster:
    """A ranked cluster of reviews ready for LLM summarization."""

    label: int
    weight: float
    reviews: list[CleanReview]
    excerpts: list[CleanReview]
    review_indices: list[int]


def cluster_reviews(
    reviews: list[CleanReview],
    embeddings: np.ndarray,
    config: ClusteringConfig,
    *,
    reference_time: datetime | None = None,
) -> list[ReviewCluster]:
    """Run UMAP + HDBSCAN, rank clusters, and sample excerpts."""
    if len(reviews) != len(embeddings):
        raise ClusteringError("Review count does not match embedding matrix rows.")
    if len(reviews) < config.hdbscan_min_cluster_size:
        raise ClusteringError(
            f"Need at least {config.hdbscan_min_cluster_size} reviews to cluster; "
            f"got {len(reviews)}."
        )

    ref = reference_time or max(review.timestamp for review in reviews)

    if config.two_band:
        clusters = _cluster_two_band(reviews, embeddings, config, reference_time=ref)
    else:
        labels = _run_hdbscan(embeddings, config)
        clusters = _clusters_from_labels(reviews, labels, config, reference_time=ref)
        if not clusters:
            clusters = _rating_band_fallback(reviews, embeddings, config, reference_time=ref)

    if not clusters:
        raise ClusteringError(
            "All reviews assigned to noise cluster; no valid themes after rating-band fallback."
        )

    clusters.sort(key=lambda cluster: cluster.weight, reverse=True)
    return clusters[: config.top_k_themes]


def _cluster_two_band(
    reviews: list[CleanReview],
    embeddings: np.ndarray,
    config: ClusteringConfig,
    *,
    reference_time: datetime,
) -> list[ReviewCluster]:
    pain_idx = [i for i, r in enumerate(reviews) if r.rating <= 3]
    praise_idx = [i for i, r in enumerate(reviews) if r.rating >= 4]

    pain_clusters = _clusters_for_indices(
        reviews, embeddings, pain_idx, config, reference_time=reference_time
    )
    praise_clusters = _clusters_for_indices(
        reviews, embeddings, praise_idx, config, reference_time=reference_time
    )

    pain_clusters.sort(key=lambda c: c.weight, reverse=True)
    praise_clusters.sort(key=lambda c: c.weight, reverse=True)

    pain_pick = min(4, len(pain_clusters))
    praise_pick = min(1, len(praise_clusters))
    return pain_clusters[:pain_pick] + praise_clusters[:praise_pick]


def _rating_band_fallback(
    reviews: list[CleanReview],
    embeddings: np.ndarray,
    config: ClusteringConfig,
    *,
    reference_time: datetime,
) -> list[ReviewCluster]:
    logger.warning("All-noise clustering; attempting rating-band fallback.")
    pain_idx = [i for i, r in enumerate(reviews) if r.rating <= 3]
    praise_idx = [i for i, r in enumerate(reviews) if r.rating >= 4]
    clusters: list[ReviewCluster] = []
    clusters.extend(
        _clusters_for_indices(reviews, embeddings, pain_idx, config, reference_time=reference_time)
    )
    clusters.extend(
        _clusters_for_indices(
            reviews,
            embeddings,
            praise_idx,
            config,
            reference_time=reference_time,
        )
    )
    clusters.sort(key=lambda c: c.weight, reverse=True)
    return clusters[: config.top_k_themes]


def _clusters_for_indices(
    reviews: list[CleanReview],
    embeddings: np.ndarray,
    indices: list[int],
    config: ClusteringConfig,
    *,
    reference_time: datetime,
) -> list[ReviewCluster]:
    if len(indices) < config.hdbscan_min_cluster_size:
        return []

    sub_embeddings = embeddings[np.array(indices)]
    labels = _run_hdbscan(sub_embeddings, config)
    clusters = _clusters_from_labels(
        reviews,
        labels,
        config,
        index_map=indices,
        reference_time=reference_time,
    )
    return _split_oversized_clusters(
        reviews,
        embeddings,
        clusters,
        config,
        band_size=len(indices),
        reference_time=reference_time,
    )


def _split_oversized_clusters(
    reviews: list[CleanReview],
    embeddings: np.ndarray,
    clusters: list[ReviewCluster],
    config: ClusteringConfig,
    *,
    band_size: int,
    reference_time: datetime,
) -> list[ReviewCluster]:
    """Re-cluster any theme that captures too large a share of its band."""
    if band_size == 0:
        return clusters

    max_size = max(config.hdbscan_min_cluster_size, int(band_size * config.max_cluster_fraction))
    result: list[ReviewCluster] = []

    for cluster in clusters:
        if len(cluster.reviews) <= max_size:
            result.append(cluster)
            continue

        logger.info(
            "Splitting oversized cluster (label=%s, size=%s, band=%s)",
            cluster.label,
            len(cluster.reviews),
            band_size,
        )
        sub_embeddings = embeddings[np.array(cluster.review_indices)]
        bumped = ClusteringConfig(
            umap_n_neighbors=config.umap_n_neighbors,
            umap_n_components=config.umap_n_components,
            hdbscan_min_cluster_size=min(
                config.hdbscan_min_cluster_size + 5,
                max(5, len(cluster.reviews) // 4),
            ),
            hdbscan_min_samples=config.hdbscan_min_samples,
            top_k_themes=config.top_k_themes,
            two_band=config.two_band,
            max_cluster_fraction=config.max_cluster_fraction,
            max_excerpt_reviews=config.max_excerpt_reviews,
            max_excerpt_chars=config.max_excerpt_chars,
        )
        sub_labels = _run_hdbscan(sub_embeddings, bumped)
        sub_clusters = _clusters_from_labels(
            reviews,
            sub_labels,
            config,
            index_map=cluster.review_indices,
            reference_time=reference_time,
        )
        if sub_clusters:
            result.extend(sub_clusters)
        else:
            result.append(cluster)

    return result


def _run_hdbscan(embeddings: np.ndarray, config: ClusteringConfig) -> np.ndarray:
    n_samples = len(embeddings)
    if n_samples < 3:
        return np.full(n_samples, -1, dtype=int)

    n_neighbors = min(config.umap_n_neighbors, max(2, n_samples - 1))
    n_components = min(config.umap_n_components, max(2, n_samples - 2))

    reducer = umap.UMAP(
        n_neighbors=n_neighbors,
        n_components=n_components,
        metric="cosine",
        random_state=42,
    )
    reduced = reducer.fit_transform(embeddings)

    min_cluster_size = min(config.hdbscan_min_cluster_size, max(2, n_samples // 2))
    min_samples = min(config.hdbscan_min_samples, min_cluster_size)

    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=min_samples,
        metric="euclidean",
        cluster_selection_method="eom",
    )
    return np.asarray(clusterer.fit_predict(reduced), dtype=int)


def _clusters_from_labels(
    reviews: list[CleanReview],
    labels: np.ndarray,
    config: ClusteringConfig,
    *,
    index_map: list[int] | None = None,
    reference_time: datetime,
) -> list[ReviewCluster]:
    label_to_indices: dict[int, list[int]] = {}
    for local_idx, label in enumerate(labels):
        label_int = int(label)
        if label_int == -1:
            continue
        global_idx = index_map[local_idx] if index_map is not None else local_idx
        label_to_indices.setdefault(label_int, []).append(global_idx)

    clusters: list[ReviewCluster] = []
    for label, indices in label_to_indices.items():
        cluster_reviews_list = [reviews[i] for i in indices]
        weight = _cluster_weight(cluster_reviews_list, reference_time)
        excerpts = _sample_excerpts(cluster_reviews_list, config)
        clusters.append(
            ReviewCluster(
                label=label,
                weight=weight,
                reviews=cluster_reviews_list,
                excerpts=excerpts,
                review_indices=indices,
            )
        )
    return clusters


def _cluster_weight(reviews: list[CleanReview], reference_time: datetime) -> float:
    size = len(reviews)
    recency = sum(_recency_weight(r.timestamp, reference_time) for r in reviews) / size
    negative_fraction = sum(1 for r in reviews if r.rating <= 3) / size
    urgency = 1.0 + 0.5 * negative_fraction
    return size * recency * urgency


def _recency_weight(timestamp: datetime, reference_time: datetime) -> float:
    delta_days = max(0.0, (reference_time - timestamp).total_seconds() / 86400.0)
    half_life_days = RECENCY_HALF_LIFE_WEEKS * 7.0
    return math.exp(-math.log(2) * delta_days / half_life_days)


def _sample_excerpts(reviews: list[CleanReview], config: ClusteringConfig) -> list[CleanReview]:
    target = min(config.max_excerpt_reviews, max(MIN_EXCERPT_REVIEWS, len(reviews)))

    def sort_key(review: CleanReview) -> tuple[int, int, float]:
        complaint_bias = 0 if review.rating <= 3 else 1
        return (complaint_bias, -len(review.text), -review.timestamp.timestamp())

    selected = sorted(reviews, key=sort_key)[:target]
    excerpts: list[CleanReview] = []
    for review in selected:
        text = review.text
        if len(text) > config.max_excerpt_chars:
            text = text[: config.max_excerpt_chars].rstrip() + "…"
        excerpts.append(
            CleanReview(
                review_id=review.review_id,
                text=text,
                rating=review.rating,
                timestamp=review.timestamp,
                version=review.version,
                source=review.source,
            )
        )
    return excerpts
