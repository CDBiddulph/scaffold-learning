#!/usr/bin/env python3
"""CLI for evaluating baseline models using prompt-only scaffolds."""

import argparse
import json
import random
import numpy as np
from datetime import datetime
from pathlib import Path

from scaffold_learning.core.dataset_utils import load_datasets, sample_examples
from scaffold_learning.core.scoring_utils import (
    create_scoring_function,
    get_scoring_function_code,
)
from scaffold_learning.core.scaffold_generation import make_prompt_only_scaffold
from scaffold_learning.core.scaffold_execution import execute_scaffold
from scaffold_learning.core.scaffold_files import save_scaffold


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate baseline models using prompt-only scaffolds"
    )

    parser.add_argument("name", help="Name for this baseline evaluation")
    parser.add_argument(
        "data_dir", type=Path, help="Directory containing train.jsonl and valid.jsonl"
    )
    parser.add_argument("--domain", default="crosswords", help="Problem domain")
    parser.add_argument("--model", help="Model to evaluate")
    parser.add_argument(
        "--num-train-examples", type=int, default=5, help="Training examples in prompt"
    )
    parser.add_argument(
        "--num-validation-examples",
        type=int,
        default=10,
        help="Validation examples to evaluate",
    )
    parser.add_argument(
        "--show-scoring-function",
        action="store_true",
        help="Include scoring function in prompt",
    )
    parser.add_argument("--seed", type=int, help="Random seed")
    parser.add_argument(
        "--thinking-budget",
        type=int,
        default=10000,
        help="Thinking budget tokens (0 to disable)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=600,
        help="Maximum execution time for each run in seconds",
    )

    return parser.parse_args()


def main():
    args = _parse_args()

    if args.seed:
        random.seed(args.seed)

    # Load datasets
    training_data, validation_data = load_datasets(args.data_dir)

    # Sample examples
    # TODO: make multiple scaffold variants with different training examples
    train_sample = sample_examples(training_data, args.num_train_examples)
    eval_sample = sample_examples(validation_data, args.num_validation_examples)

    # Create scoring function
    scoring_fn = create_scoring_function(args.domain)
    scoring_fn_code = (
        get_scoring_function_code(args.domain) if args.show_scoring_function else None
    )

    # Generate scaffold
    scaffold_result = make_prompt_only_scaffold(
        examples=train_sample,
        scoring_fn_code=scoring_fn_code,
    )

    # Save scaffold
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    scaffold_dir = Path("scaffold-baselines") / f"{args.name}-{timestamp}"
    save_scaffold(scaffold_dir, scaffold_result)

    # Evaluate
    scores = []
    execution_times = []
    for i, example in enumerate(eval_sample):
        result = execute_scaffold(
            scaffold_dir=scaffold_dir,
            log_file_path=scaffold_dir / f"eval_{i}.log",
            input_string=example.input,
            model_spec=args.model,
            timeout=args.timeout,
            console_output=False,
            thinking_budget_tokens=args.thinking_budget,
        )

        if result.error_message is None:
            expected = example.scoring_data.get("solution", str(example.scoring_data))
            score = scoring_fn(expected, {"solution": result.output})
        else:
            score = 0.0

        scores.append(score)
        execution_times.append(result.execution_time)
        print(f"{i+1}/{len(eval_sample)}: {score:.3f} ({result.execution_time:.1f}s)")

    # Save and print results
    results = {
        "mean_score": np.mean(scores),
        "std_score": np.std(scores),
        "scores": scores,
        "execution_times": execution_times,
    }

    with open(scaffold_dir / "results.json", "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nResults: {results['mean_score']:.3f} ± {results['std_score']:.3f}")
    print(f"Saved to: {scaffold_dir}")


if __name__ == "__main__":
    main()
