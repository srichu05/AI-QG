"""
test_pipeline.py — End-to-end pipeline test with a sample text document.
"""
import os
import tempfile
import pytest


SAMPLE_EDUCATIONAL_TEXT = """
Machine Learning Fundamentals

Machine learning is a branch of artificial intelligence that focuses on building systems
that learn from data. Instead of being explicitly programmed, these systems improve their
performance on a specific task through experience.

There are three main types of machine learning: supervised learning, unsupervised learning,
and reinforcement learning. Supervised learning uses labeled training data to learn a mapping
from inputs to outputs. Common algorithms include linear regression, decision trees, and
support vector machines.

Unsupervised learning finds hidden patterns in data without labeled responses. Clustering
algorithms such as K-means and hierarchical clustering group similar data points together.
Dimensionality reduction techniques like Principal Component Analysis reduce the number of
features in a dataset.

Reinforcement learning involves an agent that learns to make decisions by interacting with
an environment. The agent receives rewards or penalties for its actions and learns to
maximize cumulative reward over time. Applications include game playing, robotics, and
autonomous vehicles.

Deep learning is a subset of machine learning that uses neural networks with many layers.
Convolutional Neural Networks are used for image recognition while Recurrent Neural Networks
handle sequential data such as text and time series. Transfer learning allows models
pre-trained on large datasets to be fine-tuned for specific tasks.
"""


class TestEndToEndPipeline:
    def test_extract_preprocess_keywords(self):
        """Test extraction → preprocessing → keyword extraction chain."""
        from modules.extractor import extract_text
        from modules.preprocess import preprocess_text
        from modules.keyword_extract import extract_keywords, extract_concepts

        # Create temp file
        fd, path = tempfile.mkstemp(suffix=".txt")
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(SAMPLE_EDUCATIONAL_TEXT)

        try:
            # Extract
            raw_text = extract_text(path)
            assert len(raw_text) > 100

            # Preprocess
            processed = preprocess_text(raw_text)
            assert len(processed["sentences"]) >= 3

            # Keywords
            keywords = extract_keywords(processed)
            assert len(keywords) >= 5
            keyword_words = [k[0].lower() for k in keywords]
            assert any("learning" in kw for kw in keyword_words)

            # Concepts
            concepts = extract_concepts(processed)
            assert len(concepts) >= 3

        finally:
            os.unlink(path)

    def test_sentence_ranking(self):
        """Test sentence ranking produces ordered results."""
        from modules.preprocess import preprocess_text
        from modules.keyword_extract import extract_keywords
        from modules.sentence_ranker import rank_sentences

        processed = preprocess_text(SAMPLE_EDUCATIONAL_TEXT)
        keywords = extract_keywords(processed)
        ranked = rank_sentences(processed["sentences"], keywords, top_n=5)

        assert isinstance(ranked, list)
        assert len(ranked) <= 5
        assert all(isinstance(s, str) for s in ranked)

    def test_blank_generation_from_pipeline(self):
        """Test blank generation from preprocessed and ranked content."""
        from modules.preprocess import preprocess_text
        from modules.keyword_extract import extract_keywords
        from modules.sentence_ranker import rank_sentences
        from modules.blank_generator import generate_fill_blanks

        processed = preprocess_text(SAMPLE_EDUCATIONAL_TEXT)
        keywords = extract_keywords(processed)
        ranked = rank_sentences(processed["sentences"], keywords)
        keyword_strings = [kw[0] for kw in keywords]

        blanks = generate_fill_blanks(ranked, keyword_strings)
        assert isinstance(blanks, list)
        if blanks:
            assert blanks[0]["question_type"] == "fill_blank"

    def test_classification(self):
        """Test difficulty and taxonomy classification."""
        from modules.difficulty_classifier import classify_difficulty
        from modules.taxonomy_classifier import classify_bloom

        d = classify_difficulty("What is machine learning?", "a branch of AI", "")
        assert d in ("easy", "medium", "hard")

        b = classify_bloom("Define supervised learning.", "")
        assert b in ("remember", "understand", "apply")
