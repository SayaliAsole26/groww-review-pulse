from __future__ import annotations

import logging
from pathlib import Path

import numpy as np

from pulse.reasoning.errors import ReasoningError

logger = logging.getLogger(__name__)

BGE_PREFIX = "BAAI/bge"


def _is_bge_model(model_name: str) -> bool:
    return model_name.startswith(BGE_PREFIX)


def encode_reviews(
    texts: list[str],
    *,
    model_name: str,
    batch_size: int,
    cache_path: Path | None = None,
    review_ids: list[str] | None = None,
    force_refresh: bool = False,
) -> np.ndarray:
    """
    Batch-encode review texts with sentence-transformers.

    Optional parquet cache keyed by model name and review_ids.
    """
    if review_ids is not None and cache_path is not None and not force_refresh:
        cached = _load_embedding_cache(cache_path, model_name, review_ids)
        if cached is not None:
            logger.info("Loaded embeddings from cache (%s)", cache_path)
            return cached

    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise ReasoningError(
            "sentence-transformers is required for embeddings. "
            "Install with: pip install -e '.[reasoning]'"
        ) from exc

    try:
        model = SentenceTransformer(model_name)
    except Exception as exc:
        raise ReasoningError(
            f"Failed to load embedding model {model_name!r}. "
            "Check network access or set HF_HOME for offline cache."
        ) from exc

    logger.info("Encoding %s reviews with %s", len(texts), model_name)
    encode_kwargs: dict[str, object] = {
        "batch_size": batch_size,
        "show_progress_bar": False,
    }
    if _is_bge_model(model_name):
        encode_kwargs["normalize_embeddings"] = True

    vectors = model.encode(texts, **encode_kwargs)
    embeddings = np.asarray(vectors, dtype=np.float32)

    if cache_path is not None and review_ids is not None:
        _save_embedding_cache(cache_path, model_name, review_ids, embeddings)
        logger.info("Saved embeddings to %s", cache_path)

    return embeddings


def _load_embedding_cache(
    path: Path,
    model_name: str,
    review_ids: list[str],
) -> np.ndarray | None:
    if not path.is_file():
        return None
    try:
        import pyarrow.parquet as pq
    except ImportError:
        return None

    try:
        table = pq.read_table(path)
    except Exception:
        return None

    metadata = table.schema.metadata or {}
    cached_model = metadata.get(b"model", b"").decode("utf-8")
    if cached_model != model_name:
        return None

    ids = table.column("review_id").to_pylist()
    if ids != review_ids:
        return None

    embedding_lists = table.column("embedding").to_pylist()
    return np.asarray(embedding_lists, dtype=np.float32)


def _save_embedding_cache(
    path: Path,
    model_name: str,
    review_ids: list[str],
    embeddings: np.ndarray,
) -> None:
    import pyarrow as pa
    import pyarrow.parquet as pq

    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.table(
        {
            "review_id": review_ids,
            "embedding": [row.tolist() for row in embeddings],
        }
    )
    table = table.replace_schema_metadata({b"model": model_name.encode("utf-8")})
    temp_path = path.with_suffix(".parquet.tmp")
    pq.write_table(table, temp_path)
    temp_path.replace(path)
