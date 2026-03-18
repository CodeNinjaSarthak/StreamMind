"""Gemini AI client with retry logic and rate limiting."""

import json
import logging
import threading

import numpy as np
from app.core.config import settings
from app.services.gemini.circuit_breaker import (
    CircuitOpenError,
    GeminiCircuitBreaker,
)
from google import genai
from google.genai import types
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)


def vector_to_literal(vec: list) -> str:
    """Format vector for pgvector SQL queries."""
    return "[" + ",".join(str(x) for x in vec) + "]"


class GeminiClient:
    """Client for Gemini AI API calls."""

    def __init__(self):
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._semaphore = threading.Semaphore(5)
        self._circuit_breaker = GeminiCircuitBreaker()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def generate_embedding(self, text: str) -> list[float]:
        """Generate 768-dimensional normalized embedding for text.

        Note: Google's embedding model requires normalization for dimensions
        other than 3072 to ensure accurate semantic similarity.
        """
        self._circuit_breaker.ensure_closed()
        try:
            with self._semaphore:
                result = self._client.models.embed_content(
                    model=settings.gemini_embedding_model,
                    contents=text,
                    config=types.EmbedContentConfig(output_dimensionality=768),
                )
                # Get embedding values
                embedding_values = result.embeddings[0].values

                # Normalize (required for 768-dim per Google docs)
                embedding_np = np.array(embedding_values)
                normed_embedding = embedding_np / np.linalg.norm(embedding_np)

                self._circuit_breaker.record_success()
                return normed_embedding.tolist()
        except CircuitOpenError:
            raise
        except Exception:
            self._circuit_breaker.record_failure()
            raise

    CLASSIFICATION_SYSTEM_INSTRUCTION = (
        "You are a Teaching Assistant for a Live Stream. Your job is to identify "
        '"Student Doubts." A student doubt is any inquiry, confusion, or request '
        "for clarification. Classify as a question if the student is seeking an "
        "answer, even if they use informal language or omit question marks."
    )

    CLASSIFICATION_FEW_SHOT = (
        "Examples:\n"
        'Comment: "I dont get the list part" -> {"is_question": true, "confidence": 0.92}\n'
        'Comment: "Wait, why is that true?" -> {"is_question": true, "confidence": 0.97}\n'
        'Comment: "Hello from London" -> {"is_question": false, "confidence": 0.95}\n'
        'Comment: "Can you repeat the last step?" -> {"is_question": true, "confidence": 0.96}\n'
    )

    CLASSIFICATION_RESPONSE_SCHEMA = {
        "type": "object",
        "properties": {
            "is_question": {"type": "boolean"},
            "confidence": {"type": "number"},
        },
        "required": ["is_question", "confidence"],
    }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def classify_question(self, text: str) -> dict:
        """Classify whether a comment is a question.

        Returns:
            dict with keys 'is_question' (bool) and 'confidence' (float 0-1).
        """
        self._circuit_breaker.ensure_closed()
        try:
            with self._semaphore:
                prompt = f"{self.CLASSIFICATION_FEW_SHOT}\nComment: {text}"
                response = self._client.models.generate_content(
                    model=settings.gemini_model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=self.CLASSIFICATION_SYSTEM_INSTRUCTION,
                        response_mime_type="application/json",
                        response_schema=self.CLASSIFICATION_RESPONSE_SCHEMA,
                    ),
                )
                result = json.loads(response.text)
                logger.debug(
                    f"Classified comment: is_question={result.get('is_question')}, "
                    f"confidence={result.get('confidence')}"
                )
                self._circuit_breaker.record_success()
                return result
        except CircuitOpenError:
            raise
        except Exception:
            self._circuit_breaker.record_failure()
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def generate_answer(self, question: str, context: str | None) -> str:
        """Generate an answer for the given question(s).

        Args:
            question: Question text (may be multiple questions joined by newlines).
            context: RAG context to ground the answer, or None if unavailable.

        Returns:
            Answer text.
        """
        self._circuit_breaker.ensure_closed()
        try:
            with self._semaphore:
                if context:
                    prompt = (
                        f"You are a teaching assistant answering student questions during a live class.\n"
                        f"Answer concisely and clearly using only the provided context.\n\n"
                        f"Context:\n{context}\n\n"
                        f"Question(s):\n{question}"
                    )
                else:
                    prompt = (
                        f"You are a teaching assistant answering student questions during a live class.\n"
                        f"No teacher-uploaded context is available. Answer concisely and clearly "
                        f"using your general knowledge.\n\n"
                        f"Question(s):\n{question}"
                    )
                response = self._client.models.generate_content(model=settings.gemini_model, contents=prompt)
                logger.debug("Answer generated successfully")
                self._circuit_breaker.record_success()
                return response.text
        except CircuitOpenError:
            raise
        except Exception:
            self._circuit_breaker.record_failure()
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def summarize_cluster(self, questions: list[str]) -> str:
        """Summarize a cluster of questions in 8 words or less."""
        self._circuit_breaker.ensure_closed()
        try:
            with self._semaphore:
                joined = "\n".join(f"- {q}" for q in questions)
                prompt = (
                    "Summarize what these questions are asking in 8 words or less. "
                    "Return only the summary, no punctuation.\n\n"
                    f"{joined}"
                )
                response = self._client.models.generate_content(
                    model=settings.gemini_model,
                    contents=prompt,
                    config=types.GenerateContentConfig(max_output_tokens=20),
                )
                self._circuit_breaker.record_success()
                return response.text.strip()
        except CircuitOpenError:
            raise
        except Exception:
            self._circuit_breaker.record_failure()
            raise
