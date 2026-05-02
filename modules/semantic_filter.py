"""
semantic_filter.py
==================
Remove duplicate or near-duplicate questions using sentence-transformers
embedding similarity.
"""

import logging
from typing import Any

import numpy as np

from config import NLPConfig
from modules.utils import timed

logger = logging.getLogger(__name__)

# Singleton model cache
_st_model = None


def _get_model():
    """Load and cache the sentence-transformer model."""
    global _st_model
    if _st_model is None:
        from sentence_transformers import SentenceTransformer
        logger.info("Loading sentence-transformer: %s", NLPConfig.SENTENCE_TRANSFORMER_MODEL)
        _st_model = SentenceTransformer(NLPConfig.SENTENCE_TRANSFORMER_MODEL)
        logger.info("Sentence-transformer loaded")
    return _st_model


@timed
def filter_duplicates(
    questions: list[dict[str, Any]],
    threshold: float = NLPConfig.SIMILARITY_THRESHOLD,
) -> list[dict[str, Any]]:
    """
    Remove semantically duplicate questions.

    Parameters
    ----------
    questions : list[dict]
        List of question dicts (must have 'question' key).
    threshold : float
        Cosine similarity threshold above which questions are
        considered duplicates (default 0.85).

    Returns
    -------
    list[dict]
        Deduplicated question list.
    """
    if len(questions) <= 1:
        return questions

    # Extract question texts
    texts = [q.get("question", "") for q in questions]

    # Encode all questions
    try:
        model = _get_model()
        embeddings = model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
    except Exception as exc:
        logger.warning("Sentence-transformer failed (%s) — skipping dedup", exc)
        return questions

    # Compute pairwise cosine similarity
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1, norms)  # avoid div by zero
    normalised = embeddings / norms
    similarity_matrix = np.dot(normalised, normalised.T)

    # Greedy deduplication: keep the first (higher-ranked) question
    keep_indices: list[int] = []
    removed: set[int] = set()

    for i in range(len(questions)):
        if i in removed:
            continue
        keep_indices.append(i)

        # Mark similar questions as removed
        for j in range(i + 1, len(questions)):
            if j in removed:
                continue
            if similarity_matrix[i, j] >= threshold:
                # Keep the one with more content (longer question + answer)
                len_i = len(texts[i]) + len(questions[i].get("answer", ""))
                len_j = len(texts[j]) + len(questions[j].get("answer", ""))
                if len_j > len_i:
                    # j is better — swap: remove i, keep j
                    removed.add(i)
                    keep_indices.pop()  # remove i from keep
                    break
                else:
                    removed.add(j)

    filtered = [questions[i] for i in keep_indices]

    removed_count = len(questions) - len(filtered)
    if removed_count > 0:
        logger.info(
            "Semantic filter: removed %d duplicates (%d → %d)",
            removed_count, len(questions), len(filtered),
        )

    return filtered
