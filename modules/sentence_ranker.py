"""
sentence_ranker.py
==================
Rank sentences by educational importance using TF-IDF cosine similarity
to the document centroid and concept-density scoring.
"""

import logging
from typing import Any

import numpy as np

from modules.utils import timed
from config import NLPConfig

logger = logging.getLogger(__name__)


@timed
def rank_sentences(
    sentences: list[str],
    keywords: list[tuple[str, float, str]] | list[str],
    top_n: int = NLPConfig.TOP_SENTENCES,
) -> list[str]:
    """
    Rank sentences by educational importance and return top-N.

    Scoring combines:
    1. TF-IDF cosine similarity to document centroid
    2. Concept density (keyword count per sentence)
    3. Length preference (moderate-length sentences preferred)

    Parameters
    ----------
    sentences : list[str]
        Preprocessed sentences.
    keywords : list
        Keywords from ``extract_keywords`` (tuples) or plain strings.
    top_n : int
        Number of top sentences to return.

    Returns
    -------
    list[str]
        Top-ranked sentences sorted by score.
    """
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    if not sentences:
        return []

    if len(sentences) <= top_n:
        return sentences

    # Normalise keywords to plain strings
    keyword_set: set[str] = set()
    for kw in keywords:
        if isinstance(kw, tuple):
            keyword_set.add(kw[0].lower())
        else:
            keyword_set.add(str(kw).lower())

    # --- TF-IDF cosine similarity to centroid ---
    vectorizer = TfidfVectorizer(stop_words="english", max_features=1000)
    try:
        tfidf_matrix = vectorizer.fit_transform(sentences)
    except ValueError:
        logger.warning("TF-IDF fitting failed for sentence ranking")
        return sentences[:top_n]

    # Document centroid = mean of all sentence vectors
    centroid = tfidf_matrix.mean(axis=0).A
    similarities = cosine_similarity(tfidf_matrix, centroid).flatten()

    # --- Concept density ---
    concept_densities: list[float] = []
    for sent in sentences:
        words = set(sent.lower().split())
        count = sum(1 for kw in keyword_set if kw in words or kw in sent.lower())
        density = count / max(len(words), 1)
        concept_densities.append(density)

    concept_densities_arr = np.array(concept_densities)

    # Normalise concept density to [0, 1]
    max_density = concept_densities_arr.max()
    if max_density > 0:
        concept_densities_arr = concept_densities_arr / max_density

    # --- Length preference ---
    # Prefer sentences with 10-40 words (educational sweet spot)
    length_scores: list[float] = []
    for sent in sentences:
        word_count = len(sent.split())
        if 10 <= word_count <= 40:
            length_scores.append(1.0)
        elif 5 <= word_count < 10 or 40 < word_count <= 60:
            length_scores.append(0.6)
        else:
            length_scores.append(0.3)

    length_arr = np.array(length_scores)

    # --- Combined score ---
    # Weights: similarity=0.5, concept_density=0.35, length=0.15
    final_scores = (
        0.50 * similarities
        + 0.35 * concept_densities_arr
        + 0.15 * length_arr
    )

    # Get top-N indices
    top_indices = np.argsort(final_scores)[::-1][:top_n]

    # Return in document order for coherence
    top_indices_sorted = sorted(top_indices)
    ranked = [sentences[i] for i in top_indices_sorted]

    logger.info(
        "Ranked %d → %d sentences (top score: %.3f, min: %.3f)",
        len(sentences), len(ranked),
        final_scores[top_indices[0]], final_scores[top_indices[-1]],
    )
    return ranked
