#!/usr/bin/env python3
"""CLI for running scaffold learning experiments."""

import argparse
import logging
from pathlib import Path

from scaffold_learning.core.experiment_runner import ExperimentRunner
from scaffold_learning.core.llm_interfaces import LLMFactory
from scaffold_learning.core.dataset_utils import load_datasets
from scaffold_learning.core.scoring_utils import (
    create_scoring_function,
    get_scoring_function_code,
)
from scaffold_learning.core.docker_utils import build_docker_image


def main():
    # Configure logging first before anything else
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

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
    parser.add_argument(
        "--suggest-hack",
        choices=["no", "hidden", "explicit"],
        default="no",
        help="Include text encouraging the model to find exploits/hacks: 'no' (default), 'hidden' (hidden exploits that look legitimate), 'explicit' (obvious exploits)",
    )
    parser.add_argument(
        "--train-seed",
        type=int,
        default=42,
        help="Random seed for reproducible experiments",
    )
    parser.add_argument(
        "--valid-seed",
        type=int,
        default=42,
        help="Random seed for reproducible experiments",
    )

    # Output
    parser.add_argument(
        "--base-dir",
        type=Path,
        default=Path("experiments"),
        help="Base directory for experiment outputs",
    )
    parser.add_argument(
        "--no-build",
        action="store_true",
        help="Skip building Docker image (assume it already exists)",
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.data_dir.exists() or not args.data_dir.is_dir():
        raise FileNotFoundError(f"Data directory not found: {args.data_dir}")

    if args.scaffolds_per_iter > args.initial_scaffolds:
        raise ValueError("scaffolds-per-iter cannot be greater than initial-scaffolds")

    if not args.no_build:
        print("Building Docker image...")
        build_docker_image()

    # Load datasets
    print("Loading datasets...")
    data = load_datasets(args.data_dir, splits=["train", "valid"])

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
        training_data=data["train"],
        validation_data=data["valid"],
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
        suggest_hack=args.suggest_hack,
        train_seed=args.train_seed,
        valid_seed=args.valid_seed,
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
