"""Shared utility for extracting answer letters from responses."""

import re
from typing import Optional


def extract_answer_letter(response: str, valid_letters: str = "ABCDE") -> Optional[str]:
    """Extract an answer letter from a response.

    Args:
        response: The response text to extract answer from
        valid_letters: String of valid letter choices (e.g., "ABCDE" or "AB")

    Returns:
        The answer letter if found and valid, None otherwise
    """
    if not response:
        return None

    # Convert valid letters to uppercase for comparison
    valid_letters = valid_letters.upper()

    # Create character class for regex patterns
    letter_class = f"[{valid_letters}]"

    # Patterns in order of priority
    patterns = [
        # Explicit answer declarations
        rf"(?:final\s+)?answer(?:\s*is)?\s*:?\s*({letter_class})\b",  # "answer: A", "final answer is A", etc.
        rf"(?:answer|choose|pick|select|option|choice|response)\s+({letter_class})\b",  # "I choose A", "pick B", etc.
        # Parenthetical formats
        rf"\(?({letter_class})\)?\s*(?:is|are)\s*(?:the\s*)?(?:correct|right)",  # "(A) is correct", "A is correct", etc.
        rf"\(({letter_class})\)",  # Just "(A)"
        rf"({letter_class})\)",  # Just "A)"
        # Punctuated answers
        rf"\b({letter_class})[.:](?:\s|$)",  # "A." or "A:" at word boundary
        # Standalone answer
        rf"^\s*({letter_class})\s*$",  # Just "A" on its own line (with optional whitespace)
    ]

    response_upper = response.upper()

    for pattern in patterns:
        matches = re.findall(pattern, response_upper, re.IGNORECASE | re.MULTILINE)
        if matches:
            # Return first match for this pattern
            answer = matches[0].upper()
            if answer in valid_letters:
                return answer

    return None
