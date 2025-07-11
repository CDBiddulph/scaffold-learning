#!/usr/bin/env python3
"""CLI for running scaffold learning experiments."""

import argparse
import json
from pathlib import Path
from typing import Callable, Dict, List

from scaffold_learning.core.data_structures import DatasetExample
from scaffold_learning.core.experiment_runner import ExperimentRunner
from scaffold_learning.core.llm_interfaces import LLMFactory

from scaffold_learning.domains.crosswords.score.score import score as score_crosswords


def load_dataset(dataset_path: Path) -> List[DatasetExample]:
    """Load dataset from JSONL file.

    Args:
        dataset_path: Path to JSONL file containing dataset examples

    Returns:
        List of DatasetExample objects
    """
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

    print(f"Loaded {len(examples)} examples from {dataset_path}")
    return examples


def create_scoring_function(domain: str) -> Callable[[str, Dict], float]:
    """Create a scoring function for the specified domain.

    Args:
        domain: Domain name (e.g., 'crosswords')

    Returns:
        Scoring function that takes (expected, scoring_data) and returns 0-1 score
    """
    if domain in ["crosswords", "crosswords_strict"]:
        return lambda expected, scoring_data: score_crosswords(
            expected, scoring_data.get("solution", ""), mode="strict"
        )
    elif domain == "crosswords_lenient":
        return lambda expected, scoring_data: score_crosswords(
            expected, scoring_data.get("solution", ""), mode="lenient"
        )
    else:
        raise ValueError(f"Error: Unknown domain '{domain}'")


def get_scoring_function_code(domain: str) -> str:
    """Get the scoring function code content for the specified domain.

    Args:
        domain: Domain name (e.g., 'crosswords')

    Returns:
        Content of the scoring function file
    """
    if domain == "crosswords_lenient":
        path = "src/scaffold_learning/domains/crosswords/score/score_lenient.py"
    elif domain in ["crosswords", "crosswords_strict"]:
        path = "src/scaffold_learning/domains/crosswords/score/score_strict.py"
    else:
        raise ValueError(f"Scoring function content not supported for domain: {domain}")

    with open(path, "r") as f:
        return f.read()


def main():
    parser = argparse.ArgumentParser(
        description="Run scaffold learning experiments",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Required arguments
    parser.add_argument("experiment_name", help="Name for this experiment run")
    parser.add_argument(
        "data_dir",
        type=Path,
        help="Directory containing train.jsonl and valid.jsonl files",
    )

    # Domain and model
    parser.add_argument(
        "--domain", default="crosswords", help="Problem domain for scoring function"
    )
    parser.add_argument(
        "--scaffolder-model",
        default="haiku",
        help="Model to use for scaffold generation/evolution",
    )
    parser.add_argument(
        "--executor-model",
        default="haiku",
        help="Model to use for executing scaffolds",
    )

    # Experiment parameters
    parser.add_argument(
        "--num-iterations",
        type=int,
        default=3,
        help="Number of evolution iterations to run",
    )
    parser.add_argument(
        "--scaffolds-per-iter",
        type=int,
        default=2,
        help="Number of top scaffolds to evolve each iteration",
    )
    parser.add_argument(
        "--initial-scaffolds",
        type=int,
        default=5,
        help="Number of initial scaffolds to create",
    )
    parser.add_argument(
        "--num-validation-examples",
        type=int,
        default=10,
        help="Number of validation examples to use for scoring",
    )
    parser.add_argument(
        "--num-training-examples",
        type=int,
        default=1,
        help="Number of training examples to show when evolving scaffolds",
    )
    parser.add_argument(
        "--show-scoring-function",
        action="store_true",
        help="Show a Python file with the scoring function in the prompt",
    )

    # Output
    parser.add_argument(
        "--base-dir",
        type=Path,
        default=Path("experiments"),
        help="Base directory for experiment outputs",
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.data_dir.exists() or not args.data_dir.is_dir():
        raise FileNotFoundError(f"Data directory not found: {args.data_dir}")

    if args.scaffolds_per_iter > args.initial_scaffolds:
        raise ValueError("scaffolds-per-iter cannot be greater than initial-scaffolds")

    # Load datasets
    print("Loading datasets...")
    training_data = load_dataset(args.data_dir / "train.jsonl")
    validation_data = load_dataset(args.data_dir / "valid.jsonl")

    # Create scoring function and get a code representation of it
    print(f"Setting up {args.domain} domain...")
    scoring_fn = create_scoring_function(args.domain)
    scoring_fn_code = (
        get_scoring_function_code(args.domain) if args.show_scoring_function else None
    )

    # Create scaffolder LLM
    print(f"Initializing scaffolder model: {args.scaffolder_model}")
    scaffolder_llm = LLMFactory.create_llm(args.scaffolder_model)

    # Create experiment runner
    print("Initializing experiment runner...")
    runner = ExperimentRunner(
        experiment_name=args.experiment_name,
        training_data=training_data,
        validation_data=validation_data,
        scoring_fn=scoring_fn,
        scaffolder_llm=scaffolder_llm,
        num_iterations=args.num_iterations,
        scaffolds_per_iter=args.scaffolds_per_iter,
        initial_scaffolds=args.initial_scaffolds,
        num_validation_examples=args.num_validation_examples,
        num_training_examples=args.num_training_examples,
        base_dir=args.base_dir,
        executor_model=args.executor_model,
        scoring_fn_code=scoring_fn_code,
    )

    # Run experiment
    print("Starting experiment...")
    best_scaffold_path, best_score = runner.run()

    # Print results
    print("\n" + "=" * 50)
    print("EXPERIMENT COMPLETE")
    print("=" * 50)
    print(f"Best scaffold path: {best_scaffold_path}")
    print(f"Best score: {best_score:.3f}")
    print("=" * 50)


if __name__ == "__main__":
    main()
