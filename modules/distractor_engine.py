"""
distractor_engine.py
====================
Intelligent distractor generation for MCQs using WordNet, semantic
neighbors, and concept similarity.
"""

import logging
import random
from typing import Any

from modules.utils import timed

logger = logging.getLogger(__name__)

_wordnet_ready = False


def _ensure_wordnet():
    global _wordnet_ready
    if _wordnet_ready:
        return
    import nltk
    for resource in ["wordnet", "omw-1.4"]:
        try:
            nltk.data.find(f"corpora/{resource}")
        except LookupError:
            nltk.download(resource, quiet=True)
    _wordnet_ready = True


@timed
def generate_distractors(
    answer: str,
    context: str = "",
    keywords: list[str] | None = None,
    concepts: list[str] | None = None,
    num_distractors: int = 3,
) -> list[str]:
    """
    Generate plausible but incorrect distractors for a given answer.

    Uses WordNet, concept neighbors, keyword pool, and morphological
    variations in priority order.
    """
    _ensure_wordnet()
    answer_lower = answer.lower().strip()
    distractors: list[str] = []
    seen: set[str] = {answer_lower}

    # Strategy 1: WordNet
    for d in _wordnet_distractors(answer, num_distractors * 2):
        if d.lower() not in seen and not _is_substring_match(d, answer):
            distractors.append(d)
            seen.add(d.lower())
        if len(distractors) >= num_distractors:
            break

    # Strategy 2: Concept neighbors
    if len(distractors) < num_distractors and concepts:
        for d in _concept_neighbors(answer, concepts):
            if d.lower() not in seen and not _is_substring_match(d, answer):
                distractors.append(d)
                seen.add(d.lower())
            if len(distractors) >= num_distractors:
                break

    # Strategy 3: Keyword pool
    if len(distractors) < num_distractors and keywords:
        for d in _keyword_pool_distractors(answer, keywords):
            if d.lower() not in seen and not _is_substring_match(d, answer):
                distractors.append(d)
                seen.add(d.lower())
            if len(distractors) >= num_distractors:
                break

    # Strategy 4: Morphological (last resort)
    if len(distractors) < num_distractors:
        for d in _morphological_distractors(answer):
            if d.lower() not in seen and not _is_substring_match(d, answer):
                distractors.append(d)
                seen.add(d.lower())
            if len(distractors) >= num_distractors:
                break

    return distractors[:num_distractors]


def _wordnet_distractors(answer: str, max_count: int = 6) -> list[str]:
    from nltk.corpus import wordnet as wn
    candidates: list[str] = []
    for word in answer.lower().split():
        synsets = wn.synsets(word)
        if not synsets:
            continue
        primary = synsets[0]
        for lemma in primary.lemmas():
            name = lemma.name().replace("_", " ")
            if name.lower() != word:
                candidates.append(name)
        for hypernym in primary.hypernyms():
            for lemma in hypernym.lemmas():
                candidates.append(lemma.name().replace("_", " "))
        for hypernym in primary.hypernyms():
            for hyponym in hypernym.hyponyms():
                if hyponym != primary:
                    for lemma in hyponym.lemmas():
                        name = lemma.name().replace("_", " ")
                        if name.lower() != word:
                            candidates.append(name)
        if len(candidates) >= max_count:
            break
    seen: set[str] = set()
    unique: list[str] = []
    for c in candidates:
        if c.lower() not in seen and len(c) > 1:
            unique.append(c)
            seen.add(c.lower())
    random.shuffle(unique)
    return unique[:max_count]


def _concept_neighbors(answer: str, concepts: list[str]) -> list[str]:
    answer_lower = answer.lower().strip()
    candidates = []
    for concept in concepts:
        cl = concept.lower().strip()
        if cl == answer_lower or cl in answer_lower or answer_lower in cl:
            continue
        len_ratio = len(concept) / max(len(answer), 1)
        if 0.3 <= len_ratio <= 3.0:
            candidates.append(concept)
    random.shuffle(candidates)
    return candidates[:6]


def _keyword_pool_distractors(answer: str, keywords: list[str]) -> list[str]:
    answer_lower = answer.lower().strip()
    candidates = []
    for kw in keywords:
        kl = kw.lower().strip()
        if kl == answer_lower or kl in answer_lower or answer_lower in kl:
            continue
        if len(kw) > 2:
            candidates.append(kw)
    random.shuffle(candidates)
    return candidates[:6]


def _morphological_distractors(answer: str) -> list[str]:
    distractors = []
    for prefix in ["non-", "un-", "pre-", "post-", "anti-", "sub-"]:
        distractors.append(prefix + answer.lower())
    for suffix in [" system", " process", " theory", " model", " method"]:
        if not answer.lower().endswith(suffix.strip()):
            distractors.append(answer + suffix)
    random.shuffle(distractors)
    return distractors[:4]


def _is_substring_match(distractor: str, answer: str) -> bool:
    d, a = distractor.lower().strip(), answer.lower().strip()
    if d == a:
        return True
    if len(d) > 3 and len(a) > 3 and (d in a or a in d):
        return True
    return False
