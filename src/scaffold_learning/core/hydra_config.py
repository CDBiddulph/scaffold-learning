"""Hydra configuration dataclasses for scaffold learning experiments."""

from dataclasses import dataclass
from typing import Dict, Optional, Any
from omegaconf import DictConfig


@dataclass
class ExperimentConfig:
    """Configuration for experiment parameters."""

    experiment_name: str
    data_dir: str
    domain: str
    domain_params: Dict[str, str]

    # Experiment flow
    num_iterations: int
    scaffolds_per_iter: int
    initial_scaffolds: int
    num_validation_examples: int
    num_training_examples: int

    # Model configuration
    scaffolder: str
    executor: str
    strategy: Optional[str]
    strategy_batch_size: Optional[int]

    # Execution settings
    show_scoring_function: bool
    suggest_hack: str
    train_seed: int
    valid_seed: int
    test_seed: int
    num_test_examples: int
    scaffold_timeout: int
    max_generate_workers: int
    max_execute_workers: int
    base_dir: str
    build_docker: bool

    # Reasoning effort configuration
    executor_reasoning_effort: str
    scaffolder_reasoning_effort: str



def create_experiment_config(cfg: DictConfig) -> ExperimentConfig:
    """Create ExperimentConfig from Hydra DictConfig."""
    return ExperimentConfig(
        experiment_name=cfg.experiment_name,
        data_dir=cfg.data_dir,
        domain=cfg.domain,
        domain_params=dict(cfg.get("domain_params", {})),
        num_iterations=cfg.num_iterations,
        scaffolds_per_iter=cfg.scaffolds_per_iter,
        initial_scaffolds=cfg.initial_scaffolds,
        num_validation_examples=cfg.num_validation_examples,
        num_training_examples=cfg.num_training_examples,
        scaffolder=cfg.scaffolder,
        executor=cfg.executor,
        strategy=cfg.strategy,
        strategy_batch_size=cfg.strategy_batch_size,
        show_scoring_function=cfg.show_scoring_function,
        suggest_hack=cfg.suggest_hack,
        train_seed=cfg.train_seed,
        valid_seed=cfg.valid_seed,
        test_seed=cfg.test_seed,
        num_test_examples=cfg.num_test_examples,
        scaffold_timeout=cfg.scaffold_timeout,
        max_generate_workers=cfg.max_generate_workers,
        max_execute_workers=cfg.max_execute_workers,
        base_dir=cfg.base_dir,
        build_docker=cfg.build_docker,
        executor_reasoning_effort=cfg.executor_reasoning_effort,
        scaffolder_reasoning_effort=cfg.scaffolder_reasoning_effort,
    )
