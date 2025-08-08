#!/usr/bin/env python
"""Prepare reward model datasets by downloading Arena dataset and extracting prompts."""

import argparse
import json
import os
from pathlib import Path
from typing import List, Dict, Any

from datasets import load_dataset
from dotenv import load_dotenv

from scaffold_learning.core.dataset_utils import save_dataset_splits

# Load environment variables from .env file
load_dotenv()


def _download_preference_dataset(num_examples: int) -> List[Dict[str, Any]]:
    """Download and filter human preference dataset for prompts.

    Args:
        num_examples: Number of examples to download

    Returns:
        List of prompt dictionaries
    """
    # Load Arena dataset with authentication token
    token = os.getenv("HF_TOKEN")
    dataset = load_dataset(
        "lmarena-ai/arena-human-preference-55k", split="train", token=token
    )

    # Extract prompts from valid examples
    valid_examples = []
    seen_prompts = set()  # Track unique prompts

    for item in dataset:
        # Parse JSON fields (they are JSON-encoded strings)
        try:
            prompt_list = json.loads(item["prompt"])
        except (json.JSONDecodeError, TypeError):
            # Skip if we can't parse the JSON
            continue

        # Skip if prompt is not a single string (we want single prompts only)
        if not isinstance(prompt_list, list) or len(prompt_list) != 1:
            continue

        prompt = prompt_list[0]

        # Skip duplicate prompts
        if prompt in seen_prompts:
            continue
        seen_prompts.add(prompt)

        example_data = {
            "id": item.get("id", f"rm_{len(valid_examples):05d}"),
            "prompt": prompt,
        }
        valid_examples.append(example_data)

        if len(valid_examples) >= num_examples:
            break

    if len(valid_examples) < num_examples:
        raise ValueError(
            f"Only found {len(valid_examples)} unique prompts, "
            f"but {num_examples} were requested"
        )

    return valid_examples


def prepare_dataset(
    output_dir: Path, train_count: int, valid_count: int, test_count: int, seed: int
) -> None:
    """Prepare reward model dataset.

    Args:
        output_dir: Directory to save the dataset files
        train_count: Number of training examples
        valid_count: Number of validation examples
        test_count: Number of test examples
        seed: Random seed for shuffling
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    total_needed = train_count + valid_count + test_count
    print(
        f"Downloading {total_needed} unique prompts from Arena Human Preference dataset..."
    )

    # Download examples
    raw_examples = _download_preference_dataset(total_needed)

    # Convert to our JSONL format
    dataset_examples = []
    for raw_ex in raw_examples:
        example_data = {
            "id": raw_ex["id"],
            "input": raw_ex["prompt"],
            "scoring_data": {},
        }
        dataset_examples.append(example_data)

    # Save the dataset splits
    split_counts = {"train": train_count, "valid": valid_count, "test": test_count}
    save_dataset_splits(dataset_examples, output_dir, split_counts, seed)


def main():
    """Download human preference data and prepare datasets for reward model."""
    parser = argparse.ArgumentParser(
        description="Prepare reward model datasets from Arena dataset prompts"
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
