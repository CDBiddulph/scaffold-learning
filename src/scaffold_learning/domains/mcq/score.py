#!/usr/bin/env python
"""Score MCQ responses by extracting answers and checking correctness"""

import argparse
import json
import re
from typing import Optional


def _extract_answer(response: str) -> Optional[str]:
    """
    Extract the answer letter from an MCQ response.

    Args:
        response: The response text to extract answer from

    Returns:
        The answer letter (A-Z) if found, None otherwise
    """
    if not response:
        return None

    # Patterns in order of priority
    patterns = [
        # Explicit answer declarations
        r"(?:final\s+)?answer(?:\s*is)?\s*:?\s*([A-E])\b",  # "answer: A", "final answer is A", etc.
        r"(?:answer|choose|pick|select|option|choice)\s+([A-E])\b",  # "I choose A", "pick B", etc.
        # Parenthetical formats
        r"\(?([A-E])\)?\s*(?:is|are)\s*(?:the\s*)?(?:correct|right)",  # "(A) is correct", "A is correct", etc.
        r"\(([A-E])\)",  # Just "(A)"
        r"([A-E])\)",  # Just "A)"
        # Punctuated answers
        r"\b([A-E])[.:](?:\s|$)",  # "A." or "A:" at word boundary
        # Standalone answer
        r"^([A-E])$",  # Just "A" on its own line
    ]

    response_upper = response.upper()

    for pattern in patterns:
        matches = re.findall(pattern, response_upper, re.IGNORECASE)
        if matches:
            # Return first match for this pattern
            answer = matches[0].upper()
            if answer in "ABCDE":
                return answer

    return None


def score(expected_answer: str, attempted_response: str) -> float:
    """
    Score an MCQ response against the expected answer.

    Args:
        expected_answer: The correct answer letter (e.g., "A")
        attempted_response: The response text containing the attempted answer

    Returns:
        1.0 if correct, 0.0 if incorrect or no answer extracted
    """
    # Validate expected answer
    if not expected_answer or not isinstance(expected_answer, str):
        raise ValueError("Expected answer must be a non-empty string")

    expected_upper = expected_answer.upper()
    if len(expected_upper) != 1 or expected_upper not in "ABCDE":
        raise ValueError(
            f"Expected answer must be a single letter A-E, got: {expected_answer}"
        )

    extracted = _extract_answer(attempted_response)
    if extracted is None:
        return 0.0

    return 1.0 if extracted.upper() == expected_upper else 0.0


def _load_expected_answer(file_path: str, question_id: str) -> str:
    """
    Load expected answer from JSONL file for a specific question.

    Args:
        file_path: Path to the JSONL file
        question_id: ID of the question to find

    Returns:
        Expected answer string
    """
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            data = json.loads(line.strip())
            if data.get("id") == question_id:
                return data["scoring_data"]["correct_answer"]

    raise ValueError(f"Question '{question_id}' not found in JSONL file")


def main():
    """Command line interface"""
    parser = argparse.ArgumentParser(
        description="Score an MCQ response against the expected answer",
    )

    parser.add_argument("expected_file", help="JSONL file with expected answers")
    parser.add_argument("attempted_response", help="Text file with attempted response")
    parser.add_argument(
        "--question",
        "-q",
        required=True,
        help="Question ID to score",
    )

    args = parser.parse_args()

    # Load expected answer
    expected_answer = _load_expected_answer(args.expected_file, args.question)

    # Load attempted response
    with open(args.attempted_response, "r", encoding="utf-8") as f:
        attempted_response = f.read()

    # Score the response
    result = score(expected_answer, attempted_response)
    print(f"Score: {result:.1f}")


if __name__ == "__main__":
    main()
