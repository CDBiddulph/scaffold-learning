#!/usr/bin/env python
"""Prepare AIME datasets by downloading from HuggingFace and splitting by year"""

import argparse
import json
import re
from pathlib import Path
from typing import List, Dict, Any

from datasets import load_dataset


def _extract_year_from_url(url: str) -> str:
    """
    Extract year from AOPS URL.

    Args:
        url: The source URL

    Returns:
        Year as string (e.g., "2022", "2023", "2024")
    """
    # Look for patterns like "AIME_2022", "AIME_2023", etc. in URL
    match = re.search(r"AIME[_\s]*(\d{4})", url, re.IGNORECASE)
    if match:
        return match.group(1)

    # Fallback: look for any 4-digit year
    match = re.search(r"(202[2-4])", url)
    if match:
        return match.group(1)

    raise ValueError(f"Unknown year: {url}")


def _download_aime_dataset() -> Dict[str, List[Dict[str, Any]]]:
    """
    Download AIME dataset from HuggingFace and organize by year.

    Returns:
        Dictionary mapping year to list of problems
    """
    # Load AIME dataset from HuggingFace
    dataset = load_dataset("AI-MO/aimo-validation-aime", split="train")

    # Organize problems by year
    problems_by_year = {"2022": [], "2023": [], "2024": []}

    for item in dataset:
        year = _extract_year_from_url(item["url"])

        problem_data = {
            "id": f"aime_{year}_{item['id']}",
            "problem": item["problem"],
            "explanation": item["explanation"],
            "answer": item["answer"],
        }

        problems_by_year[year].append(problem_data)

    return problems_by_year


def create_input_prompt(problem: str) -> str:
    """
    Create an input prompt for an AIME problem.

    Args:
        problem: The problem statement text

    Returns:
        Formatted prompt string
    """
    # Build the prompt
    prompt_parts = [
        problem,
        "",
        'Provide your final answer as an integer from 0 to 999 in the format "Answer: <number>".',
    ]

    return "\n".join(prompt_parts)


def prepare_dataset(output_dir: Path) -> None:
    """
    Prepare AIME dataset by downloading and splitting by year.
    Train=2022, Valid=2023, Test=2024

    Args:
        output_dir: Directory to save the dataset files
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Downloading AIME problems from HuggingFace...")

    # Download and organize problems by year
    problems_by_year = _download_aime_dataset()

    print(f"Found {len(problems_by_year['2022'])} problems from 2022")
    print(f"Found {len(problems_by_year['2023'])} problems from 2023")
    print(f"Found {len(problems_by_year['2024'])} problems from 2024")

    # Convert each year's problems to our JSONL format
    year_to_split = {"2022": "train", "2023": "valid", "2024": "test"}
    split_problems = {"train": [], "valid": [], "test": []}

    for year, split_name in year_to_split.items():
        for raw_p in problems_by_year[year]:
            formatted_prompt = create_input_prompt(raw_p["problem"])

            # Parse answer as integer
            try:
                answer_int = int(raw_p["answer"])
                if not 0 <= answer_int <= 999:
                    raise ValueError(f"Answer {answer_int} not in range 0-999")
            except (ValueError, TypeError) as e:
                raise ValueError(
                    f"Invalid answer format for problem {raw_p['id']}: {raw_p['answer']}"
                )

            problem_data = {
                "id": raw_p["id"],
                "input": formatted_prompt,
                "scoring_data": {
                    "correct_answer": answer_int,
                    "explanation": raw_p["solution"],
                },
            }
            split_problems[split_name].append(problem_data)

    # Save each split
    for split_name, problems in split_problems.items():
        if problems:
            output_file = output_dir / f"{split_name}.jsonl"
            with open(output_file, "w", encoding="utf-8") as f:
                for problem in problems:
                    f.write(json.dumps(problem) + "\n")
            print(f"Saved {len(problems)} {split_name} items to {output_file}")


def main():
    """Download AIME problems and prepare datasets"""
    parser = argparse.ArgumentParser(
        description="Prepare AIME datasets from HuggingFace, split by year"
    )
    parser.add_argument(
        "output_dir",
        help="Directory to save train.jsonl, valid.jsonl, and test.jsonl files",
    )

    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    prepare_dataset(output_dir)


if __name__ == "__main__":
    main()
