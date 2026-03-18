"""Content moderation service using Gemini AI."""

import json
import logging
from typing import Optional

from app.core.config import settings
from app.services.gemini.client import GeminiClient
from google.genai import types

logger = logging.getLogger(__name__)

MODERATION_SYSTEM_INSTRUCTION = (
    "You are a content moderator for an educational platform where students ask "
    "questions to teachers during live YouTube sessions. "
    "Your job is to identify content that is inappropriate for an academic setting."
)

COMMENT_MODERATION_SCHEMA = {
    "type": "object",
    "properties": {
        "approved": {"type": "boolean"},
        "reason": {"type": "string"},
        "category": {
            "type": "string",
            "enum": ["safe", "spam", "offensive", "harmful", "irrelevant"],
        },
    },
    "required": ["approved", "reason", "category"],
}

COMMENT_MODERATION_PROMPT = """Analyze this student comment from a live educational stream.

Comment: "{text}"

Approve if: genuine academic question or statement, non-English content, minor typos, informal language.
Reject if: profanity, personal attacks, spam or promotional content, self-harm, explicit content.

Respond only with JSON."""

ANSWER_MODERATION_PROMPT = """Analyze this AI-generated answer that will be posted publicly to YouTube on behalf of a teacher.

Answer: "{text}"

Approve if: factual academic content, clear explanation, appropriate tone.
Reject if: harmful advice, offensive language, factual content that could cause harm if wrong.

Respond only with JSON."""


class ModerationService:
    """Service for content moderation using Gemini AI."""

    def __init__(self):
        self._gemini = GeminiClient()

    def moderate_comment(self, text: str) -> tuple[bool, Optional[str]]:
        """Moderate a student comment for inappropriate content.

        Returns:
            Tuple of (is_safe, reason_if_unsafe).
            On any Gemini failure, approves by default to avoid blocking the pipeline.
        """
        try:
            prompt = COMMENT_MODERATION_PROMPT.format(text=text)
            response = self._gemini._client.models.generate_content(
                model=settings.gemini_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=MODERATION_SYSTEM_INSTRUCTION,
                    response_mime_type="application/json",
                    response_schema=COMMENT_MODERATION_SCHEMA,
                ),
            )
            result = json.loads(response.text)
            approved = result.get("approved", True)
            reason = result.get("reason") if not approved else None
            category = result.get("category", "safe")
            logger.info(
                "Comment moderation result",
                extra={"approved": approved, "category": category, "reason": reason},
            )
            return (approved, reason)
        except Exception as e:
            logger.error(f"Moderation failed for comment, approving by default: {e}")
            return (True, None)

    def moderate_answer(self, text: str) -> tuple[bool, Optional[str]]:
        """Moderate an AI-generated answer before it is posted to YouTube.

        Returns:
            Tuple of (is_safe, reason_if_unsafe).
            On any Gemini failure, approves by default to avoid blocking the pipeline.
        """
        try:
            prompt = ANSWER_MODERATION_PROMPT.format(text=text)
            response = self._gemini._client.models.generate_content(
                model=settings.gemini_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=MODERATION_SYSTEM_INSTRUCTION,
                    response_mime_type="application/json",
                    response_schema=COMMENT_MODERATION_SCHEMA,
                ),
            )
            result = json.loads(response.text)
            approved = result.get("approved", True)
            reason = result.get("reason") if not approved else None
            category = result.get("category", "safe")
            logger.info(
                "Answer moderation result",
                extra={"approved": approved, "category": category, "reason": reason},
            )
            return (approved, reason)
        except Exception as e:
            logger.error(f"Moderation failed for answer, approving by default: {e}")
            return (True, None)
