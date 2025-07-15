#!/usr/bin/env python3
"""
Unified CLI for scaffold creation and execution.

Combines functionality from generate_scaffold.py, evaluate_baseline.py, and run_scaffold.py
into a single command with make and run subcommands.
"""

import argparse
import json
import numpy as np
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from scaffold_learning.core.dataset_utils import ExampleSampler, load_datasets
from scaffold_learning.core.scoring_utils import (
    create_scoring_function,
    get_scoring_function_code,
)
from scaffold_learning.core.scaffold_generation import (
    make_prompt_only_scaffold,
    generate_scaffold,
)
from scaffold_learning.core.scaffold_execution import execute_scaffold
from scaffold_learning.core.scaffold_files import save_scaffold
from scaffold_learning.core.docker_utils import build_docker_image
from scaffold_learning.core.llm_interfaces import LLMFactory


@dataclass
class ScaffoldConfig:
    """Configuration for scaffold operations."""

    # Subcommand flags
    do_make: bool = False
    do_run: bool = False

    # Make arguments
    name: Optional[str] = None
    scaffolder_model: Optional[str] = None
    task: Optional[str] = None
    baseline: bool = False
    data_dir: Optional[Path] = None
    num_train_examples: Optional[int] = None
    train_seed: Optional[int] = None
    show_scoring_function: bool = False
    suggest_hack: bool = False

    # Run arguments
    base_dir: Optional[Path] = None
    executor_model: Optional[str] = None
    input_string: Optional[str] = None
    input_file: Optional[Path] = None
    num_test_examples: Optional[int] = None
    test_seed: Optional[int] = None
    domain: Optional[str] = None
    timeout: Optional[int] = None
    no_build: bool = False
    thinking_budget: int = 0


