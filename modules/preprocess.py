"""
preprocess.py
=============
NLP preprocessing pipeline using spaCy and NLTK.
Handles sentence segmentation, tokenization, lemmatization, stopword
removal, entity extraction, and noun-chunk extraction.
"""

import logging
import re
from typing import Any

from modules.utils import timed, normalize_whitespace
from config import NLPConfig

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Singleton spaCy model loader
# ---------------------------------------------------------------------------
_nlp_model = None


def _get_spacy_model():
    """Load and cache the spaCy model (singleton)."""
    global _nlp_model
    if _nlp_model is None:
        import spacy
        logger.info("Loading spaCy model: %s", NLPConfig.SPACY_MODEL)
        _nlp_model = spacy.load(NLPConfig.SPACY_MODEL)
        logger.info("spaCy model loaded successfully")
    return _nlp_model


# ---------------------------------------------------------------------------
# NLTK setup
# ---------------------------------------------------------------------------
_nltk_ready = False


def _ensure_nltk():
    """Download required NLTK data if not present."""
    global _nltk_ready
    if _nltk_ready:
        return
    import nltk
    for resource in ["punkt", "punkt_tab", "stopwords", "averaged_perceptron_tagger",
                     "averaged_perceptron_tagger_eng", "wordnet"]:
        try:
            nltk.data.find(f"tokenizers/{resource}" if "punkt" in resource
                           else f"corpora/{resource}" if resource in ("stopwords", "wordnet")
                           else f"taggers/{resource}")
        except LookupError:
            logger.info("Downloading NLTK resource: %s", resource)
            nltk.download(resource, quiet=True)
    _nltk_ready = True


# ---------------------------------------------------------------------------
# Preprocessing pipeline
# ---------------------------------------------------------------------------

@timed
def preprocess_text(raw_text: str) -> dict[str, Any]:
    """
    Run the full NLP preprocessing pipeline on raw text.

    Parameters
    ----------
    raw_text : str
        Raw extracted document text.

    Returns
    -------
    dict
        Structured data with keys:
        - sentences : list[str]        — cleaned, segmented sentences
        - tokens    : list[list[str]]  — tokenised sentences
        - lemmas    : list[list[str]]  — lemmatised tokens
        - entities  : list[dict]       — named entities {text, label, start, end}
        - noun_chunks : list[str]      — extracted noun phrases
        - pos_tags  : list[list[tuple]]— POS tags per sentence
    """
    _ensure_nltk()
    nlp = _get_spacy_model()

    # Normalise whitespace
    text = normalize_whitespace(raw_text)

    # Process with spaCy
    doc = nlp(text)

    # --- Sentence segmentation ---
    sentences: list[str] = []
    for sent in doc.sents:
        cleaned = sent.text.strip()
        # Filter: minimum length, must contain alpha chars
        if (len(cleaned.split()) >= NLPConfig.MIN_SENTENCE_LENGTH
                and re.search(r"[a-zA-Z]", cleaned)):
            sentences.append(cleaned)

    # --- Tokenization & Lemmatization ---
    from nltk.corpus import stopwords
    stop_words = set(stopwords.words("english"))

    tokens: list[list[str]] = []
    lemmas: list[list[str]] = []
    pos_tags: list[list[tuple]] = []

    for sent_text in sentences:
        sent_doc = nlp(sent_text)
        sent_tokens: list[str] = []
        sent_lemmas: list[str] = []
        sent_pos: list[tuple] = []

        for token in sent_doc:
            if token.is_punct or token.is_space:
                continue

            sent_pos.append((token.text, token.pos_))

            if token.text.lower() not in stop_words and not token.is_stop:
                sent_tokens.append(token.text)
                sent_lemmas.append(token.lemma_.lower())

        tokens.append(sent_tokens)
        lemmas.append(sent_lemmas)
        pos_tags.append(sent_pos)

    # --- Named Entity Recognition ---
    entities: list[dict] = []
    seen_entities: set[str] = set()
    for ent in doc.ents:
        key = f"{ent.text.lower()}:{ent.label_}"
        if key not in seen_entities and len(ent.text.strip()) > 1:
            entities.append({
                "text": ent.text.strip(),
                "label": ent.label_,
                "start": ent.start_char,
                "end": ent.end_char,
            })
            seen_entities.add(key)

    # --- Noun chunks ---
    noun_chunks: list[str] = []
    seen_chunks: set[str] = set()
    for chunk in doc.noun_chunks:
        cleaned = chunk.text.strip().lower()
        if cleaned not in seen_chunks and len(cleaned.split()) >= 1:
            noun_chunks.append(chunk.text.strip())
            seen_chunks.add(cleaned)

    logger.info(
        "Preprocessed: %d sentences, %d entities, %d noun chunks",
        len(sentences), len(entities), len(noun_chunks),
    )

    return {
        "sentences": sentences,
        "tokens": tokens,
        "lemmas": lemmas,
        "entities": entities,
        "noun_chunks": noun_chunks,
        "pos_tags": pos_tags,
    }
