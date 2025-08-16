#!/usr/bin/env python3
"""
Unified CLI for scaffold creation and execution.

Combines functionality from generate_scaffold.py, evaluate_baseline.py, and run_scaffold.py
into a single command with make and run subcommands.
"""

import argparse
import json
import numpy as np
import shutil
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
from scaffold_learning.core.strategy_generation import generate_strategies
from scaffold_learning.core.data_structures import (
    DatasetExample,
    ScaffoldResult,
    ScaffolderPromptConfig,
)
from scaffold_learning.core.scaffold_execution import execute_scaffolds
from scaffold_learning.core.data_structures import ScaffoldExecutionTask
from scaffold_learning.core.scaffold_files import save_scaffold
from scaffold_learning.core.docker_utils import build_docker_image
from scaffold_learning.core.llm_interfaces import LLMFactory, LLMInterface
from scaffold_learning.core.domain_params import parse_domain_params


@dataclass
class MakeAndRunConfig:
    """Configuration for make_and_run operations."""

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
    suggest_hack: str = "no"
    thinking_budget: Optional[int] = None
    strategy_model: Optional[str] = None
    human_strategy: Optional[str] = None

    # Run arguments
    base_dir: Optional[Path] = None
    executor_model: Optional[str] = None
    input_string: Optional[str] = None
    input_file: Optional[Path] = None
    num_test_examples: Optional[int] = None
    test_seed: Optional[int] = None
    domain: Optional[str] = None
    domain_param: Optional[List[str]] = None
    timeout: Optional[int] = None
    no_build: bool = False
    executor_thinking_budget: Optional[int] = None
    console_output: bool = False
    max_execute_workers: int = 1


def parse_args(argv: Optional[List[str]] = None) -> MakeAndRunConfig:
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
        choices=["no", "hidden", "explicit"],
        default="no",
        help="Include text encouraging exploits/hacks: 'no' (default), 'hidden' (hidden exploits), 'explicit' (obvious exploits)",
    )
    parser.add_argument(
        "--scaffolder-thinking-budget",
        type=int,
        default=10000,
        help="Thinking budget tokens for scaffolder (default: 10000)",
    )
    parser.add_argument(
        "--strategy-model",
        help="Model to use for strategy generation. If --strategy-model and --human-strategy are both unset, no strategy will be used.",
    )
    parser.add_argument(
        "--human-strategy",
        help="Specific strategy to use for scaffold generation, used instead of an LLM-generated strategy. If --strategy-model and --human-strategy are both unset, no strategy will be used.",
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
    parser.add_argument(
        "--domain-param",
        action="append",
        help="Domain parameter in key=value format (can be used multiple times)",
    )
    parser.add_argument("--timeout", type=int, help="Execution timeout in seconds")
    parser.add_argument(
        "--no-build", action="store_true", help="Skip Docker image build"
    )
    parser.add_argument(
        "--executor-thinking-budget",
        type=int,
        default=0,
        help="Thinking budget tokens for executor (default: 0, no thinking)",
    )
    parser.add_argument(
        "--console-output",
        action="store_true",
        help="Enable console output during scaffold execution",
    )
    parser.add_argument(
        "--max-execute-workers",
        type=int,
        default=1,
        help="Maximum workers for parallel scaffold execution (default: 1)",
    )

    args = parser.parse_args(remaining_args)

    # Build config
    config = MakeAndRunConfig()
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
        "thinking_budget",
        "num_train_examples",
        "train_seed",
        "show_scoring_function",
        "suggest_hack",
        "strategy_model",
        "human_strategy",
        "executor_model",
        "executor_thinking_budget",
        "input_string",
        "input_file",
        "num_test_examples",
        "test_seed",
        "domain",
        "domain_param",
        "timeout",
        "no_build",
        "console_output",
        "max_execute_workers",
    ]:
        setattr(config, attr, getattr(args, attr, None))

    return config


def _validate_arguments(config: MakeAndRunConfig) -> None:
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
            if config.num_train_examples is None:
                errors.append("--num-train-examples is required when using --data-dir")
            if config.train_seed is None:
                errors.append("--train-seed is required when using --data-dir")

        # Show scoring function validation
        if config.show_scoring_function and config.data_dir and not config.domain:
            errors.append("--domain is required when using --show-scoring-function")

        # Task mode validation
        if config.task:
            if config.data_dir:
                errors.append("Cannot use both --task and --data-dir")
            if config.num_train_examples is not None:
                errors.append("--num-train-examples cannot be used with --task")
            if config.train_seed is not None:
                errors.append("--train-seed cannot be used with --task")

        # Strategy validation
        if config.human_strategy and config.strategy_model:
            errors.append("Cannot use both --human-strategy and --strategy-model")

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
            if not config.domain:
                errors.append("--domain is required when using --data-dir for run")
            if config.num_test_examples is None:
                errors.append(
                    "--num-test-examples is required when using --data-dir for run"
                )
            if config.test_seed is None:
                errors.append("--test-seed is required when using --data-dir for run")
        else:
            # Single input validation
            if config.domain:
                errors.append("--domain can only be used with --data-dir")
            if config.num_test_examples is not None:
                errors.append("--num-test-examples can only be used with --data-dir")
            if config.test_seed is not None:
                errors.append("--test-seed can only be used with --data-dir")

    # Seed validation
    if config.train_seed and not (config.do_make and config.data_dir):
        errors.append("--train-seed can only be used with --data-dir in make mode")
    if config.test_seed and not (config.do_run and config.data_dir):
        errors.append("--test-seed can only be used with --data-dir in run mode")

    # Console output validation
    if config.console_output and not config.do_run:
        errors.append("--console-output can only be used with run mode")

    # Raise all errors at once
    if errors:
        raise ValueError("\n".join(errors))


