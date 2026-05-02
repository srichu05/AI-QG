"""
test_generators.py — Tests for question generation, classification, and filtering.
"""
import pytest


class TestBlankGenerator:
    def test_generates_blanks(self):
        from modules.blank_generator import generate_fill_blanks
        sentences = [
            "Photosynthesis converts carbon dioxide and water into glucose and oxygen.",
            "The mitochondria is the powerhouse of the cell and produces ATP.",
        ]
        keywords = ["photosynthesis", "carbon dioxide", "mitochondria", "glucose", "ATP"]
        result = generate_fill_blanks(sentences, keywords)
        assert isinstance(result, list)
        if result:
            q = result[0]
            assert "question" in q
            assert "answer" in q
            assert q["question_type"] == "fill_blank"
            assert "_________" in q["question"]


class TestDifficultyClassifier:
    def test_easy_question(self):
        from modules.difficulty_classifier import classify_difficulty
        result = classify_difficulty("What is photosynthesis?", "the process of converting light", "")
        assert result in ("easy", "medium", "hard")

    def test_hard_question(self):
        from modules.difficulty_classifier import classify_difficulty
        result = classify_difficulty(
            "Analyze the relationship between photosynthesis and cellular respiration in the context of energy flow.",
            "Photosynthesis produces glucose and oxygen which are consumed by cellular respiration to generate ATP",
            "Complex sentence with multiple clauses, discussing energy flow, metabolic pathways, and biochemical processes in detail."
        )
        assert result in ("medium", "hard")


class TestTaxonomyClassifier:
    def test_remember(self):
        from modules.taxonomy_classifier import classify_bloom
        result = classify_bloom("What is the capital of France?", "Paris")
        assert result == "remember"

    def test_understand(self):
        from modules.taxonomy_classifier import classify_bloom
        result = classify_bloom("Explain how photosynthesis works.", "")
        assert result == "understand"

    def test_apply(self):
        from modules.taxonomy_classifier import classify_bloom
        result = classify_bloom("How would you calculate the velocity of a projectile?", "")
        assert result == "apply"


class TestDistractorEngine:
    def test_generates_distractors(self):
        from modules.distractor_engine import generate_distractors
        result = generate_distractors("photosynthesis", keywords=["respiration", "osmosis", "diffusion"])
        assert isinstance(result, list)

    def test_distractors_not_equal_answer(self):
        from modules.distractor_engine import generate_distractors
        result = generate_distractors("oxygen", keywords=["nitrogen", "hydrogen", "carbon"])
        for d in result:
            assert d.lower().strip() != "oxygen"


class TestMCQGenerator:
    def test_generates_mcqs(self):
        from modules.mcq_generator import generate_mcqs
        questions = [
            {"question": "What is the powerhouse of the cell?", "answer": "mitochondria",
             "source_sentence": "The mitochondria is known as the powerhouse of the cell.", "question_type": "wh"},
        ]
        keywords = ["cell", "nucleus", "ribosome", "cytoplasm", "membrane"]
        concepts = ["cell membrane", "nucleus", "ribosome", "cytoplasm"]
        result = generate_mcqs(questions, keywords, concepts, max_mcqs=5)
        assert isinstance(result, list)
        if result:
            mcq = result[0]
            assert mcq["question_type"] == "mcq"
            assert "options" in mcq
            assert "correct_index" in mcq
