#!/usr/bin/env python
"""Score human preference responses by extracting answers and checking correctness."""

import argparse
import json

from ..answer_extraction import extract_answer_letter


def score(expected_preference: str, attempted_response: str) -> float:
    """Score a preference response against the expected preference.
    
    Args:
        expected_preference: The correct preference ("A" or "B")
        attempted_response: The response text containing the attempted answer
        
    Returns:
        1.0 if correct, 0.0 if incorrect or no answer extracted
    """
    # Validate expected preference
    if not expected_preference or not isinstance(expected_preference, str):
        raise ValueError("Expected preference must be a non-empty string")
    
    expected_upper = expected_preference.upper()
    if len(expected_upper) != 1 or expected_upper not in "AB":
        raise ValueError(
            f"Expected preference must be a single letter A or B, got: {expected_preference}"
        )
    
    extracted = extract_answer_letter(attempted_response, "AB")
    if extracted is None:
        return 0.0
    
    return 1.0 if extracted.upper() == expected_upper else 0.0


def _load_expected_preference(file_path: str, example_id: str) -> str:
    """Load expected preference from JSONL file for a specific example.
    
    Args:
        file_path: Path to the JSONL file
        example_id: ID of the example to find
        
    Returns:
        Expected preference string
    """
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            data = json.loads(line.strip())
            if data.get("id") == example_id:
                return data["scoring_data"]["correct_answer"]
    
    raise ValueError(f"Example '{example_id}' not found in JSONL file")


def main():
    """Command line interface."""
    parser = argparse.ArgumentParser(
        description="Score a human preference response against the expected preference",
    )
    
    parser.add_argument("expected_file", help="JSONL file with expected preferences")
    parser.add_argument("attempted_response", help="Text file with attempted response")
    parser.add_argument(
        "--example",
        "-e",
        required=True,
        help="Example ID to score",
    )
    
    args = parser.parse_args()
    
    # Load expected preference
    expected_preference = _load_expected_preference(args.expected_file, args.example)
    
    # Load attempted response
    with open(args.attempted_response, "r", encoding="utf-8") as f:
        attempted_response = f.read()
    
    # Score the response
    result = score(expected_preference, attempted_response)
    print(f"Score: {result:.1f}")


if __name__ == "__main__":
    main()