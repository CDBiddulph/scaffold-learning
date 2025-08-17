#!/usr/bin/env python
"""Score AIME responses by extracting numerical answers and checking correctness"""

import argparse
import json
import re
from typing import Optional


def extract_numerical_answer(response: str) -> Optional[int]:
    """
    Extract a numerical answer from a response.

    Args:
        response: The response text to extract answer from

    Returns:
        The answer as an integer if found and valid (0-999), None otherwise
    """
    if not response:
        return None

    # Patterns to find the answer, in order of priority
    patterns = [
        # Explicit answer declarations
        r"(?:final\s+)?answer(?:\s*is)?\s*:?\s*(\d+)",  # "answer: 123", "final answer is 456"
        r"(?:the\s+)?answer\s+is\s+(\d+)",  # "the answer is 123"
        # Boxed answer (common in math solutions)
        r"\\boxed\{(\d+)\}",  # \boxed{123}
        # Standalone number at the end of response
        r"(?:^|\n)(\d+)\s*$",  # Just "123" on last line
    ]

    for pattern in patterns:
        matches = re.findall(pattern, response, re.IGNORECASE | re.MULTILINE)
        if matches:
            # Take the last match (most likely to be the final answer)
            try:
                answer = int(matches[-1])
                if 0 <= answer <= 999:
                    return answer
            except (ValueError, TypeError):
                continue

    return None


def score(expected_answer: int, attempted_response: str) -> float:
    """
    Score an AIME response against the expected answer.

    Args:
        expected_answer: The correct answer as an integer (0-999)
        attempted_response: The response text containing the attempted answer

    Returns:
        1.0 if correct, 0.0 if incorrect or no answer extracted
    """
    # Validate expected answer
    if not isinstance(expected_answer, int):
        raise ValueError(
            f"Expected answer must be an integer, got: {type(expected_answer)}"
        )

    if not 0 <= expected_answer <= 999:
        raise ValueError(
            f"Expected answer must be between 0 and 999, got: {expected_answer}"
        )

    # Extract answer from response
    extracted = extract_numerical_answer(attempted_response)

    if extracted is None:
        return 0.0

    return 1.0 if extracted == expected_answer else 0.0


def _load_expected_answer(file_path: str, problem_id: str) -> int:
    """
    Load expected answer from JSONL file for a specific problem.

    Args:
        file_path: Path to the JSONL file
        problem_id: ID of the problem to find

    Returns:
        Expected answer as integer
    """
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            data = json.loads(line.strip())
            if data.get("id") == problem_id:
                return data["scoring_data"]["correct_answer"]

    raise ValueError(f"Problem '{problem_id}' not found in JSONL file")


def main():
    """Command line interface"""
    parser = argparse.ArgumentParser(
        description="Score an AIME response against the expected answer",
    )

    parser.add_argument("expected_file", help="JSONL file with expected answers")
    parser.add_argument("attempted_response", help="Text file with attempted response")
    parser.add_argument(
        "--problem",
        "-p",
        required=True,
        help="Problem ID to score",
    )

    args = parser.parse_args()

    # Load expected answer
    expected_answer = _load_expected_answer(args.expected_file, args.problem)

    # Load attempted response
    with open(args.attempted_response, "r", encoding="utf-8") as f:
        attempted_response = f.read()

    # Score the response
    result = score(expected_answer, attempted_response)
    print(f"Score: {result:.1f}")


if __name__ == "__main__":
    main()