def _infer_base_dir(config: MakeAndRunConfig) -> Path:
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


def _get_input_string(config: MakeAndRunConfig) -> Optional[str]:
    """Get input string from config (string, file, or None for dataset)."""
    if config.input_string:
        return config.input_string
    elif config.input_file:
        return config.input_file.read_text().strip()
    else:
        return None  # Dataset mode


def _create_llm(config: MakeAndRunConfig, model_type: str) -> LLMInterface:
    """Create an LLM based on configuration."""
    if model_type == "scaffolder":
        model_name = config.scaffolder_model
    elif model_type == "strategy":
        model_name = config.strategy_model
    else:
        raise ValueError(f"Invalid model type: {model_type}")

    assert model_name is not None
    return LLMFactory.create_llm(
        model_name,
        thinking_budget_tokens=config.thinking_budget,
    )


def _get_strategy(
    make_and_run_config: MakeAndRunConfig,
    scaffolder_prompt_config: ScaffolderPromptConfig,
) -> Optional[str]:
    """Get the strategy to use for scaffold generation."""
    if make_and_run_config.human_strategy:
        return make_and_run_config.human_strategy
    elif make_and_run_config.strategy_model:
        strategies = generate_strategies(
            llm=_create_llm(make_and_run_config, "strategy"),
            scaffolder_prompt_config=scaffolder_prompt_config,
            num_strategies=1,
        )
        return strategies[0] if strategies else None
    else:
        return None


def _get_scaffold_result(
    config: MakeAndRunConfig,
    train_sample: Optional[List[DatasetExample]],
    scoring_fn_code: Optional[str],
) -> ScaffoldResult:
    """Get the scaffold result based on configuration."""
    # Build the prompt config first
    if config.data_dir:
        # Generate from examples
        scaffolder_prompt_config = ScaffolderPromptConfig(
            generate_examples=train_sample,
            scoring_fn_code=scoring_fn_code,
            suggest_hack=config.suggest_hack,
            domain=config.domain,
        )
    else:
        # Generate from task
        scaffolder_prompt_config = ScaffolderPromptConfig(
            task_description=config.task,
            suggest_hack=config.suggest_hack,
            domain=config.domain,
        )

    # Get strategy if needed
    strategy = _get_strategy(config, scaffolder_prompt_config)
    scaffolder_prompt_config.strategy = strategy

    # Generate scaffold based on mode
    if config.baseline:
        # Baseline mode - no LLM, just prompt-only
        return make_prompt_only_scaffold(config=scaffolder_prompt_config)
    else:
        # Generate using scaffolder LLM
        scaffolder_llm = _create_llm(config, "scaffolder")
        return generate_scaffold(
            config=scaffolder_prompt_config,
            scaffolder_llm=scaffolder_llm,
        )


def _make_scaffold(config: MakeAndRunConfig) -> Path:
    """Create a scaffold based on configuration."""
    # Determine output directory
    base_dir = _infer_base_dir(config)
    assert config.name is not None
    scaffold_dir = base_dir / config.name

    # Delete existing scaffold if present
    if scaffold_dir.exists():
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

    result = _get_scaffold_result(config, train_sample, scoring_fn_code)

    # Save scaffold
    save_scaffold(scaffold_dir, result)
    print(f"Scaffold saved to: {scaffold_dir}")

    return scaffold_dir


def _run_scaffold(
    config: MakeAndRunConfig, scaffold_dir: Optional[Path] = None
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
        assert config.executor_thinking_budget is not None

        task = ScaffoldExecutionTask(
            scaffold_dir=str(scaffold_dir),
            log_file_path=str(log_path),
            input_string=single_input,
            model_spec=config.executor_model,
            timeout=config.timeout,
            console_output=True,
            thinking_budget_tokens=config.executor_thinking_budget,
        )

        execution_results = execute_scaffolds([task], max_workers=1)
        result = execution_results[0]

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
        # Parse domain parameters
        domain_params = parse_domain_params(config.domain_param or [])

        # Create scoring function
        scoring_fn = create_scoring_function(config.domain, domain_params=domain_params)

        # Prepare execution tasks
        execution_tasks = []
        for i, example in enumerate(test_sample):
            log_path = run_dir / f"{i}.log"
            execution_tasks.append(
                ScaffoldExecutionTask(
                    scaffold_dir=str(scaffold_dir),
                    log_file_path=str(log_path),
                    input_string=example.input,
                    model_spec=config.executor_model,
                    timeout=config.timeout,
                    console_output=config.console_output,
                    thinking_budget_tokens=config.executor_thinking_budget,
                )
            )

        # Define progress callback
        def progress_callback(completed: int, total: int):
            print(f"Evaluated {completed}/{total} examples", end="\r", flush=True)

        # Execute all tasks
        assert config.executor_model is not None
        assert config.timeout is not None
        assert config.executor_thinking_budget is not None
        results_list = execute_scaffolds(
            tasks=execution_tasks,
            max_workers=config.max_execute_workers,
            progress_callback=(
                progress_callback if config.max_execute_workers > 1 else None
            ),
        )
        print()  # New line after progress updates

        # Process results
        scores = []
        execution_times = []
        outputs = []

        for i, (example, result) in enumerate(zip(test_sample, results_list)):
            # Score the result
            if result.error_message is None:
                score = scoring_fn(result.output, example.scoring_data)
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

            if config.max_execute_workers == 1:
                print(f"Example {i+1}/{len(test_sample)}: score {score:.3f}")

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
