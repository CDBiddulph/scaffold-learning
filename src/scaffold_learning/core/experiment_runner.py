import numpy as np
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Callable, Tuple
from scaffold_learning.core.data_structures import (
    DatasetExample,
    ScaffoldRunData,
)
from scaffold_learning.core.llm_interfaces import LLMInterface
from scaffold_learning.core.experiment_files import ExperimentFileManager
from scaffold_learning.core.scaffold_creation import ScaffoldGenerator
from scaffold_learning.core.scaffold_evaluator import ScaffoldEvaluator
from scaffold_learning.core.dataset_utils import load_datasets, ExampleSampler
from scaffold_learning.core.hydra_config import ExperimentConfig


class ExperimentRunner:
    """Orchestrates scaffold learning experiments."""

    def __init__(
        self,
        config: ExperimentConfig,
        data: Dict[str, List[DatasetExample]],
        scoring_fn: Callable[[str, Dict], float],
        scaffolder_llm: Optional[LLMInterface],
        output_dir: Path,
        strategy_llm: Optional[LLMInterface] = None,
        scoring_fn_code: Optional[str] = None,
    ):
        """Initialize an experiment runner with structured configuration.

        Args:
            config: Experiment configuration
            data: Dictionary with 'train', 'valid', and 'test' dataset splits
            scoring_fn: Function that takes (expected, scoring_data) and returns score 0-1
            scaffolder_llm: LLM to use for generating/improving scaffolds (None for baseline mode)
            output_dir: Directory for experiment outputs
            strategy_llm: Optional LLM interface for strategy generation
            scoring_fn_code: Optional scoring function code to include in prompts
        """
        self.config = config
        self.training_data = data["train"]
        self.validation_data = data["valid"]
        self.test_data = data["test"]
        self.scoring_fn = scoring_fn
        self.scaffolder_llm = scaffolder_llm
        self.strategy_llm = strategy_llm
        self.scoring_fn_code = scoring_fn_code

        self.train_sampler = ExampleSampler(
            config.train_seed,
            self.training_data,
            allow_resample=True,
        )
        self.valid_sampler = ExampleSampler(
            config.valid_seed,
            self.validation_data,
            allow_resample=False,
        )
        self.test_sampler = ExampleSampler(
            config.test_seed,
            self.test_data,
            allow_resample=False,
        )

        # Set up experiment directory - use Hydra's output directory
        self.file_manager = ExperimentFileManager(output_dir)

        # Set up logging
        self.logger = logging.getLogger(__name__)

        # Detect baseline mode
        self.is_baseline = config.scaffolder == "baseline"
        if self.is_baseline:
            self.logger.info("Running in baseline mode (prompt-only scaffold)")
        # Set values that special-case in baseline mode
        self.initial_scaffolds = 1 if self.is_baseline else config.initial_scaffolds
        self.num_iterations = 1 if self.is_baseline else config.num_iterations

        # Initialize scaffold generator
        self.scaffold_generator = ScaffoldGenerator(
            config=config,
            scaffolder_llm=scaffolder_llm,
            strategy_llm=strategy_llm,
            file_manager=self.file_manager,
            train_sampler=self.train_sampler,
            scoring_fn_code=scoring_fn_code,
        )

        # Save experiment metadata
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        metadata = {
            "experiment_name": config.experiment_name,
            "created_at": timestamp,
            "num_iterations": self.num_iterations,
            "scaffolds_per_iter": config.scaffolds_per_iter,
            "initial_scaffolds": self.initial_scaffolds,
            "num_training_examples": config.num_training_examples,
            "num_validation_examples": config.num_validation_examples,
            "train_seed": config.train_seed,
            "valid_seed": config.valid_seed,
            "test_seed": config.test_seed,
            "scaffold_timeout": config.scaffold_timeout,
        }
        self.file_manager.save_experiment_metadata(metadata)

        # Initialize scaffold evaluator
        self.scaffold_evaluator = ScaffoldEvaluator(
            scoring_fn=scoring_fn,
            file_manager=self.file_manager,
            executor_model=config.executor,
            scaffold_timeout=config.scaffold_timeout,
            max_execute_workers=config.max_execute_workers,
            executor_reasoning_effort=config.executor_reasoning_effort,
        )

        self.logger.info(f"Initialized experiment: {config.experiment_name}")
        self.logger.info(f"Random training seed: {config.train_seed}")
        self.logger.info(f"Random validation seed: {config.valid_seed}")
        self.logger.info(f"Random test seed: {config.test_seed}")

    def run(self) -> Tuple[Optional[str], float, Optional[float]]:
        """Run the complete experiment.

        Creates initial scaffolds, runs iterations of evaluation and evolution,
        and returns the best performing scaffold.

        Returns:
            Tuple of (best_scaffold_id, best_validation_score, test_score)
            test_score is None if no test evaluation was run
        """
        self.logger.info("Starting experiment run")

        # Sample validation examples once for the entire experiment
        validation_sample = self.valid_sampler.sample(
            self.config.num_validation_examples
        )
        self.logger.info(
            f"Using {len(validation_sample)} validation examples for all iterations"
        )

        best_scaffold_id = None
        best_score = -float("inf")

        # Run iterations (only one iteration for baselines)
        for iteration in range(self.num_iterations):
            self.logger.info(f"Starting iteration {iteration}")

            if iteration == 0:
                # Create and validate initial scaffolds
                scaffold_ids = self.scaffold_generator.create_initial_scaffolds()
            else:
                # Run normal evolution iteration (baseline runs never reach this)
                scaffold_ids = self._run_evolution_iteration(iteration)

            # Get validation scores for the new scaffolds
            validation_scores = self._validate_scaffolds(
                0, scaffold_ids, validation_sample
            )

            # Find best scaffold from current iteration scores
            iter_best_scaffold_id, iter_best_score = (
                self._find_best_scaffold_from_scores(validation_scores)
            )
            if iter_best_score > best_score:
                best_score = iter_best_score
                best_scaffold_id = iter_best_scaffold_id

            # Save scores and log results
            self._log_iteration_results(iteration, validation_scores)

        if best_scaffold_id is None:
            self.logger.warning("No scaffolds were scored during the experiment.")
        else:
            self.logger.info(
                f"Experiment complete. Best scaffold: {best_scaffold_id} (score: {best_score:.3f})"
            )

        # Run test evaluation if configured
        test_score = None
        if self.config.num_test_examples > 0 and best_scaffold_id is not None:
            self.logger.info("Starting test evaluation...")
            test_score = self._run_test_evaluation(best_scaffold_id)

        return best_scaffold_id, best_score, test_score

    def _run_evolution_iteration(
        self,
        iteration: int,
    ) -> List[str]:
        """Run one iteration of scaffold evolution.

        Args:
            iteration: Current iteration number

        Returns:
            List of new scaffold IDs
        """
        # Select top scaffolds to evolve
        top_scaffold_ids = self._select_top_scaffolds()

        # Run training examples for top scaffolds
        top_scaffold_runs = self._run_training(
            iteration=iteration,
            scaffold_ids=top_scaffold_ids,
        )

        # Evolve selected scaffolds and get new scaffold IDs
        return self.scaffold_generator.evolve_scaffolds(iteration, top_scaffold_runs)

    def _validate_scaffolds(
        self,
        iteration: int,
        scaffold_ids: List[str],
        validation_sample: List[DatasetExample],
    ) -> Dict[str, List[float]]:
        """Validate a list of scaffolds and return their scores.

        Args:
            iteration: Current iteration number
            scaffold_ids: List of scaffold IDs to validate
            validation_sample: Validation examples to use

        Returns:
            Dictionary mapping scaffold_id to list of validation scores
        """
        validation_scores = {}
        for scaffold_id in scaffold_ids:
            run_data = self.scaffold_evaluator.evaluate_scaffold(
                iteration,
                scaffold_id,
                validation_sample,
                "valid",
            )
            scores = [rd.score for rd in run_data]
            validation_scores[scaffold_id] = scores
        return validation_scores

    def _select_top_scaffolds(self) -> List[str]:
        """Select top scaffolds to evolve using pre-computed validation scores.

        Returns:
            List of top scaffold IDs to evolve
        """
        # Get most recent validation scores for ranking
        most_recent_scores = self.file_manager.get_most_recent_validation_scores()

        # All scaffolds should have been validated in their creation iteration
        all_scaffold_scores = {}
        for scaffold_id, score_dict in most_recent_scores.items():
            if score_dict is None:
                raise ValueError(f"Scaffold {scaffold_id} has no validation scores")
            all_scaffold_scores[scaffold_id] = score_dict["mean_score"]

        # Sort scaffolds by score and select top K
        sorted_scaffolds = sorted(
            all_scaffold_scores.items(), key=lambda x: x[1], reverse=True
        )
        top_k_ids = [
            scaffold_id
            for scaffold_id, _ in sorted_scaffolds[: self.config.scaffolds_per_iter]
        ]

        # Log results for top K scaffolds
        id_score_pairs = [f"{id}: {score:.3f}" for id, score in sorted_scaffolds]
        logging.info(f"Using validation scores: {', '.join(id_score_pairs)}")
        logging.info(f"Selected top {len(top_k_ids)} scaffolds: {', '.join(top_k_ids)}")

        return top_k_ids

    def _find_best_scaffold_from_scores(
        self,
        scores: Dict[str, List[float]],
    ) -> Tuple[Optional[str], float]:
        """Find the best scaffold from current iteration scores.

        Args:
            iteration: Current iteration number
            scores: Dictionary mapping scaffold_id to list of scores

        Returns:
            Tuple of (best_scaffold_id, best_score) from this iteration
        """
        best_scaffold_id = None
        best_score = -float("inf")

        for scaffold_id, score_list in scores.items():
            score = float(np.mean(score_list))
            if score > best_score:
                best_score = score
                best_scaffold_id = scaffold_id

        return best_scaffold_id, best_score

    def _log_iteration_results(
        self, iteration: int, validation_scores: Dict[str, List[float]]
    ) -> None:
        """Log summary statistics for the current iteration."""
        if validation_scores:
            mean_scores = [
                float(np.mean(score_list)) for score_list in validation_scores.values()
            ]
            avg_score = np.mean(mean_scores)
            max_score = max(mean_scores)
            self.logger.info(
                f"Iteration {iteration}: avg={avg_score:.3f}, max={max_score:.3f}"
            )

    def _run_training(
        self,
        iteration: int,
        scaffold_ids: List[str],
    ) -> Dict[str, List[ScaffoldRunData]]:
        """Run scaffolds on training examples and get ScaffoldRunData.

        Args:
            iteration: Current iteration number (where to save logs)
            scaffold_ids: List of scaffold IDs to run

        Returns:
            Dictionary mapping scaffold_id to list of ScaffoldRunData
        """
        training_runs = {}
        for scaffold_id in scaffold_ids:
            examples = self.train_sampler.sample(self.config.num_training_examples)
            run_data = self.scaffold_evaluator.evaluate_scaffold(
                iteration,
                scaffold_id,
                examples,
                "train",
            )
            training_runs[scaffold_id] = run_data
        return training_runs

    def _run_test_evaluation(self, best_scaffold_id: str) -> float:
        """Run test evaluation on the best scaffold.

        Args:
            best_scaffold_id: ID of the best scaffold to evaluate

        Returns:
            Mean test score
        """

        # Sample test examples
        test_sample = self.test_sampler.sample(self.config.num_test_examples)

        self.logger.info(f"Evaluating {len(test_sample)} test examples...")

        # Run scaffold on test examples - use scaffold evaluator
        run_data = self.scaffold_evaluator.evaluate_scaffold(
            iteration="test",  # Special marker for test runs
            scaffold_id=best_scaffold_id,
            examples=test_sample,
            log_type="test",
        )
        scores = [rd.score for rd in run_data]

        # Log results
        mean_score = float(np.mean(scores))
        std_score = float(np.std(scores))
        self.logger.info(
            f"Test evaluation complete: {mean_score:.3f} ± {std_score:.3f}"
        )

        return mean_score
