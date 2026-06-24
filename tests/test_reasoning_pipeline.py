from __future__ import annotations

import json
from datetime import datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import numpy as np
import pytest

from pulse.config import load_config
from pulse.data_paths import report_path
from pulse.ingestion.models import CleanReview
from pulse.reasoning.cluster import ReviewCluster
from pulse.reasoning.pipeline import analyze_reviews_for_run
from pulse.reasoning.report_io import load_report

IST = ZoneInfo("Asia/Kolkata")


class _FakeGroqClient:
    def __init__(self, responses: list[dict]) -> None:
        self._responses = responses
        self._index = 0
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs: object) -> SimpleNamespace:
        payload = self._responses[min(self._index, len(self._responses) - 1)]
        self._index += 1
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(payload)))],
            usage=SimpleNamespace(prompt_tokens=100, completion_tokens=50, total_tokens=150),
        )


def _review(i: int, rating: int) -> CleanReview:
    return CleanReview(
        review_id=f"r{i}",
        text=f"Support ticket unresolved for {i} days and app crashes during market hours",
        rating=rating,
        timestamp=datetime(2026, 6, 10 + i, tzinfo=IST),
        version="1.0",
        source="playstore",
    )


def test_analyze_pipeline_with_mocked_llm_and_embeddings(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: object,
) -> None:
    from pathlib import Path

    config = load_config()
    run_id = "groww:2026-W25"
    reviews = [_review(i, 1 if i < 6 else 5) for i in range(10)]

    # Deterministic embeddings: two groups
    fake_embeddings = np.vstack(
        [
            np.tile(np.array([1.0, 0.0, 0.0], dtype=np.float32), (6, 1)),
            np.tile(np.array([0.0, 1.0, 0.0], dtype=np.float32), (4, 1)),
        ]
    )

    monkeypatch.setattr(
        "pulse.reasoning.pipeline.encode_reviews",
        lambda *args, **kwargs: fake_embeddings,
    )

    cluster = ReviewCluster(
        label=0,
        weight=100.0,
        reviews=reviews[:6],
        excerpts=reviews[:3],
        review_indices=[0, 1, 2],
    )
    monkeypatch.setattr(
        "pulse.reasoning.pipeline.cluster_reviews",
        lambda *args, **kwargs: [cluster],
    )

    quote = "Support ticket unresolved for 0 days and app crashes during market hours"
    fake_client = _FakeGroqClient(
        [
            {
                "title": "Support and crashes",
                "summary": "Users report unresolved tickets and crashes.",
                "quotes": [quote],
                "action_ideas": ["Improve support SLA visibility in-app."],
            },
        ]
    )

    root = Path(str(tmp_path))
    report = analyze_reviews_for_run(
        config,
        run_id,
        reviews,
        data_root=root,
        llm_client=fake_client,
    )

    assert len(report.themes) >= 1
    assert report.themes[0].quotes
    loaded = load_report(report_path(run_id, root))
    assert loaded.run_id == run_id
