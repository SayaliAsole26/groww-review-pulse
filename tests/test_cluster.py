from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import numpy as np

from pulse.config import ClusteringConfig
from pulse.ingestion.models import CleanReview
from pulse.reasoning.cluster import _cluster_weight, _sample_excerpts, cluster_reviews

IST = ZoneInfo("Asia/Kolkata")


def _clean(review_id: str, text: str, rating: int, day: int) -> CleanReview:
    return CleanReview(
        review_id=review_id,
        text=text,
        rating=rating,
        timestamp=datetime(2026, 6, day, tzinfo=IST),
        version="1.0",
        source="playstore",
    )


def test_complaint_cluster_weights_higher() -> None:
    ref = datetime(2026, 6, 25, tzinfo=IST)
    complaints = [
        _clean("c1", "App crashes during market open very frustrating experience", 1, 20),
        _clean("c2", "App freezes when placing orders during peak trading hours", 1, 21),
    ]
    praise = [
        _clean("p1", "Great app for beginners who want to start investing today", 5, 22),
        _clean("p2", "Nice interface and easy to use for mutual fund investing", 5, 23),
    ]
    assert _cluster_weight(complaints, ref) > _cluster_weight(praise, ref)


def test_sample_excerpts_prefers_complaints_and_truncates() -> None:
    config = ClusteringConfig(
        umap_n_neighbors=5,
        umap_n_components=2,
        hdbscan_min_cluster_size=2,
        hdbscan_min_samples=1,
        top_k_themes=3,
        two_band=False,
        max_cluster_fraction=0.25,
        max_excerpt_reviews=2,
        max_excerpt_chars=20,
    )
    reviews = [
        _clean("a", "x" * 40, 5, 10),
        _clean("b", "y" * 40, 1, 11),
    ]
    excerpts = _sample_excerpts(reviews, config)
    assert excerpts[0].rating == 1
    assert excerpts[0].text.endswith("…")


def test_cluster_reviews_produces_ranked_clusters() -> None:
    reviews = [
        _clean(
            f"r{i}",
            f"Trading order execution failed during market hours issue number {i}",
            1 if i < 4 else 5,
            10 + i,
        )
        for i in range(8)
    ]
    # Simple 2-group embedding: first 4 similar, last 4 similar
    embeddings = np.vstack(
        [
            np.tile(np.array([1.0, 0.0], dtype=np.float32), (4, 1)),
            np.tile(np.array([0.0, 1.0], dtype=np.float32), (4, 1)),
        ]
    )
    config = ClusteringConfig(
        umap_n_neighbors=3,
        umap_n_components=2,
        hdbscan_min_cluster_size=3,
        hdbscan_min_samples=1,
        top_k_themes=2,
        two_band=False,
        max_cluster_fraction=0.25,
        max_excerpt_reviews=3,
        max_excerpt_chars=200,
    )
    ref_time = datetime(2026, 6, 25, tzinfo=IST)
    clusters = cluster_reviews(reviews, embeddings, config, reference_time=ref_time)
    assert len(clusters) >= 1
    assert clusters[0].weight >= clusters[-1].weight
