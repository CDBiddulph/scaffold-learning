#!/usr/bin/env python
"""Prepare meta-optimize datasets by sampling from mesa-domain datasets."""

import argparse
import json
from pathlib import Path
from typing import Dict, List

from scaffold_learning.core.data_structures import DatasetExample
from scaffold_learning.core.dataset_utils import (
    ExampleSampler,
    load_datasets,
    save_dataset_splits,
)


def _create_meta_examples(
    mesa_examples: List[DatasetExample], num_mesa_examples: int, seed: int = 42
) -> List[DatasetExample]:
    """Create meta examples from mesa domain examples.

    Args:
        mesa_examples: List of mesa domain examples
        num_mesa_examples: Number of mesa examples per meta example
        seed: Random seed for sampling

    Returns:
        List of meta examples
    """
    # Use ExampleSampler to sample without replacement
    sampler = ExampleSampler(seed, mesa_examples, allow_resample=False)

    meta_examples = []
    while True:
        try:
            # Try to sample the required number of mesa examples
            batch = sampler.sample(num_mesa_examples)
        except ValueError:
            # No more complete batches available
            break

        # Create meta example ID by concatenating mesa IDs
        meta_id = "meta:" + ":".join(str(example.id) for example in batch)

        # Create meta example
        meta_input = json.dumps(
            {"scoring_data": [example.scoring_data for example in batch]}
        )
        meta_example = DatasetExample(id=meta_id, input=meta_input, scoring_data={})
        meta_examples.append(meta_example)

    return meta_examples


def prepare_dataset(
    output_dir: Path,
    mesa_domain: str,
    mesa_data_dir: Path,
    num_mesa_examples: int,
    seed: int = 42,
) -> None:
    """Prepare meta-optimize dataset.

    Args:
        output_dir: Directory to save meta-optimize datasets
        mesa_domain: Name of the mesa domain (for logging)
        mesa_data_dir: Directory containing mesa domain data
        num_mesa_examples: Number of mesa examples per meta example
        seed: Random seed for sampling
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading mesa domain datasets from {mesa_data_dir}...")
    mesa_datasets = load_datasets(mesa_data_dir)
    print(f"Found splits: {list(mesa_datasets.keys())}")
    for split_name, examples in mesa_datasets.items():
        print(f"  {split_name}: {len(examples)} examples")

    # Create meta examples from each split separately
    print(f"Creating meta examples with {num_mesa_examples} mesa examples each...")
    all_meta_examples = []
    split_counts = {}

    for split_name, mesa_examples in mesa_datasets.items():
        meta_examples = _create_meta_examples(mesa_examples, num_mesa_examples, seed)
        print(f"Created {len(meta_examples)} {split_name} meta examples")

        if meta_examples:
            split_counts[split_name] = len(meta_examples)
            # Convert to dictionaries for save_dataset_splits
            all_meta_examples.extend(
                [
                    {"id": me.id, "input": me.input, "scoring_data": me.scoring_data}
                    for me in meta_examples
                ]
            )

    if not all_meta_examples:
        raise ValueError(
            f"No meta examples could be created with {num_mesa_examples} mesa examples per batch"
        )

    print(f"Total meta examples created: {len(all_meta_examples)}")
    save_dataset_splits(all_meta_examples, output_dir, split_counts, seed)


def main():
    """Prepare meta-optimize datasets from mesa domain datasets."""
    parser = argparse.ArgumentParser(
        description="Prepare meta-optimize datasets from mesa domain datasets"
    )
    parser.add_argument(
        "output_dir",
        help="Directory to save train.jsonl and valid.jsonl files",
    )
    parser.add_argument(
        "--mesa-domain",
        required=True,
        help="Mesa domain name (for logging)",
    )
    parser.add_argument(
        "--mesa-data-dir",
        type=Path,
        required=True,
        help="Directory containing mesa domain train.jsonl and valid.jsonl",
    )
    parser.add_argument(
        "--num-mesa-examples",
        type=int,
        required=True,
        help="Number of mesa examples per meta example",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for sampling (default: 42)",
    )

    args = parser.parse_args()
    output_dir = Path(args.output_dir)

    prepare_dataset(
        output_dir=output_dir,
        mesa_domain=args.mesa_domain,
        mesa_data_dir=args.mesa_data_dir,
        num_mesa_examples=args.num_mesa_examples,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()
