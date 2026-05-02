"""
blank_generator.py
==================
Generate fill-in-the-blank questions by replacing key educational concepts
with blanks in ranked sentences.
"""

import logging
import re
from typing import Any

from modules.utils import timed

logger = logging.getLogger(__name__)


@timed
def generate_fill_blanks(
    ranked_sentences: list[str],
    keywords: list[str],
    max_blanks_per_sentence: int = 1,
    max_total: int = 15,
) -> list[dict[str, Any]]:
    """
    Generate fill-in-the-blank questions from ranked sentences.

    For each sentence, identifies the most important keyword present
    and replaces it with a blank.

    Parameters
    ----------
    ranked_sentences : list[str]
        Top-ranked educational sentences.
    keywords : list[str]
        Extracted keywords (plain strings, ordered by importance).
    max_blanks_per_sentence : int
        Maximum blanks to create per sentence.
    max_total : int
        Maximum total fill-in-the-blank questions.

    Returns
    -------
    list[dict]
        List of question dicts with keys:
        question, answer, source_sentence, question_type
    """
    questions: list[dict[str, Any]] = []
    used_keywords: set[str] = set()

    for sentence in ranked_sentences:
        if len(questions) >= max_total:
            break

        blanks_created = 0
        sentence_lower = sentence.lower()

        for keyword in keywords:
            if blanks_created >= max_blanks_per_sentence:
                break
            if len(questions) >= max_total:
                break

            kw_lower = keyword.lower()

            # Skip very short or already-used keywords
            if len(kw_lower) < 3 or kw_lower in used_keywords:
                continue

            # Check if keyword appears in the sentence
            if kw_lower not in sentence_lower:
                continue

            # Find the keyword in original casing (case-insensitive match)
            pattern = re.compile(re.escape(keyword), re.IGNORECASE)
            match = pattern.search(sentence)
            if not match:
                continue

            original_span = match.group()

            # Ensure the keyword is a meaningful concept (not a common word)
            if _is_trivial_word(kw_lower):
                continue

            # Create the blank question
            blank_sentence = (
                sentence[:match.start()]
                + "_________"
                + sentence[match.end():]
            )

            # Clean up any double spaces
            blank_sentence = re.sub(r"\s+", " ", blank_sentence).strip()

            questions.append({
                "question": f"Fill in the blank: {blank_sentence}",
                "answer": original_span,
                "source_sentence": sentence,
                "question_type": "fill_blank",
            })

            used_keywords.add(kw_lower)
            blanks_created += 1

    logger.info("Generated %d fill-in-the-blank questions", len(questions))
    return questions


def _is_trivial_word(word: str) -> bool:
    """Check if a word is too trivial for a blank question."""
    trivial = {
        "also", "many", "much", "very", "more", "most", "some",
        "other", "each", "every", "such", "like", "just", "well",
        "even", "still", "already", "often", "never", "always",
        "first", "last", "new", "old", "big", "small", "good",
        "great", "important", "different", "several", "various",
        "used", "using", "known", "called", "made", "found",
        "based", "including", "following", "given", "related",
        "example", "way", "part", "form", "type", "case",
    }
    return word in trivial
