"""
test_keyword_extract.py — Tests for keyword and concept extraction.
"""
import pytest


SAMPLE_PROCESSED = None


def _get_processed():
    global SAMPLE_PROCESSED
    if SAMPLE_PROCESSED is None:
        from modules.preprocess import preprocess_text
        text = (
            "Machine learning is a subset of artificial intelligence that enables "
            "systems to learn from data. Deep learning is a specialized form of "
            "machine learning using neural networks with multiple layers. "
            "Supervised learning requires labeled training data while unsupervised "
            "learning discovers patterns in unlabeled data."
        )
        SAMPLE_PROCESSED = preprocess_text(text)
    return SAMPLE_PROCESSED


class TestKeywordExtraction:
    def test_returns_list(self):
        from modules.keyword_extract import extract_keywords
        result = extract_keywords(_get_processed())
        assert isinstance(result, list)

    def test_keywords_have_scores(self):
        from modules.keyword_extract import extract_keywords
        result = extract_keywords(_get_processed(), top_n=10)
        for item in result:
            assert len(item) == 3  # (keyword, score, pos)
            assert isinstance(item[1], float)

    def test_relevant_keywords_found(self):
        from modules.keyword_extract import extract_keywords
        result = extract_keywords(_get_processed(), top_n=20)
        keywords_lower = [kw[0].lower() for kw in result]
        assert any("learning" in kw for kw in keywords_lower)


class TestConceptExtraction:
    def test_returns_list(self):
        from modules.keyword_extract import extract_concepts
        result = extract_concepts(_get_processed())
        assert isinstance(result, list)
        assert len(result) > 0

    def test_concepts_are_strings(self):
        from modules.keyword_extract import extract_concepts
        result = extract_concepts(_get_processed())
        for concept in result:
            assert isinstance(concept, str)
            assert len(concept) > 0
