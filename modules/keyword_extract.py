"""
keyword_extract.py
==================
Extract educationally relevant keywords and concepts from preprocessed text.
Combines TF-IDF scoring, POS filtering, NER boosting, and frequency analysis.
"""

import logging
from collections import Counter
from typing import Any

from modules.utils import timed
from config import NLPConfig

logger = logging.getLogger(__name__)


@timed
def extract_keywords(
    processed_data: dict[str, Any],
    top_n: int = NLPConfig.MAX_KEYWORDS,
) -> list[tuple[str, float, str]]:
    """
    Extract ranked keywords from preprocessed text using TF-IDF + POS filtering.

    Parameters
    ----------
    processed_data : dict
        Output from ``preprocess_text()``.
    top_n : int
        Maximum number of keywords to return.

    Returns
    -------
    list[tuple[str, float, str]]
        List of (keyword, score, pos_tag) tuples sorted by score descending.
    """
    from sklearn.feature_extraction.text import TfidfVectorizer

    sentences = processed_data["sentences"]
    pos_tags = processed_data["pos_tags"]
    entities = processed_data["entities"]

    if not sentences:
        logger.warning("No sentences available for keyword extraction")
        return []

    # --- TF-IDF scoring ---
    vectorizer = TfidfVectorizer(
        max_features=500,
        stop_words="english",
        ngram_range=(1, 2),
        min_df=1,
        max_df=0.95,
    )

    try:
        tfidf_matrix = vectorizer.fit_transform(sentences)
    except ValueError:
        logger.warning("TF-IDF fitting failed — likely too few documents")
        return []

    feature_names = vectorizer.get_feature_names_out()
    # Average TF-IDF across all sentences
    avg_scores = tfidf_matrix.mean(axis=0).A1
    tfidf_scores = dict(zip(feature_names, avg_scores))

    # --- POS-based candidate selection ---
    IMPORTANT_POS = {"NOUN", "PROPN", "ADJ"}
    pos_map: dict[str, str] = {}
    word_freq: Counter = Counter()

    for sent_tags in pos_tags:
        for word, pos in sent_tags:
            lower_word = word.lower()
            if pos in IMPORTANT_POS and len(lower_word) > 2:
                pos_map[lower_word] = pos
                word_freq[lower_word] += 1

    # --- Entity boosting ---
    entity_set: set[str] = set()
    for ent in entities:
        entity_set.add(ent["text"].lower())

    # --- Scoring ---
    keyword_scores: dict[str, float] = {}
    keyword_pos: dict[str, str] = {}

    for word, pos in pos_map.items():
        score = 0.0

        # TF-IDF component
        if word in tfidf_scores:
            score += tfidf_scores[word] * 3.0

        # Check bigrams containing this word
        for feature, tfidf_val in tfidf_scores.items():
            if " " in feature and word in feature.split():
                score += tfidf_val * 1.5

        # Frequency component (normalised)
        max_freq = max(word_freq.values()) if word_freq else 1
        score += (word_freq.get(word, 0) / max_freq) * 1.0

        # Entity boost
        for entity in entity_set:
            if word in entity or entity in word:
                score += 2.0
                break

        # POS boost: proper nouns are more important
        if pos == "PROPN":
            score *= 1.3
        elif pos == "NOUN":
            score *= 1.1

        if score > 0:
            keyword_scores[word] = score
            keyword_pos[word] = pos

    # Sort and return top-N
    sorted_keywords = sorted(keyword_scores.items(), key=lambda x: x[1], reverse=True)
    results = [
        (word, round(score, 4), keyword_pos.get(word, "NOUN"))
        for word, score in sorted_keywords[:top_n]
    ]

    logger.info("Extracted %d keywords (top: %s)", len(results),
                ", ".join(w for w, _, _ in results[:5]))
    return results


@timed
def extract_concepts(
    processed_data: dict[str, Any],
    top_n: int = 50,
) -> list[str]:
    """
    Extract educational concepts by combining NER entities, noun chunks, and keywords.

    Parameters
    ----------
    processed_data : dict
        Output from ``preprocess_text()``.
    top_n : int
        Maximum number of concepts to return.

    Returns
    -------
    list[str]
        Deduplicated, ranked list of concept strings.
    """
    entities = processed_data.get("entities", [])
    noun_chunks = processed_data.get("noun_chunks", [])

    # Collect all concept candidates
    concept_scores: dict[str, float] = {}

    # Named entities (highest priority)
    for ent in entities:
        text = ent["text"].strip()
        if len(text) > 2:
            key = text.lower()
            concept_scores[key] = concept_scores.get(key, 0) + 3.0
            # Preserve original casing for the best version
            concept_scores[f"__orig__{key}"] = 0  # placeholder
            concept_scores[key] = concept_scores[key]

    # Noun chunks (medium priority)
    for chunk in noun_chunks:
        chunk_lower = chunk.lower()
        if len(chunk_lower.split()) <= 4 and len(chunk_lower) > 2:
            concept_scores[chunk_lower] = concept_scores.get(chunk_lower, 0) + 2.0

    # Extract keywords and add (lower priority)
    keywords = extract_keywords(processed_data, top_n=40)
    for kw, score, _ in keywords:
        concept_scores[kw] = concept_scores.get(kw, 0) + score

    # Remove placeholder entries
    concept_scores = {k: v for k, v in concept_scores.items() if not k.startswith("__orig__")}

    # Deduplicate: remove substrings
    sorted_concepts = sorted(concept_scores.items(), key=lambda x: x[1], reverse=True)
    final: list[str] = []
    seen: set[str] = set()

    for concept, _ in sorted_concepts:
        if concept in seen:
            continue
        # Check if this concept is a substring of an already-added concept
        is_substring = any(concept in existing for existing in seen)
        if not is_substring:
            final.append(concept)
            seen.add(concept)

        if len(final) >= top_n:
            break

    logger.info("Extracted %d concepts", len(final))
    return final
