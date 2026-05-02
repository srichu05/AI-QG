"""
hf_generator.py
===============
Hugging Face Inference API integration for question generation.
Uses valhalla/t5-base-qg-hl as primary model with automatic fallback
to iarfmoose/t5-base-question-generator.
"""

import logging
import re
import time
from typing import Any

import requests

from config import HuggingFaceConfig
from modules.utils import timed

logger = logging.getLogger(__name__)


class HuggingFaceGenerator:
    """
    Generate WH and short-answer questions using Hugging Face Inference API.

    Implements retry logic, timeout handling, and automatic model fallback.
    """

    def __init__(self):
        self.api_token = HuggingFaceConfig.API_TOKEN
        self.primary_model = HuggingFaceConfig.PRIMARY_MODEL
        self.fallback_model = HuggingFaceConfig.FALLBACK_MODEL
        self.api_url = HuggingFaceConfig.API_URL
        self.timeout = HuggingFaceConfig.TIMEOUT
        self.max_retries = HuggingFaceConfig.MAX_RETRIES
        self.headers = {"Authorization": f"Bearer {self.api_token}"}

        if not self.api_token:
            logger.warning("HF_API_TOKEN not set — HF generation will be skipped")

    # ------------------------------------------------------------------
    # Internal API call
    # ------------------------------------------------------------------

    def _call_api(self, payload: dict, model: str) -> list[dict] | None:
        """
        Send a request to the HF Inference API with retries.

        Returns
        -------
        list[dict] | None
            Parsed JSON response or None on failure.
        """
        url = f"{self.api_url}{model}"

        for attempt in range(1, self.max_retries + 1):
            try:
                response = requests.post(
                    url,
                    headers=self.headers,
                    json=payload,
                    timeout=self.timeout,
                )

                if response.status_code == 200:
                    return response.json()

                # Model is loading — wait and retry
                if response.status_code == 503:
                    data = response.json()
                    wait_time = data.get("estimated_time", 20)
                    logger.info(
                        "Model %s loading — waiting %.0fs (attempt %d/%d)",
                        model, wait_time, attempt, self.max_retries,
                    )
                    time.sleep(min(wait_time, 30))
                    continue

                # Rate limited
                if response.status_code == 429:
                    wait_time = 2 ** attempt
                    logger.warning(
                        "Rate limited — waiting %ds (attempt %d/%d)",
                        wait_time, attempt, self.max_retries,
                    )
                    time.sleep(wait_time)
                    continue

                logger.error(
                    "HF API error %d: %s (attempt %d/%d)",
                    response.status_code, response.text[:200],
                    attempt, self.max_retries,
                )

            except requests.exceptions.Timeout:
                logger.warning(
                    "HF API timeout (attempt %d/%d)", attempt, self.max_retries
                )
            except requests.exceptions.ConnectionError:
                logger.warning(
                    "HF API connection error (attempt %d/%d)", attempt, self.max_retries
                )
            except Exception as exc:
                logger.error("HF API unexpected error: %s", exc)
                break

            if attempt < self.max_retries:
                time.sleep(2 ** attempt)

        return None

    # ------------------------------------------------------------------
    # Question generation from a single sentence
    # ------------------------------------------------------------------

    def generate_questions(
        self,
        sentence: str,
        context: str = "",
        answer_span: str = "",
    ) -> list[dict[str, str]]:
        """
        Generate questions for a given sentence.

        Parameters
        ----------
        sentence : str
            The target sentence to generate questions from.
        context : str
            Surrounding context for better question quality.
        answer_span : str
            Optional highlighted answer span.

        Returns
        -------
        list[dict]
            List of {question, answer, source_sentence, question_type} dicts.
        """
        if not self.api_token:
            return self._generate_rule_based(sentence, answer_span)

        questions: list[dict[str, str]] = []

        # Format input for valhalla/t5-base-qg-hl
        # This model expects: "generate question: <hl> answer <hl> context"
        if answer_span:
            input_text = sentence.replace(
                answer_span, f"<hl> {answer_span} <hl>"
            )
            input_text = f"generate question: {input_text}"
        else:
            input_text = f"generate question: {sentence}"

        payload = {
            "inputs": input_text,
            "parameters": {
                "max_length": 128,
                "num_beams": 4,
                "early_stopping": True,
            },
        }

        # Try primary model
        result = self._call_api(payload, self.primary_model)

        if result is None:
            # Fallback model (different input format)
            fallback_input = f"{sentence}"
            if context:
                fallback_input = f"{sentence} </s> {context[:300]}"

            fallback_payload = {
                "inputs": fallback_input,
                "parameters": {"max_length": 128, "num_beams": 4},
            }
            result = self._call_api(fallback_payload, self.fallback_model)

        if result is None:
            logger.warning("Both HF models failed — using rule-based fallback")
            return self._generate_rule_based(sentence, answer_span)

        # Parse response
        generated_texts = []
        if isinstance(result, list):
            for item in result:
                if isinstance(item, dict) and "generated_text" in item:
                    generated_texts.append(item["generated_text"])
                elif isinstance(item, str):
                    generated_texts.append(item)
        elif isinstance(result, dict) and "generated_text" in result:
            generated_texts.append(result["generated_text"])

        for text in generated_texts:
            # Some models output multiple questions separated by <sep>
            parts = re.split(r"<sep>|<SEP>|\n", text)
            for part in parts:
                q_text = part.strip().rstrip("?").strip() + "?"
                q_text = re.sub(r"\s+", " ", q_text)
                if len(q_text) > 10 and q_text != "?":
                    questions.append({
                        "question": q_text,
                        "answer": answer_span or self._extract_answer(sentence),
                        "source_sentence": sentence,
                        "question_type": self._classify_question_type(q_text),
                    })

        return questions

    # ------------------------------------------------------------------
    # Generate from ranked sentences in batch
    # ------------------------------------------------------------------

    @timed
    def generate_from_ranked_sentences(
        self,
        ranked_sentences: list[str],
        concepts: list[str],
        max_questions_per_sentence: int = 2,
    ) -> list[dict[str, str]]:
        """
        Generate questions from a list of ranked sentences.

        For each sentence, attempts to highlight concept spans and generate
        questions targeting those concepts.
        """
        all_questions: list[dict[str, str]] = []

        for sentence in ranked_sentences:
            # Find concepts present in this sentence
            sentence_concepts = [
                c for c in concepts
                if c.lower() in sentence.lower() and len(c) > 2
            ]

            if sentence_concepts:
                # Generate questions highlighting each concept (up to limit)
                for concept in sentence_concepts[:max_questions_per_sentence]:
                    questions = self.generate_questions(
                        sentence=sentence,
                        answer_span=concept,
                    )
                    all_questions.extend(questions)
            else:
                # Generate without specific answer span
                questions = self.generate_questions(sentence=sentence)
                all_questions.extend(questions)

            # Rate-limit courtesy pause
            time.sleep(0.5)

        logger.info("HF generator produced %d questions", len(all_questions))
        return all_questions

    # ------------------------------------------------------------------
    # Rule-based fallback
    # ------------------------------------------------------------------

    def _generate_rule_based(
        self, sentence: str, answer_span: str = ""
    ) -> list[dict[str, str]]:
        """Generate simple rule-based questions as fallback."""
        questions: list[dict[str, str]] = []

        # Try to identify a question pattern
        if answer_span:
            # WH question
            q_text = self._create_wh_question(sentence, answer_span)
            if q_text:
                questions.append({
                    "question": q_text,
                    "answer": answer_span,
                    "source_sentence": sentence,
                    "question_type": "wh",
                })

            # Short answer
            q_text2 = f"What can you tell about {answer_span} based on the given context?"
            questions.append({
                "question": q_text2,
                "answer": answer_span,
                "source_sentence": sentence,
                "question_type": "short_answer",
            })
        else:
            # Generic comprehension question
            short = sentence[:80].rstrip() + "..." if len(sentence) > 80 else sentence
            questions.append({
                "question": f"What is the main idea conveyed in: \"{short}\"?",
                "answer": sentence,
                "source_sentence": sentence,
                "question_type": "short_answer",
            })

        return questions

    def _create_wh_question(self, sentence: str, answer: str) -> str | None:
        """Create a WH question by replacing the answer span."""
        import spacy
        try:
            nlp = spacy.load("en_core_web_md")
        except Exception:
            return f"What is {answer}?"

        doc = nlp(answer)
        # Determine WH word based on entity type
        wh_word = "What"
        for ent in doc.ents:
            if ent.label_ in ("PERSON", "ORG"):
                wh_word = "Who"
            elif ent.label_ in ("DATE", "TIME"):
                wh_word = "When"
            elif ent.label_ in ("GPE", "LOC", "FAC"):
                wh_word = "Where"
            elif ent.label_ in ("CARDINAL", "QUANTITY", "PERCENT"):
                wh_word = "How many"
            break

        # Simple replacement
        question = sentence.replace(answer, f"______")
        question = f"{wh_word} {question.lower().rstrip('.')}?"
        return question

    @staticmethod
    def _extract_answer(sentence: str) -> str:
        """Extract a likely answer span from a sentence (first noun phrase)."""
        try:
            import spacy
            nlp = spacy.load("en_core_web_md")
            doc = nlp(sentence)
            for chunk in doc.noun_chunks:
                if len(chunk.text.split()) >= 1:
                    return chunk.text
        except Exception:
            pass
        # Fallback: first few words
        words = sentence.split()
        return " ".join(words[:4]) if len(words) >= 4 else sentence

    @staticmethod
    def _classify_question_type(question: str) -> str:
        """Classify a generated question as 'wh' or 'short_answer'."""
        q_lower = question.lower().strip()
        wh_words = ["what", "who", "where", "when", "which", "why", "how"]
        for w in wh_words:
            if q_lower.startswith(w):
                return "wh"
        return "short_answer"
