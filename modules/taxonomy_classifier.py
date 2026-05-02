"""
taxonomy_classifier.py
======================
Classify questions according to Bloom's Taxonomy levels:
Remember, Understand, Apply.
"""

import logging
import re

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Bloom's keyword patterns
# ---------------------------------------------------------------------------

_BLOOM_PATTERNS: dict[str, list[str]] = {
    "remember": [
        "what is", "what are", "who is", "who was", "who were",
        "when did", "when was", "when is", "where is", "where was",
        "name the", "list", "define", "identify", "state",
        "recall", "recognize", "which of the following",
        "fill in the blank", "true or false", "match the",
        "what does", "label", "select", "choose",
    ],
    "understand": [
        "explain", "describe", "summarize", "paraphrase",
        "compare", "contrast", "classify", "distinguish",
        "interpret", "illustrate", "discuss", "what is the difference",
        "what is the relationship", "why is", "why does", "why do",
        "what happens", "how does", "what role", "give an example",
        "in your own words", "what is the significance",
        "what is the meaning", "elaborate", "outline",
    ],
    "apply": [
        "how would", "how can", "how might", "calculate",
        "demonstrate", "apply", "solve", "use", "implement",
        "construct", "predict", "what would happen if",
        "show how", "compute", "determine", "produce",
        "modify", "adapt", "operate", "practice",
        "what if", "design", "plan", "develop",
        "analyze", "evaluate", "assess", "critically",
        "justify", "argue", "propose", "synthesize",
    ],
}


def classify_bloom(question: str, answer: str = "") -> str:
    """
    Classify a question into a Bloom's Taxonomy level.

    Parameters
    ----------
    question : str
        The question text.
    answer : str
        Optional answer text for additional context.

    Returns
    -------
    str
        One of 'remember', 'understand', 'apply'.
    """
    q_lower = question.lower().strip()

    # Score each level
    scores: dict[str, float] = {"remember": 0, "understand": 0, "apply": 0}

    for level, patterns in _BLOOM_PATTERNS.items():
        for pattern in patterns:
            if pattern in q_lower:
                scores[level] += 1.0
                # Boost for question-start matches
                if q_lower.startswith(pattern):
                    scores[level] += 1.5

    # Additional heuristics
    # Fill-in-the-blank → remember
    if "fill in the blank" in q_lower or "_________" in question:
        scores["remember"] += 2.0

    # MCQ with "which of" → remember
    if "which of the following" in q_lower:
        scores["remember"] += 1.0

    # Short factual answers → remember
    if answer:
        answer_words = len(answer.split())
        if answer_words <= 2:
            scores["remember"] += 0.5
        elif answer_words >= 10:
            scores["understand"] += 0.5

    # Question complexity (length as proxy)
    q_words = len(q_lower.split())
    if q_words > 20:
        scores["apply"] += 0.5
    elif q_words < 8:
        scores["remember"] += 0.3

    # Select highest scoring level
    best_level = max(scores, key=scores.get)  # type: ignore[arg-type]

    # If all scores are 0, default based on question word
    if all(v == 0 for v in scores.values()):
        if q_lower.startswith(("what", "who", "when", "where")):
            best_level = "remember"
        elif q_lower.startswith(("why", "how")):
            best_level = "understand"
        else:
            best_level = "remember"

    return best_level
