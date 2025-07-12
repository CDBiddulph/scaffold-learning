import numpy as np
import random
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Callable, Tuple, Any
from collections import defaultdict
from scaffold_learning.core.data_structures import (
    DatasetExample,
    ScaffoldRunData,
)
from scaffold_learning.core.llm_interfaces import LLMInterface
from scaffold_learning.core.experiment_files import ExperimentFileManager
from scaffold_learning.core.scaffold_generation import (
    generate_scaffold,
    evolve_scaffold,
)
from scaffold_learning.core.scaffold_execution import (
    execute_scaffold,
    ScaffoldExecutionResult,
)
from scaffold_learning.core.dataset_utils import sample_examples


class ExperimentRunner:
    """Orchestrates scaffold learning experiments."""

    def __init__(
        self,
        experiment_name: str,
        training_data: List[DatasetExample],
        validation_data: List[DatasetExample],
        scoring_fn: Callable[[str, Dict], float],
        scaffolder_llm: LLMInterface,
        num_iterations: int,
        scaffolds_per_iter: int,
        initial_scaffolds: int,
        num_training_examples: int,
        num_validation_examples: int,
        base_dir: Path = Path("experiments"),
        executor_model: str = "gpt-4",
        scoring_fn_code: Optional[str] = None,
        suggest_hack: bool = False,
    ):
        """Initialize an experiment runner.

        Args:
            experiment_name: Name for this experiment run
            training_data: List of training examples
            validation_data: List of validation examples
            scoring_fn: Function that takes (expected, scoring_data) and returns score 0-1
            scaffolder_llm: LLM to use for generating/improving scaffolds
            num_iterations: Number of evolution iterations to run
            scaffolds_per_iter: Number of top scaffolds to evolve each iteration
            initial_scaffolds: Number of scaffolds to create initially
            num_training_examples: Number of training examples to use for demonstration
            num_validation_examples: Number of validation examples to use for scoring
            base_dir: Base directory for all experiments
            executor_model: Model name to use for executing scaffolds
            scoring_fn_code: Scoring function code to include in prompts
            suggest_hack: If True, include text encouraging the model to find exploits/hacks
        """
        # Validate parameters
        if scaffolds_per_iter > initial_scaffolds:
            raise ValueError(
                "scaffolds_per_iter cannot be greater than initial_scaffolds"
            )

        self.experiment_name = experiment_name
        self.training_data = training_data
        self.validation_data = validation_data
        self.scoring_fn = scoring_fn
        self.scaffolder_llm = scaffolder_llm
        self.num_iterations = num_iterations
        self.scaffolds_per_iter = scaffolds_per_iter
        self.initial_scaffolds = initial_scaffolds
        self.num_training_examples = num_training_examples
        self.num_validation_examples = num_validation_examples
        self.executor_model = executor_model
        self.scoring_fn_code = scoring_fn_code
        self.suggest_hack = suggest_hack

        # Set up experiment directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        experiment_dir = base_dir / f"{experiment_name}_{timestamp}"
        self.file_manager = ExperimentFileManager(experiment_dir)

        # Initialize scaffold ID tracking
        self.scaffold_counters = {}  # parent_id -> next_counter
        self.next_initial_id = 0

        # Set up logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        # Save experiment metadata
        metadata = {
            "experiment_name": experiment_name,
            "created_at": timestamp,
            "num_iterations": num_iterations,
            "scaffolds_per_iter": scaffolds_per_iter,
            "initial_scaffolds": initial_scaffolds,
            "num_training_examples": num_training_examples,
            "num_validation_examples": num_validation_examples,
            "random_seed": random.randint(0, 1000000),
        }
        random.seed(metadata["random_seed"])
        self.file_manager.save_experiment_metadata(metadata)

        self.logger.info(f"Initialized experiment: {experiment_name}")
        self.logger.info(f"Random seed: {metadata['random_seed']}")

    def run(self) -> Tuple[Optional[str], float]:
        """Run the complete experiment.

        Creates initial scaffolds, runs iterations of evaluation and evolution,
        and returns the best performing scaffold.

        Returns:
            Tuple of (best_scaffold_id, best_score)
        """
        self.logger.info("Starting experiment run")

        self.logger.info("Creating initial scaffolds for iteration 0")
        self._create_initial_scaffolds()

        # Sample validation examples once for the entire experiment
        validation_sample = sample_examples(
            self.validation_data, self.num_validation_examples
        )
        self.logger.info(
            f"Using {len(validation_sample)} validation examples for all iterations"
        )

        best_scaffold_id = None
        best_score = -1.0

        # Run iterations
        for iteration in range(1, self.num_iterations):
            self.logger.info(f"Starting iteration {iteration}")

            training_scores, validation_scores = self._run_evolution_iteration(
                iteration, validation_sample
            )

            # Find best scaffold from current iteration scores
            iter_best_scaffold_id, iter_best_score = (
                self._find_best_scaffold_from_scores(iteration, validation_scores)
            )
            if iter_best_score > best_score:
                best_score = iter_best_score
                best_scaffold_id = iter_best_scaffold_id

            # Save scores and log results
            self.file_manager.save_scores(
                iteration=iteration,
                train_scores=training_scores,
                valid_scores=validation_scores,
            )
            self._log_iteration_results(iteration, validation_scores)

        if best_scaffold_id is None:
            self.logger.warning("No scaffolds were scored during the experiment.")
        else:
            self.logger.info(
                f"Experiment complete. Best scaffold: {best_scaffold_id} (score: {best_score:.3f})"
            )
        return best_scaffold_id, best_score

    def _run_evolution_iteration(
        self,
        iteration: int,
        validation_sample: List[DatasetExample],
    ) -> Tuple[Dict[str, float], Dict[str, float]]:
        """Run one iteration of scaffold evolution.

        Args:
            iteration: Current iteration number
            validation_sample: Validation examples to use for evaluation

        Returns:
            Tuple of (training_scores, validation_scores) - dictionaries mapping scaffold_id to score
        """
        # Select top scaffolds to evolve
        top_scaffold_ids, validation_scores = self._select_top_scaffolds(
            iteration, validation_sample
        )

        # Run training examples for top scaffolds
        top_scaffold_runs = self._run_training(
            iteration=iteration,
            scaffold_ids=top_scaffold_ids,
        )

        # Calculate training scores with individual scores for each scaffold
        training_scores = {}
        for scaffold_id, run_data_list in top_scaffold_runs.items():
            scores = [run_data.score for run_data in run_data_list]
            training_scores[scaffold_id] = {
                "mean_score": np.mean(scores),
                "scores": scores,
            }

        # Evolve selected scaffolds
        self._evolve_scaffolds(iteration, top_scaffold_runs)

        return training_scores, validation_scores

    def _select_top_scaffolds(
        self,
        iteration: int,
        validation_sample: List[DatasetExample],
    ) -> Tuple[List[str], Dict[str, Dict[str, Any]]]:
        """Select top scaffolds to evolve.

        Args:
            iteration: Current iteration number
            validation_sample: Validation examples to use for evaluation

        Returns:
            Tuple of (top_scaffold_ids, validation_scores) where validation_scores
            maps scaffold_id to dict with 'mean_score' and 'scores' keys
        """
        # Get most recent validation scores for ranking
        most_recent_scores = self.file_manager.get_most_recent_validation_scores()

        # Validate any scaffolds that haven't been validated yet
        newly_validated_scores = {}
        for scaffold_id in most_recent_scores:
            if most_recent_scores[scaffold_id] is None:
                # This scaffold has never been validated
                scores = self._run_scaffold_on_examples(
                    iteration, scaffold_id, validation_sample, "valid"
                )
                newly_validated_scores[scaffold_id] = {
                    "mean_score": np.mean(scores),
                    "scores": scores,
                }

        # Create combined scores for selection (newly validated + previously validated)
        all_scaffold_scores = {}
        for scaffold_id, score in most_recent_scores.items():
            if scaffold_id in newly_validated_scores:
                all_scaffold_scores[scaffold_id] = newly_validated_scores[scaffold_id][
                    "mean_score"
                ]
            else:
                all_scaffold_scores[scaffold_id] = score

        # Sort scaffolds by score and select top K
        sorted_scaffolds = sorted(
            all_scaffold_scores.items(), key=lambda x: x[1], reverse=True
        )
        top_k_ids = [
            scaffold_id
            for scaffold_id, _ in sorted_scaffolds[: self.scaffolds_per_iter]
        ]

        # Log results for top K scaffolds
        id_score_pairs = [f"{id}: {score:.3f}" for id, score in sorted_scaffolds]
        logging.info(f"Got validation scores: {', '.join(id_score_pairs)}")
        logging.info(f"Selected top {len(top_k_ids)} scaffolds: {', '.join(top_k_ids)}")

        # Return only newly validated scores to be saved to the scoring JSON
        return top_k_ids, newly_validated_scores

    def _evolve_scaffolds(
        self,
        iteration: int,
        top_scaffold_runs: Dict[str, List[ScaffoldRunData]],
    ) -> List[str]:
        """Evolve selected scaffolds by running on training data and generating new versions.

        Args:
            iteration: Current iteration number
            top_scaffold_runs: Dict of scaffold_id to list of ScaffoldRunData for top scaffolds

        Returns:
            List of newly created scaffold IDs
        """
        current_scaffold_ids = []

        for parent_id, run_data_list in top_scaffold_runs.items():
            evolved_result = evolve_scaffold(
                run_data=run_data_list,
                scaffolder_llm=self.scaffolder_llm,
                scoring_fn_code=self.scoring_fn_code,
                iteration=iteration,
                parent_scaffold_id=parent_id,
                suggest_hack=self.suggest_hack,
            )

            # Save evolved scaffold
            new_scaffold_id = self._get_next_scaffold_id(parent_id)
            self.file_manager.save_scaffold(
                scaffold_id=new_scaffold_id,
                result=evolved_result,
            )

            current_scaffold_ids.append(new_scaffold_id)
            self.logger.info(
                f"Created evolved scaffold {new_scaffold_id} from {parent_id}"
            )

        return current_scaffold_ids

    def _find_best_scaffold_from_scores(
        self,
        iteration: int,
        scores: Dict[str, Dict[str, Any]],
    ) -> Tuple[Optional[str], float]:
        """Find the best scaffold from current iteration scores.

        Args:
            iteration: Current iteration number
            scores: Dictionary mapping scaffold_id to score data dict

        Returns:
            Tuple of (best_scaffold_id, best_score) from this iteration
        """
        best_scaffold_id = None
        best_score = -1.0

        for scaffold_id, score_data in scores.items():
            score = score_data["mean_score"]
            if score > best_score:
                best_score = score
                best_scaffold_id = scaffold_id

        return best_scaffold_id, best_score

    def _log_iteration_results(
        self, iteration: int, validation_scores: Dict[str, Dict[str, Any]]
    ) -> None:
        """Log summary statistics for the current iteration."""
        if validation_scores:
            mean_scores = [
                score_data["mean_score"] for score_data in validation_scores.values()
            ]
            avg_score = np.mean(mean_scores)
            max_score = max(mean_scores)
            self.logger.info(
                f"Iteration {iteration}: avg={avg_score:.3f}, max={max_score:.3f}"
            )

    def _get_next_scaffold_id(self, parent_id: Optional[str] = None) -> str:
        """Generate the next scaffold ID.

        Args:
            parent_id: Parent scaffold ID if this is a derived scaffold

        Returns:
            New scaffold ID following the naming convention
        """
        if parent_id is None:
            # Initial scaffold: use sequential numbers
            scaffold_id = str(self.next_initial_id)
            self.next_initial_id += 1
            return scaffold_id
        else:
            # Derived scaffold: append counter to parent ID
            if parent_id not in self.scaffold_counters:
                self.scaffold_counters[parent_id] = 0

            counter = self.scaffold_counters[parent_id]
            self.scaffold_counters[parent_id] += 1

            return f"{parent_id}-{counter}"

    def _create_initial_scaffolds(self) -> List[str]:
        """Create initial scaffolds using random training examples.

        Returns:
            List of scaffold IDs created
        """
        # This will end up just being ["0", "1", "2", ...]
        scaffold_ids = [
            self._get_next_scaffold_id() for _ in range(self.initial_scaffolds)
        ]

        self.logger.info(f"Creating {self.initial_scaffolds} initial scaffolds")

        for scaffold_id, examples in self._get_training_examples(scaffold_ids).items():
            # Generate scaffold
            result = generate_scaffold(
                examples=examples,
                scaffolder_llm=self.scaffolder_llm,
                scoring_fn_code=self.scoring_fn_code,
                iteration=0,
                suggest_hack=self.suggest_hack,
            )

            # Save scaffold
            self.file_manager.save_scaffold(scaffold_id=scaffold_id, result=result)

            scaffold_ids.append(scaffold_id)
            self.logger.info(f"Created initial scaffold {scaffold_id}")

        return scaffold_ids

    def _execute_and_score_scaffold(
        self,
        iteration: int,
        scaffold_id: str,
        example: DatasetExample,
        log_type: str,
    ) -> Tuple[ScaffoldExecutionResult, float]:
        """Execute a scaffold on a single example and return the score and execution result.

        Args:
            iteration: Current iteration number (where to save logs)
            scaffold_id: ID of scaffold to execute
            example: Example to test the scaffold on
            log_type: Type of log ("train" or "valid")

        Returns:
            Tuple of (execution_result, score)
        """
        # Execute scaffold
        result = execute_scaffold(
            scaffold_dir=self.file_manager.get_scaffold_dir(scaffold_id),
            log_file_path=self.file_manager.get_new_execution_log_path(
                iteration, scaffold_id, log_type
            ),
            input_string=example.input,
            model_spec=self.executor_model,
            console_output=False,
        )

        # Calculate score
        if result.error_message is None:
            expected = example.scoring_data.get("solution", str(example.scoring_data))
            score = self.scoring_fn(expected, {"solution": result.output})
        else:
            logging.warning(
                f"Scaffold {scaffold_id} failed to execute: {result.error_message}"
            )
            score = 0.0  # Failed execution gets 0 score

        return result, score

    def _run_scaffold_on_examples(
        self,
        iteration: int,
        scaffold_id: str,
        examples: List[DatasetExample],
        log_type: str,
        run_data_list: Optional[List[ScaffoldRunData]] = None,
        scaffold_code: Optional[str] = None,
    ) -> List[float]:
        """Run a scaffold on examples and return scores and run data.

        Args:
            iteration: Current iteration number (where to save logs)
            scaffold_id: ID of scaffold to run
            examples: Examples to test the scaffold on
            log_type: Type of log ("train" or "valid")
            run_data_list: List of ScaffoldRunData to append to. Requires scaffold_code.
            scaffold_code: Scaffold code to use for ScaffoldRunData.

        Returns:
            A list of scores, in order of examples
        """
        scores = []

        for example in examples:
            execution_result, score = self._execute_and_score_scaffold(
                iteration, scaffold_id, example, log_type
            )
            scores.append(score)

            # For training, create ScaffoldRunData
            if run_data_list is not None:
                if scaffold_code is None:
                    raise ValueError("Scaffold code is required for ScaffoldRunData")
                run_data_list.append(
                    ScaffoldRunData(
                        code=scaffold_code,
                        execution_log=execution_result.stderr,
                        example=example,
                        actual_output=execution_result.output,
                        score=score,
                    )
                )

        # Log scores
        log_type_str = "validation" if log_type == "valid" else "training"
        scores_str = ", ".join(f"{s:.3f}" for s in scores)
        if len(scores) > 1:
            maybe_s, average_str = "s", f" (avg {np.mean(scores):.3f})"
        else:
            maybe_s, average_str = "", ""
        self.logger.info(
            f"Scaffold {scaffold_id} {log_type_str} score{maybe_s}: {scores_str}{average_str}"
        )

        return scores

    # TODO: move to dataset_utils and add test cases that check that this works
    # TODO: make this work for validation examples too
    def _get_training_examples(
        self, scaffold_ids: List[str]
    ) -> Dict[str, List[DatasetExample]]:
        """Randomly sample training examples, minimizing duplicates."""
        n = len(scaffold_ids) * self.num_training_examples
        flat_examples = (
            self.training_data * (n // len(self.training_data))
        ) + random.sample(self.training_data, n % len(self.training_data))
        random.shuffle(flat_examples)
        examples_by_scaffold = {}
        i = 0
        for scaffold_id in scaffold_ids:
            examples_by_scaffold[scaffold_id] = flat_examples[
                i : i + self.num_training_examples
            ]
            i += self.num_training_examples
        return examples_by_scaffold

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
        examples_by_scaffold = self._get_training_examples(scaffold_ids)
        training_runs = defaultdict(list)
        for scaffold_id, examples in examples_by_scaffold.items():
            # Load scaffold to get code for ScaffoldRunData
            scaffold_result = self.file_manager.load_scaffold(scaffold_id)
            self._run_scaffold_on_examples(
                iteration,
                scaffold_id,
                examples,
                "train",
                scaffold_code=scaffold_result.code,
                run_data_list=training_runs[scaffold_id],
            )

        return training_runs
