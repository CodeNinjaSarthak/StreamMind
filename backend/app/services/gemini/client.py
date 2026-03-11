"""Gemini AI client with retry logic and rate limiting."""

import json
import logging
import threading

import numpy as np
from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings

logger = logging.getLogger(__name__)


def vector_to_literal(vec: list) -> str:
    """Format vector for pgvector SQL queries."""
    return "[" + ",".join(str(x) for x in vec) + "]"


class GeminiClient:
    """Client for Gemini AI API calls."""

    def __init__(self):
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._semaphore = threading.Semaphore(5)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def generate_embedding(self, text: str) -> list[float]:
        """Generate 768-dimensional normalized embedding for text.

        Note: Google's embedding model requires normalization for dimensions
        other than 3072 to ensure accurate semantic similarity.
        """
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

            return normed_embedding.tolist()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def classify_question(self, text: str) -> dict:
        """Classify whether a comment is a question.

        Returns:
            dict with keys 'is_question' (bool) and 'confidence' (float 0-1).
        """
        with self._semaphore:
            prompt = (
                f'Is this a question? Return JSON only: {{"is_question": bool, "confidence": float 0-1}}\n'
                f"Comment: {text}"
            )
            response = self._client.models.generate_content(model=settings.gemini_model, contents=prompt)
            raw = response.text.strip().removeprefix("```json").removesuffix("```").strip()
            result = json.loads(raw)
            logger.debug(
                f"Classified comment: is_question={result.get('is_question')}, confidence={result.get('confidence')}"
            )
            return result

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def generate_answer(self, question: str, context: str | None) -> str:
        """Generate an answer for the given question(s).

        Args:
            question: Question text (may be multiple questions joined by newlines).
            context: RAG context to ground the answer, or None if unavailable.

        Returns:
            Answer text.
        """
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
            return response.text
