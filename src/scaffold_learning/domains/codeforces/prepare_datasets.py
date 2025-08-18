#!/usr/bin/env python
"""Prepare CodeForces datasets by downloading from HuggingFace and filtering for Python problems"""

import argparse
import json
import logging
from pathlib import Path
from typing import List, Dict, Any

from datasets import load_dataset
from dotenv import load_dotenv

from scaffold_learning.core.dataset_utils import save_dataset_splits
from scaffold_learning.core.xml_utils import dict_to_xml

# Load environment variables from .env file
load_dotenv()


def _format_problem(item: Dict[str, Any], index: int) -> Dict[str, Any]:
    """
    Format a single problem into our expected format.

    Args:
        item: Raw problem from dataset
        index: Problem index for ID generation

    Returns:
        Formatted problem dictionary
    """
    # Extract fields with defaults
    problem_description = item["description"]
    input_format = item["input_format"]
    output_format = item["output_format"]
    examples = item["examples"]
    time_limit = item.get("time_limit", 2.0)  # Default 2 seconds
    memory_limit = item.get("memory_limit", 256.0)  # Default 256 MB

    # Format examples
    examples_text = ""
    if examples:
        examples_text = "\n\n" + dict_to_xml({"example": examples}, "examples")

    # Create the input prompt
    input_prompt = f"""Problem: {item['title']}

{problem_description}

Input Format:
{input_format}

Output Format:
{output_format}

Time Limit: {time_limit} seconds
Memory Limit: {memory_limit} MB{examples_text}

Write a Python solution for this problem."""

    # Prepare scoring data with official test cases
    scoring_data = {
        "held_out_tests": item["official_tests"],
        "time_limit": time_limit,
        "memory_limit": memory_limit,
    }

    return {
        "id": f"codeforces_{index:06d}",
        "input": input_prompt,
        "scoring_data": scoring_data,
    }


def _is_valid_problem(item: Dict[str, Any]) -> bool:
    """
    Check if a problem meets our criteria.

    Args:
        item: Raw problem from dataset

    Returns:
        True if problem is valid for our use
    """
    # Skip non-executable problems
    if not item.get("executable", True):
        return False

    # Only include problems that have official test cases
    if not item.get("official_tests"):
        return False

    # Skip C++ problems - we only want Python
    tags = item.get("tags", [])
    if any("c++" in str(tag).lower() for tag in tags):
        return False

    return True


def _download_codeforces_dataset(total_needed: int) -> List[Dict[str, Any]]:
    """
    Download and filter CodeForces dataset from HuggingFace.

    Args:
        total_needed: Number of valid problems needed

    Returns:
        List of problem dictionaries
    """
    logging.info("Loading CodeForces dataset from HuggingFace...")

    # Load dataset - using the default subset
    dataset = load_dataset("open-r1/codeforces", split="train")

    logging.info(f"Searching for {total_needed} suitable Python problems...")

    problems = []
    problems_checked = 0

    for item in dataset:
        problems_checked += 1

        # Check if problem is valid
        if not _is_valid_problem(item):
            continue

        # Format and add the problem
        problem = _format_problem(item, len(problems))
        problems.append(problem)

        # Log progress occasionally
        if len(problems) % 100 == 0:
            logging.info(
                f"Found {len(problems)} valid problems after checking {problems_checked}..."
            )

        # Stop once we have enough
        if len(problems) >= total_needed:
            logging.info(
                f"Found {len(problems)} valid problems after checking {problems_checked} total"
            )
            break
    else:
        # We went through the entire dataset
        logging.warning(
            f"Only found {len(problems)} valid problems after checking entire dataset ({problems_checked} total)"
        )

    return problems


def prepare_dataset(
    output_dir: Path,
    train_count: int,
    valid_count: int,
    test_count: int,
    seed: int,
) -> None:
    """
    Prepare CodeForces dataset by downloading and filtering problems.

    Args:
        output_dir: Directory to save the dataset files
        train_count: Number of training problems
        valid_count: Number of validation problems
        test_count: Number of test problems
        seed: Random seed for shuffling
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    total_needed = train_count + valid_count + test_count
    print(f"Need {total_needed} problems total")

    # Download exactly as many valid problems as needed
    problems = _download_codeforces_dataset(total_needed)

    if len(problems) < total_needed:
        raise ValueError(
            f"Only found {len(problems)} suitable problems in entire dataset, but need {total_needed}. "
            f"Consider reducing split sizes."
        )

    print(f"Found exactly {len(problems)} valid problems")

    # Save the dataset splits
    split_counts = {"train": train_count, "valid": valid_count, "test": test_count}
    save_dataset_splits(problems, output_dir, split_counts, seed)


def main():
    """Download CodeForces problems and prepare datasets"""
    parser = argparse.ArgumentParser(
        description="Prepare CodeForces datasets from HuggingFace"
    )
    parser.add_argument(
        "output_dir",
        help="Directory to save train.jsonl, valid.jsonl, and test.jsonl files",
    )
    parser.add_argument(
        "--num-train",
        type=int,
        required=True,
        help="Number of training problems",
    )
    parser.add_argument(
        "--num-valid",
        type=int,
        required=True,
        help="Number of validation problems",
    )
    parser.add_argument(
        "--num-test",
        type=int,
        required=True,
        help="Number of test problems",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for shuffling problems (default: 42)",
    )

    args = parser.parse_args()

    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    output_dir = Path(args.output_dir)

    prepare_dataset(
        output_dir,
        args.num_train,
        args.num_valid,
        args.num_test,
        args.seed,
    )


if __name__ == "__main__":
    main()
