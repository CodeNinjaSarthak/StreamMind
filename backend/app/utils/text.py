"""Text processing utilities."""

import re
from typing import List


def clean_text(text: str) -> str:
    """Clean and normalize text.

    Args:
        text: Raw text input.

    Returns:
        Cleaned text string.
    """
    # TODO: Implement actual text cleaning
    return text.strip()


def extract_hashtags(text: str) -> List[str]:
    """Extract hashtags from text.

    Args:
        text: Text to extract hashtags from.

    Returns:
        List of hashtag strings.
    """
    # TODO: Implement actual hashtag extraction
    return []


def is_question(text: str) -> bool:
    """Check if text appears to be a question.

    Args:
        text: Text to check.

    Returns:
        True if text is a question, False otherwise.
    """
    # TODO: Implement actual question detection
    return text.strip().endswith("?")

