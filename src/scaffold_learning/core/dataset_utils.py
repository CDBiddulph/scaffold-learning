"""Utilities for loading and working with datasets."""

import hashlib
import random
import json
from typing import Any
from pathlib import Path
from typing import List, Dict, Collection

from scaffold_learning.core.data_structures import DatasetExample


def _load_dataset(dataset_path: Path) -> List[DatasetExample]:
    examples = []

    with open(dataset_path, "r") as f:
        for line_num, line in enumerate(f, 1):
            data = json.loads(line.strip())

            scoring_data = data["scoring_data"]
            # Always include the input in the scoring data
            scoring_data["input"] = data["input"]

            examples.append(
                DatasetExample(
                    id=data["id"],
                    input=data["input"],
                    scoring_data=scoring_data,
                )
            )

    if not examples:
        raise ValueError(f"No examples found in {dataset_path}")

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


def get_rng(seed: Any) -> random.Random:
    """Use arbitrary data as a consistent seed for a random number generator.

    Python's hash() function is non-deterministic across runs, so we use a SHA-256 hash instead.
    """
    if not isinstance(seed, int):
        seed = int(hashlib.sha256(str(seed).encode("utf-8")).hexdigest(), 16)
    return random.Random(seed)


def save_dataset_splits(
    data: List[Dict], output_dir: Path, split_counts: Dict[str, int], seed: Any
) -> None:
    """Save data to train.jsonl, valid.jsonl, and test.jsonl files.

    Args:
        data: List of data dictionaries to save
        output_dir: Directory to save the files
        split_counts: Dictionary mapping split names to counts (e.g., {"train": 100, "valid": 20})
        seed: Random seed for shuffling, can be any type that can be converted to a meaningful string with str()
    """
    # Shuffle with deterministic seed
    rng = get_rng(seed)
    rng.shuffle(data)

    total_needed = sum(split_counts.values())
    if len(data) < total_needed:
        raise ValueError(f"Only found {len(data)} items, needed {total_needed}")

    # Split and save datasets
    start_idx = 0
    for split_name, count in split_counts.items():
        if count <= 0:
            continue

        split_data = data[start_idx : start_idx + count]
        start_idx += count

        file_path = output_dir / f"{split_name}.jsonl"
        with open(file_path, "w", encoding="utf-8") as f:
            for item in split_data:
                f.write(json.dumps(item) + "\n")

        print(f"Saved {len(split_data)} {split_name} items to {file_path}")


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
