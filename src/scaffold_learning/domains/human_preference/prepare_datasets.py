#!/usr/bin/env python
"""Prepare human preference datasets by downloading Arena dataset and creating prompts."""

import argparse
import os
from pathlib import Path
from typing import List, Dict, Any

from datasets import load_dataset
from dotenv import load_dotenv

from scaffold_learning.core.dataset_utils import save_dataset_splits

# Load environment variables from .env file
load_dotenv()


def create_input_prompt(prompt: str, response_a: str, response_b: str) -> str:
    """Create an input prompt for preference prediction.

    Args:
        prompt: The original prompt
        response_a: First response
        response_b: Second response

    Returns:
        Formatted prompt string
    """
    return f"""Original prompt: {prompt}

Response A:
{response_a}

Response B:
{response_b}

Which response was preferred? Write "Answer: A" or "Answer: B"."""


def _download_preference_dataset(num_examples: int) -> List[Dict[str, Any]]:
    """Download and filter human preference dataset.

    Args:
        num_examples: Number of examples to download

    Returns:
        List of preference dictionaries
    """
    # Load Arena dataset with authentication token
    token = os.getenv("HF_TOKEN")
    dataset = load_dataset(
        "lmarena-ai/arena-human-preference-55k", split="train", token=token
    )

    # Filter for single prompts and non-ties
    valid_examples = []
    for item in dataset:
        # Skip if prompt is not a single string
        if not isinstance(item["prompt"], str):
            continue

        # Skip ties
        if item["winner_tie"] == 1:
            continue

        # Determine preference
        if item["winner_model_a"] == 1:
            preferred = "A"
        elif item["winner_model_b"] == 1:
            preferred = "B"
        else:
            # Skip if no clear winner
            continue

        example_data = {
            "id": item.get("id", f"pref_{len(valid_examples):05d}"),
            "prompt": item["prompt"],
            "response_a": item["response_a"],
            "response_b": item["response_b"],
            "preferred": preferred,
        }
        valid_examples.append(example_data)

        if len(valid_examples) >= num_examples:
            break

    if len(valid_examples) < num_examples:
        raise ValueError(
            f"Only found {len(valid_examples)} valid examples, "
            f"but {num_examples} were requested"
        )

    return valid_examples


def prepare_dataset(
    output_dir: Path, train_count: int, valid_count: int, test_count: int, seed: int
) -> None:
    """Prepare human preference dataset.

    Args:
        output_dir: Directory to save the dataset files
        train_count: Number of training examples
        valid_count: Number of validation examples
        test_count: Number of test examples
        seed: Random seed for shuffling
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    total_needed = train_count + valid_count + test_count
    print(f"Downloading {total_needed} examples from Arena Human Preference dataset...")

    # Download examples
    raw_examples = _download_preference_dataset(total_needed)

    # Convert to our JSONL format
    dataset_examples = []
    for raw_ex in raw_examples:
        input_prompt = create_input_prompt(
            raw_ex["prompt"],
            raw_ex["response_a"],
            raw_ex["response_b"],
        )

        example_data = {
            "id": raw_ex["id"],
            "input": input_prompt,
            "scoring_data": {"correct_answer": raw_ex["preferred"]},
        }
        dataset_examples.append(example_data)

    # Save the dataset splits
    split_counts = {"train": train_count, "valid": valid_count, "test": test_count}
    save_dataset_splits(dataset_examples, output_dir, split_counts, seed)


def main():
    """Download human preference data and prepare datasets."""
    parser = argparse.ArgumentParser(
        description="Prepare human preference datasets from Arena dataset"
    )
    parser.add_argument(
        "output_dir",
        help="Directory to save train.jsonl, valid.jsonl, and test.jsonl files",
    )
    parser.add_argument(
        "--num-train",
        type=int,
        required=True,
        help="Number of training examples",
    )
    parser.add_argument(
        "--num-valid",
        type=int,
        required=True,
        help="Number of validation examples",
    )
    parser.add_argument(
        "--num-test",
        type=int,
        required=True,
        help="Number of test examples",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for shuffling examples (default: 42)",
    )

    args = parser.parse_args()

    output_dir = Path(args.output_dir)

    prepare_dataset(
        output_dir, args.num_train, args.num_valid, args.num_test, args.seed
    )


if __name__ == "__main__":
    main()
