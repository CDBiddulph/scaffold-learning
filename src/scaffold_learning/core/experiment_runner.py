import random
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Callable, Tuple
from scaffold_learning.core.data_structures import (
    DatasetExample,
    ScaffoldResult,
    ScaffoldRunData,
)
from scaffold_learning.core.llm_interfaces import LLMInterface
from scaffold_learning.core.experiment_files import ExperimentFileManager
from scaffold_learning.core.scaffold_generation import (
    generate_scaffold,
    evolve_scaffold,
)
from scaffold_learning.core.scaffold_execution import execute_scaffold


class ExperimentRunner:
    """Orchestrates scaffold learning experiments."""

    def __init__(
        self,
        experiment_name: str,
        training_data: List[DatasetExample],
        validation_data: List[DatasetExample],
        scoring_function: Callable[[str, Dict], float],
        scaffolder_llm: LLMInterface,
        num_iterations: int,
        scaffolds_per_iter: int,
        initial_scaffolds: int,
        num_validation_examples: int,
        base_dir: Path = Path("experiments"),
        executor_model: str = "gpt-4",
    ):
        """Initialize an experiment runner.

        Args:
            experiment_name: Name for this experiment run
            training_data: List of training examples
            validation_data: List of validation examples
            scoring_function: Function that takes (expected, scoring_data) and returns score 0-1
            scaffolder_llm: LLM to use for generating/improving scaffolds
            num_iterations: Number of evolution iterations to run
            scaffolds_per_iter: Number of top scaffolds to evolve each iteration
            initial_scaffolds: Number of scaffolds to create initially
            num_validation_examples: Number of validation examples to use for scoring
            base_dir: Base directory for all experiments
            executor_model: Model name to use for executing scaffolds
        """
        # Validate parameters
        if scaffolds_per_iter > initial_scaffolds:
            raise ValueError(
                "scaffolds_per_iter cannot be greater than initial_scaffolds"
            )

        self.experiment_name = experiment_name
        self.training_data = training_data
        self.validation_data = validation_data
        self.scoring_function = scoring_function
        self.scaffolder_llm = scaffolder_llm
        self.num_iterations = num_iterations
        self.scaffolds_per_iter = scaffolds_per_iter
        self.initial_scaffolds = initial_scaffolds
        self.num_validation_examples = num_validation_examples
        self.executor_model = executor_model

        # Set up experiment directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        experiment_dir = base_dir / f"{experiment_name}_{timestamp}"
        self.file_manager = ExperimentFileManager(experiment_dir)

        # Initialize scaffold ID tracking
        self.scaffold_counters = {}  # parent_id -> next_counter
        self.next_initial_id = 0

        # Track current iteration scores
        self.current_iteration_scores = {}

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
            "num_validation_examples": num_validation_examples,
            "random_seed": random.randint(0, 1000000),
        }
        random.seed(metadata["random_seed"])
        self.file_manager.save_experiment_metadata(metadata)

        self.logger.info(f"Initialized experiment: {experiment_name}")
        self.logger.info(f"Random seed: {metadata['random_seed']}")

    def run(self) -> Path:
        """Run the complete experiment.

        Creates initial scaffolds, runs iterations of evaluation and evolution,
        and returns the best performing scaffold.

        Returns:
            Path to the best performing scaffold directory
        """
        self.logger.info("Starting experiment run")

        # Create initial scaffolds
        prompt = (
            "Generate a Python script that solves crossword clues"  # Default prompt
        )
        scaffold_ids = self._create_initial_scaffolds(prompt)

        best_path = None
        best_score = -1.0

        # Run iterations
        for iteration in range(self.num_iterations):
            self.logger.info(f"Starting iteration {iteration}")

            # Use one set of validation examples within an iteration for consistency
            validation_sample = self._sample_validation_examples()

            # Get scaffolds for this iteration
            if iteration == 0:
                # For iteration 0, just create initial scaffolds
                current_scaffold_ids = scaffold_ids
            else:
                # For later iterations, evolve top scaffolds
                current_scaffold_ids = self._run_evolution_iteration(
                    iteration, validation_sample
                )

            # Evaluate newly created scaffolds and track best
            iter_best_path, iter_best_score = self._evaluate_current_scaffolds(
                iteration, current_scaffold_ids, validation_sample
            )
            if iter_best_score > best_score:
                best_score = iter_best_score
                best_path = iter_best_path

            # Save scores and log results
            self.file_manager.save_scores(
                iteration=iteration,
                train_scores={},  # Not tracking training scores currently
                valid_scores=self.current_iteration_scores,
            )
            self._log_iteration_results(iteration)

        if best_path is None:
            raise RuntimeError("No valid scaffolds were created during the experiment")

        self.logger.info(
            f"Experiment complete. Best scaffold: {best_path} (score: {best_score:.3f})"
        )
        return best_path

    def _sample_validation_examples(self) -> List[DatasetExample]:
        """Sample validation examples for consistent evaluation within an iteration."""
        return random.sample(
            self.validation_data,
            min(self.num_validation_examples, len(self.validation_data)),
        )

    def _run_evolution_iteration(
        self, iteration: int, validation_sample: List[DatasetExample]
    ) -> List[str]:
        """Run one iteration of scaffold evolution.

        Args:
            iteration: Current iteration number
            validation_sample: Validation examples to use for evaluation

        Returns:
            List of newly created scaffold IDs
        """
        self.logger.info("Evaluating all scaffolds from previous iterations")

        # Collect and evaluate previous scaffolds
        all_scaffold_info = self._collect_previous_scaffolds(iteration)
        all_scaffold_scores = self._evaluate_previous_scaffolds(
            iteration, all_scaffold_info, validation_sample
        )

        # Select top scaffolds
        top_scaffolds = self._select_top_scaffolds(
            all_scaffold_info, all_scaffold_scores
        )

        # evolve selected scaffolds
        return self._evolve_scaffolds(iteration, top_scaffolds)

    def _collect_previous_scaffolds(
        self, current_iteration: int
    ) -> Dict[str, Tuple[int, Path]]:
        """Collect scaffold paths from all previous iterations.

        Args:
            current_iteration: Current iteration number

        Returns:
            Dictionary mapping scaffold_id to (iteration, path)
        """
        all_scaffold_info = {}

        for prev_iter in range(current_iteration):
            try:
                train_scores, valid_scores = self.file_manager.load_scores(prev_iter)
                for scaffold_id in valid_scores.keys():
                    path = self.file_manager.get_scaffold_path(prev_iter, scaffold_id)
                    if path.exists():
                        all_scaffold_info[scaffold_id] = (prev_iter, path)
            except FileNotFoundError:
                # No scores file for this iteration
                continue

        return all_scaffold_info

    def _evaluate_previous_scaffolds(
        self,
        iteration: int,
        all_scaffold_info: Dict[str, Tuple[int, Path]],
        validation_sample: List[DatasetExample],
    ) -> Dict[str, float]:
        """Evaluate all previous scaffolds on current validation sample.

        Args:
            iteration: Current iteration number
            all_scaffold_info: Mapping of scaffold_id to (iteration, path)
            validation_sample: Validation examples to evaluate on

        Returns:
            Dictionary mapping scaffold_id to score
        """
        all_scaffold_scores = {}

        for scaffold_id, (scaffold_iter, scaffold_path) in all_scaffold_info.items():
            try:
                score = self._evaluate_scaffold(
                    iteration=iteration,  # Log in current iteration
                    scaffold_id=scaffold_id,
                    validation_examples=validation_sample,
                    source_iteration=scaffold_iter,  # Track where scaffold came from
                )
                all_scaffold_scores[scaffold_id] = score
            except Exception as e:
                self.logger.warning(f"Failed to evaluate scaffold {scaffold_id}: {e}")
                all_scaffold_scores[scaffold_id] = 0.0

        return all_scaffold_scores

    def _select_top_scaffolds(
        self,
        all_scaffold_info: Dict[str, Tuple[int, Path]],
        all_scaffold_scores: Dict[str, float],
    ) -> List[Tuple[str, int, Path]]:
        """Select top scaffolds for evolution based on scores.

        Args:
            all_scaffold_info: Mapping of scaffold_id to (iteration, path)
            all_scaffold_scores: Mapping of scaffold_id to score

        Returns:
            List of (scaffold_id, iteration, path) tuples for top scaffolds
        """
        sorted_scaffolds = sorted(
            all_scaffold_scores.items(), key=lambda x: x[1], reverse=True
        )

        top_scaffolds = []
        for scaffold_id, score in sorted_scaffolds[: self.scaffolds_per_iter]:
            if scaffold_id in all_scaffold_info:
                scaffold_iter, path = all_scaffold_info[scaffold_id]
                top_scaffolds.append((scaffold_id, scaffold_iter, path))
                self.logger.info(
                    f"Selected scaffold {scaffold_id} (score: {score:.3f}) for evolution"
                )

        return top_scaffolds

    def _evolve_scaffolds(
        self, iteration: int, top_scaffolds: List[Tuple[str, int, Path]]
    ) -> List[str]:
        """Evolve selected scaffolds by running on training data and generating new versions.

        Args:
            iteration: Current iteration number
            top_scaffolds: List of (scaffold_id, source_iteration, path) tuples

        Returns:
            List of newly created scaffold IDs
        """
        current_scaffold_ids = []

        for parent_id, parent_iteration, parent_path in top_scaffolds:
            # Copy to old directory
            self.file_manager.copy_scaffold(
                from_path=parent_path,
                to_iteration=iteration,
                to_scaffold_id=parent_id,
            )

            # Generate evolved scaffold
            new_scaffold_id = self._get_next_scaffold_id(parent_id)

            # Run a training example to get feedback
            training_example = random.choice(self.training_data)
            run_data = self._run_training_example(
                iteration=iteration,  # Log training in current iteration
                scaffold_id=parent_id,
                example=training_example,
                source_iteration=parent_iteration,
            )

            # Generate evolved scaffold
            try:
                evolved_result = evolve_scaffold(
                    run_data=run_data, scaffolder_llm=self.scaffolder_llm
                )
                evolved_result.metadata.iteration = iteration
                evolved_result.metadata.parent_scaffold_id = parent_id

                # Save evolved scaffold
                self.file_manager.save_scaffold(
                    iteration=iteration,
                    scaffold_id=new_scaffold_id,
                    result=evolved_result,
                )

                current_scaffold_ids.append(new_scaffold_id)
                self.logger.info(
                    f"Created evolved scaffold {new_scaffold_id} from {parent_id}"
                )

            except Exception as e:
                self.logger.warning(f"Failed to evolve scaffold {parent_id}: {e}")
                # Continue with other scaffolds
                continue

        return current_scaffold_ids

    def _evaluate_current_scaffolds(
        self,
        iteration: int,
        scaffold_ids: List[str],
        validation_sample: List[DatasetExample],
    ) -> Tuple[Optional[Path], float]:
        """Evaluate newly created scaffolds in current iteration.

        Args:
            iteration: Current iteration number
            scaffold_ids: List of scaffold IDs to evaluate
            validation_sample: Validation examples to evaluate on

        Returns:
            Tuple of (best_scaffold_path, best_score) from this iteration
        """
        self.current_iteration_scores = {}
        best_path = None
        best_score = -1.0

        for scaffold_id in scaffold_ids:
            try:
                score = self._evaluate_scaffold(
                    iteration=iteration,
                    scaffold_id=scaffold_id,
                    validation_examples=validation_sample,
                )
                self.current_iteration_scores[scaffold_id] = score

                # Track best scaffold
                if score > best_score:
                    best_score = score
                    best_path = self.file_manager.get_scaffold_path(
                        iteration, scaffold_id
                    )

            except Exception as e:
                self.logger.warning(f"Failed to evaluate scaffold {scaffold_id}: {e}")
                self.current_iteration_scores[scaffold_id] = 0.0

        return best_path, best_score

    def _log_iteration_results(self, iteration: int) -> None:
        """Log summary statistics for the current iteration."""
        if self.current_iteration_scores:
            avg_score = sum(self.current_iteration_scores.values()) / len(
                self.current_iteration_scores
            )
            max_score = max(self.current_iteration_scores.values())
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

    def _create_initial_scaffolds(self, prompt: str) -> List[str]:
        """Create initial scaffolds using random training examples.

        Args:
            prompt: Task description for the scaffolds

        Returns:
            List of scaffold IDs created
        """
        scaffold_ids = []

        self.logger.info(f"Creating {self.initial_scaffolds} initial scaffolds")

        for i in range(self.initial_scaffolds):
            scaffold_id = self._get_next_scaffold_id()

            # Select random training example
            example = random.choice(self.training_data)

            # Generate scaffold
            result = generate_scaffold(
                prompt=prompt,
                scaffolder_llm=self.scaffolder_llm,
                examples=[example],  # Show one example for now
            )

            # Update metadata
            result.metadata.iteration = 0

            # Save scaffold
            self.file_manager.save_scaffold(
                iteration=0, scaffold_id=scaffold_id, result=result
            )

            scaffold_ids.append(scaffold_id)
            self.logger.info(f"Created initial scaffold {scaffold_id}")

        return scaffold_ids

    def _evaluate_scaffold(
        self,
        iteration: int,
        scaffold_id: str,
        validation_examples: List[DatasetExample],
        source_iteration: Optional[int] = None,
    ) -> float:
        """Evaluate a scaffold on validation examples.

        Args:
            iteration: Current iteration number (where to save logs)
            scaffold_id: ID of scaffold to evaluate
            validation_examples: Examples to test the scaffold on
            source_iteration: Iteration where the scaffold was created (if different from iteration)

        Returns:
            Average score across all validation examples
        """
        # Get scaffold from its source iteration
        if source_iteration is not None:
            scaffold_path = self.file_manager.get_scaffold_path(
                source_iteration, scaffold_id
            )
        else:
            scaffold_path = self.file_manager.get_scaffold_path(iteration, scaffold_id)

        scores = []

        for example_idx, example in enumerate(validation_examples):
            # Get logs path with example index to avoid overwriting
            logs_path = self.file_manager.get_logs_path(
                iteration, scaffold_id, f"valid_{example_idx}"
            )

            try:
                # Execute scaffold
                result = execute_scaffold(
                    scaffold_dir=scaffold_path,
                    input_string=example.input,
                    model=self.executor_model,
                    logs_path=logs_path,
                )

                # Calculate score
                if result.exit_code == 0:
                    expected = example.scoring_data.get(
                        "solution", str(example.scoring_data)
                    )
                    score = self.scoring_function(expected, {"solution": result.output})
                else:
                    score = 0.0  # Failed execution gets 0 score

            except Exception as e:
                self.logger.warning(f"Error evaluating scaffold {scaffold_id}: {e}")
                score = 0.0

            scores.append(score)

        average_score = sum(scores) / len(scores) if scores else 0.0
        self.logger.info(
            f"Scaffold {scaffold_id} validation score: {average_score:.3f}"
        )

        return average_score

    def _run_training_example(
        self,
        iteration: int,
        scaffold_id: str,
        example: DatasetExample,
        source_iteration: int = None,
    ) -> ScaffoldRunData:
        """Run a scaffold on a training example.

        Args:
            iteration: Current iteration number (where to save logs)
            scaffold_id: ID of scaffold to run
            example: Training example to process
            source_iteration: Iteration where the scaffold was created (if different from iteration)

        Returns:
            ScaffoldRunData with execution results and score
        """
        # Load scaffold from its source iteration
        if source_iteration is not None:
            scaffold_result = self.file_manager.load_scaffold(
                source_iteration, scaffold_id
            )
            scaffold_path = self.file_manager.get_scaffold_path(
                source_iteration, scaffold_id
            )
        else:
            scaffold_result = self.file_manager.load_scaffold(iteration, scaffold_id)
            scaffold_path = self.file_manager.get_scaffold_path(iteration, scaffold_id)

        # Get logs path
        logs_path = self.file_manager.get_logs_path(iteration, scaffold_id, "train")

        try:
            # Execute scaffold
            execution_result = execute_scaffold(
                scaffold_dir=scaffold_path,
                input_string=example.input,
                model=self.executor_model,
                logs_path=logs_path,
            )

            # Calculate score
            if execution_result.exit_code == 0:
                expected = example.scoring_data.get(
                    "solution", str(example.scoring_data)
                )
                score = self.scoring_function(
                    expected, {"solution": execution_result.output}
                )
            else:
                score = 0.0

            # Read execution log
            execution_log = logs_path.read_text() if logs_path.exists() else ""

            run_data = ScaffoldRunData(
                code=scaffold_result.code,
                execution_log=execution_log,
                example=example,
                actual_output=execution_result.output,
                score=score,
            )

            self.logger.info(f"Training run {scaffold_id}: score {score:.3f}")
            return run_data

        except Exception as e:
            self.logger.warning(
                f"Error running training example for {scaffold_id}: {e}"
            )

            # Return failed run data
            return ScaffoldRunData(
                code=scaffold_result.code,
                execution_log=f"Error: {str(e)}",
                example=example,
                actual_output="",
                score=0.0,
            )
