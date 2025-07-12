"""Utilities for loading and working with datasets."""

import json
from pathlib import Path
from typing import List, Tuple
import random

from scaffold_learning.core.data_structures import DatasetExample


def _load_dataset(dataset_path: Path) -> List[DatasetExample]:
    examples = []

    with open(dataset_path, "r") as f:
        for line_num, line in enumerate(f, 1):
            data = json.loads(line.strip())

            # Extract required fields
            example_id = data.get("id", f"example_{line_num}")
            input_text = data.get("input", "")
            scoring_data = data.get("scoring_data", {})

            # TODO: make this less hacky by making solution always come from scoring_data
            # Handle crossword dataset format where solution is at top level
            if "solution" in data and "solution" not in scoring_data:
                scoring_data["solution"] = data["solution"]

            if not input_text:
                print(f"Warning: Example {example_id} has empty input, skipping")
                continue

            examples.append(
                DatasetExample(
                    id=example_id, input=input_text, scoring_data=scoring_data
                )
            )

    if not examples:
        raise ValueError(f"No valid examples found in {dataset_path}")

    return examples


def load_datasets(
    dataset_path: Path,
) -> Tuple[List[DatasetExample], List[DatasetExample]]:
    """Load train and validation datasets from JSONL files.

    Args:
        dataset_path: Path to directory containing train.jsonl and valid.jsonl files

    Returns:
        Tuple of (train_examples, valid_examples)
    """
    train_examples = _load_dataset(dataset_path / "train.jsonl")
    valid_examples = _load_dataset(dataset_path / "valid.jsonl")
    return train_examples, valid_examples


def sample_examples(
    examples: List[DatasetExample], num_examples: int
) -> List[DatasetExample]:
    """Randomly sample examples from a dataset.

    Args:
        examples: List of examples to sample from
        num_examples: Number of examples to sample

    Returns:
        List of sampled examples
    """
    if num_examples >= len(examples):
        raise ValueError(
            f"Cannot sample {num_examples} examples from {len(examples)} examples"
        )

    return random.sample(examples, num_examples)
