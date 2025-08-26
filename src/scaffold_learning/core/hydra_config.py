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
    scaffold_timeout: int
    max_generate_workers: int
    max_execute_workers: int
    thinking_budget: Optional[int]
    base_dir: str
    build_docker: bool
    
    # Model specifications (from model config)
    model_specs: Dict[str, Dict[str, Any]]
    
    def get_thinking_budget_for_model(self, model_name: str) -> int:
        """Get thinking budget for a specific model."""
        if self.thinking_budget is not None:
            return self.thinking_budget
        return self.model_specs.get(model_name, {}).get("thinking_budget", 0)


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
        scaffold_timeout=cfg.scaffold_timeout,
        max_generate_workers=cfg.max_generate_workers,
        max_execute_workers=cfg.max_execute_workers,
        thinking_budget=cfg.get("thinking_budget"),
        base_dir=cfg.base_dir,
        build_docker=cfg.build_docker,
        model_specs=dict(cfg.model_specs),
    )