"""
mcq_generator.py
================
Assemble Multiple Choice Questions with correct answer + distractors.
"""

import logging
import random
from typing import Any

from modules.distractor_engine import generate_distractors
from modules.utils import timed

logger = logging.getLogger(__name__)


@timed
def generate_mcqs(
    questions: list[dict[str, Any]],
    keywords: list[str],
    concepts: list[str],
    max_mcqs: int = 15,
) -> list[dict[str, Any]]:
    """
    Convert question-answer pairs into MCQs with 4 options.

    Parameters
    ----------
    questions : list[dict]
        Existing questions with 'answer' and 'source_sentence' keys.
    keywords : list[str]
        Keywords from the document for distractor generation.
    concepts : list[str]
        Concepts from the document for distractor generation.
    max_mcqs : int
        Maximum MCQs to generate.

    Returns
    -------
    list[dict]
        MCQ dicts with keys: question, answer, options, correct_index,
        source_sentence, question_type, distractors.
    """
    mcqs: list[dict[str, Any]] = []
    used_answers: set[str] = set()

    # Select questions suitable for MCQ conversion
    candidates = [
        q for q in questions
        if q.get("answer", "").strip()
        and len(q["answer"].strip()) > 2
        and len(q["answer"].strip().split()) <= 8
    ]

    for q in candidates:
        if len(mcqs) >= max_mcqs:
            break

        answer = q["answer"].strip()
        answer_lower = answer.lower()

        # Skip duplicate answers
        if answer_lower in used_answers:
            continue

        # Generate distractors
        distractors = generate_distractors(
            answer=answer,
            context=q.get("source_sentence", ""),
            keywords=keywords,
            concepts=concepts,
            num_distractors=3,
        )

        # Need at least 2 distractors for a reasonable MCQ
        if len(distractors) < 2:
            continue

        # Pad with generic distractors if needed
        while len(distractors) < 3:
            distractors.append(f"None of the above")

        # Build options list and shuffle
        options = [answer] + distractors[:3]
        random.shuffle(options)
        correct_index = options.index(answer)

        # Create MCQ question text
        q_text = q.get("question", "")
        if not q_text:
            q_text = f"Which of the following is correct regarding the given context?"

        mcqs.append({
            "question": q_text,
            "answer": answer,
            "options": options,
            "correct_index": correct_index,
            "distractors": distractors[:3],
            "source_sentence": q.get("source_sentence", ""),
            "question_type": "mcq",
        })
        used_answers.add(answer_lower)

    logger.info("Generated %d MCQs from %d candidates", len(mcqs), len(candidates))
    return mcqs
