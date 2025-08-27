#!/usr/bin/env python3
"""CLI for running scaffold learning experiments with Hydra configuration."""

import logging
import os
from pathlib import Path
from typing import Optional

import hydra
from hydra.core.hydra_config import HydraConfig
from omegaconf import DictConfig

from scaffold_learning.core.hydra_config import create_experiment_config
from scaffold_learning.core.experiment_runner import ExperimentRunner
from scaffold_learning.core.llm_interfaces import LLMFactory, LLMInterface
from scaffold_learning.core.dataset_utils import load_datasets
from scaffold_learning.core.scoring_utils import (
    create_scoring_function,
    get_scoring_function_code,
)
from scaffold_learning.core.docker_utils import build_docker_image


# Get absolute path to config directory
_config_path = Path(__file__).parent.parent.parent.parent / "hydra-configs"


def _get_scaffolder_llm(config: DictConfig) -> Optional[LLMInterface]:
    # Create scaffolder LLM (None for baseline mode)
    if config.scaffolder == "baseline":
        print("Running in baseline mode (no scaffolder LLM needed)")
        return None

    scaffolder_thinking_budget = config.get_thinking_budget_for_model(config.scaffolder)
    print(f"Initializing scaffolder model: {config.scaffolder}")
    return LLMFactory.create_llm(
        config.scaffolder, thinking_budget_tokens=scaffolder_thinking_budget
    )


def _get_strategy_llm(config: DictConfig) -> Optional[LLMInterface]:
    if not config.strategy or config.strategy == "baseline":
        return None
    strategy_thinking_budget = config.get_thinking_budget_for_model(config.strategy)
    print(f"Initializing strategy model: {config.strategy}")
    return LLMFactory.create_llm(
        config.strategy, thinking_budget_tokens=strategy_thinking_budget
    )


@hydra.main(version_base=None, config_path=str(_config_path), config_name="config")
def main(cfg: DictConfig) -> None:
    """Run scaffold learning experiment with Hydra configuration."""

    # Configure logging first before anything else
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    # Convert Hydra config to structured config
    config = create_experiment_config(cfg)

    # Validate arguments
    data_dir = Path(config.data_dir)
    if not data_dir.exists() or not data_dir.is_dir():
        raise FileNotFoundError(f"Data directory not found: {data_dir}")

    if (
        config.scaffolds_per_iter > config.initial_scaffolds
        and config.num_iterations > 1
    ):
        raise ValueError("scaffolds_per_iter cannot be greater than initial_scaffolds")

    if config.strategy_batch_size and config.strategy:
        if config.initial_scaffolds % config.strategy_batch_size != 0:
            raise ValueError(
                f"initial_scaffolds ({config.initial_scaffolds}) must be divisible by "
                f"strategy_batch_size ({config.strategy_batch_size})"
            )

    # Build Docker image
    if config.build_docker:
        print("Building Docker image...")
        build_docker_image()

    # Load datasets
    print("Loading datasets...")
    splits = ["train", "valid", "test"]
    data = load_datasets(data_dir, splits=splits)

    # Create scoring function and get a code representation of it
    print(f"Setting up {config.domain} domain...")
    scoring_fn = create_scoring_function(
        config.domain, domain_params=config.domain_params
    )
    scoring_fn_code = (
        get_scoring_function_code(config.domain, domain_params=config.domain_params)
        if config.show_scoring_function
        else None
    )

    scaffolder_llm = _get_scaffolder_llm(config)
    strategy_llm = _get_strategy_llm(config)

    # Get Hydra's output directory for this job
    output_dir = Path(HydraConfig.get().runtime.output_dir)

    # Create experiment runner
    print("Initializing experiment runner...")
    runner = ExperimentRunner(
        config,
        data,
        scoring_fn,
        scaffolder_llm,
        output_dir,
        strategy_llm,
        scoring_fn_code,
    )

    # Run experiment
    print("Starting experiment...")
    best_scaffold_path, best_validation_score, test_score = runner.run()

    # Print results
    print("\n" + "=" * 50)
    print("EXPERIMENT COMPLETE")
    print("=" * 50)
    print(f"Best scaffold path: {best_scaffold_path}")
    print(f"Best scaffold validation score: {best_validation_score:.3f}")
    if test_score is not None:
        print(f"Best scaffold test score: {test_score:.3f}")
    print("=" * 50)


if __name__ == "__main__":
    main()
