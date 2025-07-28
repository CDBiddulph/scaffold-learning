"""Utilities for loading and working with datasets."""

import random
import json
from pathlib import Path
from typing import List, Dict, Collection

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
    splits: Collection[str],
) -> Dict[str, List[DatasetExample]]:
    """Load datasets from JSONL files.

    Args:
        dataset_path: Path to directory containing train.jsonl, valid.jsonl, and test.jsonl files

    Returns:
        Dictionary of split name to list of examples
    """
    return {split: _load_dataset(dataset_path / f"{split}.jsonl") for split in splits}


class ExampleSampler:
    def __init__(self, seed: int, dataset: List[DatasetExample], allow_resample: bool):
        self._random_gen = random.Random(seed)
        self._dataset = dataset
        # Sort by id to make sampling deterministic
        self._dataset.sort(key=lambda x: x.id)
        self._allow_resample = allow_resample
        self._refresh_remaining_data()

    def _refresh_remaining_data(self) -> None:
        self._remaining_data = list(self._dataset)
        self._random_gen.shuffle(self._remaining_data)

    def _yield_example(self) -> DatasetExample:
        if not self._remaining_data:
            if not self._allow_resample:
                raise ValueError("No remaining data to sample from")
            self._refresh_remaining_data()
        return self._remaining_data.pop(0)

    def sample(self, num_examples: int) -> List[DatasetExample]:
        return [self._yield_example() for _ in range(num_examples)]
