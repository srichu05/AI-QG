"""
test_preprocess.py — Tests for NLP preprocessing pipeline.
"""
import pytest


SAMPLE_TEXT = (
    "Photosynthesis is the process by which green plants and certain other organisms "
    "transform light energy into chemical energy. During photosynthesis in green plants, "
    "light energy is captured and used to convert water, carbon dioxide, and minerals "
    "into oxygen and energy-rich organic compounds. The process of photosynthesis is "
    "critically important for life on Earth as it provides the oxygen we breathe."
)


class TestPreprocessText:
    def test_returns_dict(self):
        from modules.preprocess import preprocess_text
        result = preprocess_text(SAMPLE_TEXT)
        assert isinstance(result, dict)
        assert "sentences" in result
        assert "tokens" in result
        assert "lemmas" in result
        assert "entities" in result
        assert "noun_chunks" in result

    def test_sentences_extracted(self):
        from modules.preprocess import preprocess_text
        result = preprocess_text(SAMPLE_TEXT)
        assert len(result["sentences"]) >= 1

    def test_entities_have_labels(self):
        from modules.preprocess import preprocess_text
        result = preprocess_text(SAMPLE_TEXT)
        for ent in result["entities"]:
            assert "text" in ent
            assert "label" in ent

    def test_empty_text(self):
        from modules.preprocess import preprocess_text
        result = preprocess_text("")
        assert result["sentences"] == []

    def test_short_text_filtered(self):
        from modules.preprocess import preprocess_text
        result = preprocess_text("Hello.")
        # Very short sentences should be filtered out
        assert len(result["sentences"]) == 0