def parse_args(argv: Optional[List[str]] = None) -> ScaffoldConfig:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Unified scaffold creation and execution tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate scaffold from examples and evaluate
  scaffold make run --data-dir data/crosswords --scaffolder-model gpt-4o \\
    --name solver --executor-model haiku --num-train-examples 5 \\
    --num-test-examples 10 --domain crosswords

  # Create baseline and evaluate
  scaffold make run --baseline --data-dir data/crosswords --name baseline \\
    --executor-model gpt-4o --num-train-examples 3 --num-test-examples 5 \\
    --domain crosswords --show-scoring-function

  # Generate from task description
  scaffold make --task "solve crosswords" --scaffolder-model gpt-4o --name task-solver

  # Run existing scaffold
  scaffold run --name my-scaffold --base-dir scaffolds/generated \\
    --executor-model haiku --input "test input"
        """,
    )

    if argv is None:
        argv = sys.argv[1:]

    # Show help if no arguments or only help requested
    if not argv or argv == ["--help"] or argv == ["-h"]:
        parser.print_help()
        sys.exit(0)

    # Determine which commands are present
    has_make = "make" in argv
    has_run = "run" in argv

    if not has_make and not has_run:
        parser.error("Must specify 'make', 'run', or both")

    # Remove the command words and parse remaining args
    remaining_args = [arg for arg in argv if arg not in ["make", "run"]]

    # Add all possible arguments to the parser
    parser.add_argument("--name", help="Name for the scaffold")
    parser.add_argument(
        "--base-dir", type=Path, help="Base directory containing scaffold"
    )

    # Make arguments
    parser.add_argument(
        "--baseline", action="store_true", help="Create prompt-only baseline scaffold"
    )
    parser.add_argument("--data-dir", type=Path, help="Directory with dataset files")
    parser.add_argument("--task", help="Task description for generation")
    parser.add_argument("--scaffolder-model", help="Model for scaffold generation")
    parser.add_argument(
        "--num-train-examples", type=int, help="Number of training examples to use"
    )
    parser.add_argument(
        "--train-seed", type=int, help="Random seed for training example selection"
    )
    parser.add_argument(
        "--show-scoring-function",
        action="store_true",
        help="Include scoring function in prompt",
    )
    parser.add_argument(
        "--suggest-hack",
        action="store_true",
        help="Include text encouraging exploits/hacks",
    )

    # Run arguments
    parser.add_argument("--executor-model", help="Model for scaffold execution")
    parser.add_argument("--input", dest="input_string", help="Input string to process")
    parser.add_argument(
        "--file", dest="input_file", type=Path, help="Read input from file"
    )
    parser.add_argument("--num-test-examples", type=int, help="Number of test examples")
    parser.add_argument(
        "--test-seed", type=int, help="Random seed for test example selection"
    )
    parser.add_argument("--domain", help="Domain for scoring")
    parser.add_argument("--timeout", type=int, help="Execution timeout in seconds")
    parser.add_argument(
        "--no-build", action="store_true", help="Skip Docker image build"
    )
    parser.add_argument(
        "--thinking-budget",
        type=int,
        default=0,
        help="Thinking budget tokens (default: 0)",
    )

    args = parser.parse_args(remaining_args)

    # Build config
    config = ScaffoldConfig()
    config.do_make = has_make
    config.do_run = has_run

    # Copy all arguments
    for attr in [
        "name",
        "base_dir",
        "baseline",
        "data_dir",
        "task",
        "scaffolder_model",
        "num_train_examples",
        "train_seed",
        "show_scoring_function",
        "suggest_hack",
        "executor_model",
        "input_string",
        "input_file",
        "num_test_examples",
        "test_seed",
        "domain",
        "timeout",
        "no_build",
        "thinking_budget",
    ]:
        setattr(config, attr, getattr(args, attr, None))

    return config


def _validate_arguments(config: ScaffoldConfig) -> None:
    """Validate argument combinations and requirements."""
    errors = []

    # Make validation
    if config.do_make:
        if not config.name:
            errors.append("--name is required for make")

        # Check generation mode requirements
        generation_modes = [
            config.baseline and config.data_dir is not None,
            config.data_dir is not None
            and config.scaffolder_model is not None
            and not config.baseline,
            config.task is not None and config.scaffolder_model is not None,
        ]

        if sum(generation_modes) != 1:
            errors.append(
                "Must specify exactly one generation mode:\n"
                "  - --baseline with --data-dir\n"
                "  - --data-dir with --scaffolder-model\n"
                "  - --task with --scaffolder-model"
            )

        # Baseline-specific validation
        if config.baseline:
            if config.scaffolder_model:
                errors.append("--scaffolder-model cannot be used with --baseline")
            if config.task:
                errors.append("--task cannot be used with --baseline")

        # Data-dir mode validation
        if config.data_dir:
            if not config.num_train_examples:
                errors.append("--num-train-examples is required when using --data-dir")
            if not config.train_seed:
                errors.append("--train-seed is required when using --data-dir")

        # Show scoring function validation
        if config.show_scoring_function and config.data_dir and not config.domain:
            errors.append("--domain is required when using --show-scoring-function")

        # Task mode validation
        if config.task:
            if config.data_dir:
                errors.append("Cannot use both --task and --data-dir")
            if config.num_train_examples:
                errors.append("--num-train-examples cannot be used with --task")
            if config.train_seed:
                errors.append("--train-seed cannot be used with --task")

    # Run validation
    if config.do_run:
        if not config.executor_model:
            errors.append("--executor-model is required for run")

        if not config.timeout:
            errors.append("--timeout is required for run")

        # Need name unless we just made a scaffold
        if not config.do_make and not config.name:
            errors.append("--name is required for run (unless after make)")

        # Need base-dir unless we just made a scaffold
        if not config.do_make and not config.base_dir:
            errors.append("--base-dir is required for run (unless after make)")

        # Check input mode
        input_modes = [
            config.input_string is not None,
            config.input_file is not None,
            config.data_dir is not None,
        ]

        if sum(input_modes) != 1:
            errors.append(
                "Must specify exactly one input mode:\n"
                "  - --input <string>\n"
                "  - --file <path>\n"
                "  - --data-dir <path> with --num-test-examples"
            )
        elif config.data_dir:
            # Data-dir run validation
            if not config.num_test_examples:
                errors.append(
                    "--num-test-examples is required when using --data-dir for run"
                )
            if not config.domain:
                errors.append("--domain is required when using --data-dir for run")
            if not config.test_seed:
                errors.append("--test-seed is required when using --data-dir for run")
        else:
            # Single input validation
            if config.domain:
                errors.append("--domain can only be used with --data-dir")
            if config.num_test_examples:
                errors.append("--num-test-examples can only be used with --data-dir")
            if config.test_seed:
                errors.append("--test-seed can only be used with --data-dir")

    # Seed validation
    if config.train_seed and not (config.do_make and config.data_dir):
        errors.append("--train-seed can only be used with --data-dir in make mode")
    if config.test_seed and not (config.do_run and config.data_dir):
        errors.append("--test-seed can only be used with --data-dir in run mode")

    # Raise all errors at once
    if errors:
        raise ValueError("\n".join(errors))


def _infer_base_dir(config: ScaffoldConfig) -> Path:
    """Infer base directory from scaffold type."""
    if config.baseline:
        return Path("scaffolds/baselines")
    else:
        return Path("scaffolds/generated")


def _setup_run_directory(scaffold_dir: Path) -> Path:
    """Create timestamped run directory within scaffold."""
    runs_dir = scaffold_dir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = runs_dir / f"eval_{timestamp}"
    run_dir.mkdir()

    return run_dir


def _get_input_string(config: ScaffoldConfig) -> Optional[str]:
    """Get input string from config (string, file, or None for dataset)."""
    if config.input_string:
        return config.input_string
    elif config.input_file:
        return config.input_file.read_text().strip()
    else:
        return None  # Dataset mode


def _make_scaffold(config: ScaffoldConfig) -> Path:
    """Create a scaffold based on configuration."""
    # Determine output directory
    base_dir = _infer_base_dir(config)
    assert config.name is not None
    scaffold_dir = base_dir / config.name

    # Delete existing scaffold if present
    if scaffold_dir.exists():
        import shutil

        shutil.rmtree(scaffold_dir)

    print(f"Creating scaffold: {config.name}")

    # Load data if needed
    scoring_fn_code = None
    if config.data_dir:
        datasets = load_datasets(config.data_dir, ["train"])
        train_examples = datasets["train"]

        # Sample training examples
        assert config.num_train_examples is not None
        assert config.train_seed is not None
        train_sample = ExampleSampler(
            config.train_seed, train_examples, allow_resample=True
        ).sample(config.num_train_examples)

        # Get scoring function if requested
        if config.show_scoring_function:
            assert config.domain is not None
            scoring_fn_code = get_scoring_function_code(config.domain)

    # Generate scaffold based on mode
    if config.baseline:
        # Baseline mode
        result = make_prompt_only_scaffold(
            examples=train_sample,
            scoring_fn_code=scoring_fn_code,
            suggest_hack=config.suggest_hack,
        )
    elif config.data_dir:
        # Generate from examples
        assert config.scaffolder_model is not None
        scaffolder_llm = LLMFactory.create_llm(config.scaffolder_model)
        result = generate_scaffold(
            scaffolder_llm=scaffolder_llm,
            examples=train_sample,
            scoring_fn_code=scoring_fn_code,
            iteration=None,
            suggest_hack=config.suggest_hack,
        )
    else:
        # Generate from task
        assert config.scaffolder_model is not None
        scaffolder_llm = LLMFactory.create_llm(config.scaffolder_model)
        result = generate_scaffold(
            scaffolder_llm=scaffolder_llm,
            task_description=config.task,
            iteration=None,
            suggest_hack=config.suggest_hack,
        )

    # Save scaffold
    save_scaffold(scaffold_dir, result)
    print(f"Scaffold saved to: {scaffold_dir}")

    return scaffold_dir


def _run_scaffold(
    config: ScaffoldConfig, scaffold_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """Run a scaffold with the given configuration."""
    # Resolve scaffold directory
    if scaffold_dir is None:
        assert config.base_dir is not None
        assert config.name is not None
        scaffold_dir = config.base_dir / config.name
        if not scaffold_dir.exists():
            raise FileNotFoundError(f"Scaffold not found: {scaffold_dir}")

    # Build Docker if needed
    if not config.no_build:
        print("Building Docker image...")
        build_docker_image()

    # Create run directory
    run_dir = _setup_run_directory(scaffold_dir)
    print(f"Run directory: {run_dir}")

    # Prepare for execution
    results = {
        "scaffold_dir": str(scaffold_dir),
        "run_dir": str(run_dir),
        "executor_model": config.executor_model,
        "timestamp": datetime.now().isoformat(),
    }

    # Get input(s)
    single_input = _get_input_string(config)

    if single_input is not None:
        # Single input mode
        print(f"Running scaffold on single input...")

        log_path = run_dir / "0.log"
        assert config.executor_model is not None
        assert config.timeout is not None
        result = execute_scaffold(
            scaffold_dir=scaffold_dir,
            log_file_path=log_path,
            input_string=single_input,
            model_spec=config.executor_model,
            timeout=config.timeout,
            console_output=True,
            thinking_budget_tokens=config.thinking_budget,
        )

        results["mode"] = "single"
        results["output"] = result.output
        results["error"] = result.error_message
        results["execution_time"] = result.execution_time

    else:
        # Dataset evaluation mode
        print(f"Evaluating on {config.num_test_examples} test examples...")

        # Load test data
        assert config.data_dir is not None
        datasets = load_datasets(config.data_dir, ["test"])
        test_examples = datasets["test"]

        # Sample test examples
        assert config.test_seed is not None
        assert config.num_test_examples is not None
        test_sample = ExampleSampler(
            config.test_seed, test_examples, allow_resample=False
        ).sample(config.num_test_examples)

        assert config.domain is not None
        # Create scoring function
        scoring_fn = create_scoring_function(config.domain)

        # Run evaluation
        scores = []
        execution_times = []
        outputs = []

        for i, example in enumerate(test_sample):
            print(f"Running example {i+1}/{len(test_sample)}...", end="", flush=True)

            log_path = run_dir / f"{i}.log"
            assert config.executor_model is not None
            assert config.timeout is not None
            result = execute_scaffold(
                scaffold_dir=scaffold_dir,
                log_file_path=log_path,
                input_string=example.input,
                model_spec=config.executor_model,
                timeout=config.timeout,
                console_output=False,
                thinking_budget_tokens=config.thinking_budget,
            )

            # Score the result
            if result.error_message is None:
                expected = example.scoring_data.get(
                    "solution", str(example.scoring_data)
                )
                score = scoring_fn(expected, {"solution": result.output})
            else:
                score = 0.0

            scores.append(score)
            execution_times.append(result.execution_time)
            outputs.append(
                {
                    "example_id": example.id,
                    "score": score,
                    "output": result.output,
                    "error": result.error_message,
                    "execution_time": result.execution_time,
                }
            )

            print(f" score: {score:.3f}")

        # Calculate statistics
        results["mode"] = "evaluation"
        results["num_examples"] = len(test_sample)
        results["scores"] = scores
        results["mean_score"] = np.mean(scores)
        results["std_score"] = np.std(scores)
        results["execution_times"] = execution_times
        results["mean_execution_time"] = np.mean(execution_times)
        results["outputs"] = outputs

        print(f"\nMean score: {results['mean_score']:.3f} ± {results['std_score']:.3f}")

    # Save results
    results_path = run_dir / "results.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"Results saved to: {results_path}")

    return results


def main():
    """Main entry point."""
    config = parse_args()

    _validate_arguments(config)

    scaffold_dir = None

    # Make phase
    if config.do_make:
        scaffold_dir = _make_scaffold(config)

    # Run phase
    if config.do_run:
        results = _run_scaffold(config, scaffold_dir)

        # Exit with error if scaffold execution failed
        if results.get("error"):
            raise RuntimeError(results["error"])


if __name__ == "__main__":
    main()
