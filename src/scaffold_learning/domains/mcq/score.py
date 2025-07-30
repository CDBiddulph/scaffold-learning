#!/usr/bin/env python
"""Score MCQ responses by extracting answers and checking correctness"""

import argparse
import json
from typing import Optional

from ..scoring_utils import score_letter_choice


def score(expected_answer: str, attempted_response: str) -> float:
    """
    Score an MCQ response against the expected answer.

    Args:
        expected_answer: The correct answer letter (e.g., "A")
        attempted_response: The response text containing the attempted answer

    Returns:
        1.0 if correct, 0.0 if incorrect or no answer extracted
    """
    return score_letter_choice(expected_answer, attempted_response, "ABCDE")


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
