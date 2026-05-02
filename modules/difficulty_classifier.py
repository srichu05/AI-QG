"""
difficulty_classifier.py
========================
Classify question difficulty as Easy / Medium / Hard based on
sentence complexity, answer type, concept count, and question structure.
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Difficulty classification
# ---------------------------------------------------------------------------


def classify_difficulty(
    question: str,
    answer: str,
    source_sentence: str = "",
) -> str:
    """
    Classify question difficulty level.

    Scoring criteria:
    - **Easy**: Factual recall, short answers, named entities, definitions
    - **Medium**: Conceptual understanding, moderate complexity
    - **Hard**: Inferential, analytical, multi-concept, long answers

    Parameters
    ----------
    question : str
        The question text.
    answer : str
        The correct answer.
    source_sentence : str
        The source sentence the question was derived from.

    Returns
    -------
    str
        One of 'easy', 'medium', 'hard'.
    """
    score = 0.0  # Higher = harder

    q_lower = question.lower().strip()
    a_lower = answer.lower().strip()

    # --- Factor 1: Question word complexity ---
    easy_starters = ["what is", "what are", "who is", "who was", "name the",
                     "which of", "define", "list", "state the", "what does"]
    medium_starters = ["explain", "describe", "compare", "what happens",
                       "how does", "why is", "what role", "distinguish"]
    hard_starters = ["analyze", "evaluate", "how would", "what if",
                     "critically", "justify", "assess", "to what extent",
                     "synthesize", "argue", "propose"]

    for s in hard_starters:
        if q_lower.startswith(s):
            score += 3.0
            break
    else:
        for s in medium_starters:
            if q_lower.startswith(s):
                score += 2.0
                break
        else:
            for s in easy_starters:
                if q_lower.startswith(s):
                    score += 1.0
                    break
            else:
                score += 1.5  # Default: medium-ish

    # --- Factor 2: Answer length ---
    answer_words = len(a_lower.split())
    if answer_words <= 3:
        score += 0.5  # Short = easier
    elif answer_words <= 8:
        score += 1.5
    else:
        score += 2.5  # Long answer = harder

    # --- Factor 3: Source sentence complexity ---
    if source_sentence:
        sent_words = len(source_sentence.split())
        # Subordinate clauses (commas, semicolons)
        clause_count = source_sentence.count(",") + source_sentence.count(";")

        if sent_words > 30 or clause_count >= 3:
            score += 2.0
        elif sent_words > 18 or clause_count >= 1:
            score += 1.0
        else:
            score += 0.5

    # --- Factor 4: Concept density ---
    # Count capitalised terms (likely concepts/entities)
    capital_words = len(re.findall(r"\b[A-Z][a-z]+\b", question))
    if capital_words >= 3:
        score += 1.5
    elif capital_words >= 1:
        score += 0.5

    # --- Factor 5: Question type specific ---
    if "fill in the blank" in q_lower:
        score -= 0.5  # Fill blanks are generally easier
    if "which of the following" in q_lower:
        score -= 0.3  # MCQ recognition is easier than recall

    # --- Classify ---
    if score <= 3.5:
        return "easy"
    elif score <= 6.0:
        return "medium"
    else:
        return "hard"
