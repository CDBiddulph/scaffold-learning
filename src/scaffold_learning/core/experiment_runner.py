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
                # For iteration 0, just create initial scaffolds - no validation
                current_scaffold_ids = scaffold_ids
                self.current_iteration_scores = {}
            else:
                # For later iterations, evolve top scaffolds using smart validation
                current_scaffold_ids = self._run_evolution_iteration(
                    iteration, validation_sample
                )

            # For iteration 0, we don't validate; for later iterations, validation is done in _run_evolution_iteration
            if iteration == 0:
                # Track best path as first scaffold for iteration 0 since we don't validate
                if current_scaffold_ids:
                    iter_best_path = self.file_manager.get_scaffold_path(
                        iteration, current_scaffold_ids[0]
                    )
                    iter_best_score = 0.0  # We don't know the score yet
                    best_path = iter_best_path  # Set initial best path
                else:
                    iter_best_path = None
                    iter_best_score = -1.0
            else:
                # Find best scaffold from current iteration scores
                iter_best_path, iter_best_score = self._find_best_scaffold_from_scores(
                    iteration, self.current_iteration_scores
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
        """Run one iteration of scaffold evolution using smart validation.

        Args:
            iteration: Current iteration number
            validation_sample: Validation examples to use for evaluation

        Returns:
            List of newly created scaffold IDs
        """
        self.logger.info("Running evolution iteration with smart validation")

        # Collect scaffold info from previous iterations
        all_scaffold_info = self._collect_previous_scaffolds(iteration)

        # Get most recent validation scores for ranking
        most_recent_scores = self._get_most_recent_validation_scores(
            all_scaffold_info, iteration
        )

        # Select top scaffolds using smart validation
        top_scaffolds = self._select_top_scaffolds_smart_validation(
            iteration, all_scaffold_info, most_recent_scores, validation_sample
        )

        # Evolve selected scaffolds
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
            # First, try to get scaffolds from scores file (scaffolds that were validated)
            try:
                train_scores, valid_scores = self.file_manager.load_scores(prev_iter)
                for scaffold_id in valid_scores.keys():
                    path = self.file_manager.get_scaffold_path(prev_iter, scaffold_id)
                    if path.exists():
                        all_scaffold_info[scaffold_id] = (prev_iter, path)

                # Always check directory structure to find scaffolds created in this iteration
                # (they won't be in the scores file since they weren't validated)
                iter_dir = (
                    self.file_manager.experiment_dir
                    / "iterations"
                    / str(prev_iter)
                    / "scaffolds"
                )
                if iter_dir.exists():
                    # Check both 'new' and 'old' subdirectories
                    for subdir_name in ["new", "old"]:
                        subdir = iter_dir / subdir_name
                        if subdir.exists():
                            for scaffold_dir in subdir.iterdir():
                                if scaffold_dir.is_dir():
                                    scaffold_id = scaffold_dir.name
                                    # Only add if not already found (prefer scaffolds from scores file for path accuracy)
                                    if scaffold_id not in all_scaffold_info:
                                        all_scaffold_info[scaffold_id] = (
                                            prev_iter,
                                            scaffold_dir,
                                        )

            # TODO: check whether this FileNotFoundError is needed or just a hack
            except FileNotFoundError:
                # No scores file for this iteration, check directory structure instead
                iter_dir = (
                    self.file_manager.experiment_dir
                    / "iterations"
                    / str(prev_iter)
                    / "scaffolds"
                )
                if iter_dir.exists():
                    # Check both 'new' and 'old' subdirectories
                    for subdir_name in ["new", "old"]:
                        subdir = iter_dir / subdir_name
                        if subdir.exists():
                            for scaffold_dir in subdir.iterdir():
                                if scaffold_dir.is_dir():
                                    scaffold_id = scaffold_dir.name
                                    all_scaffold_info[scaffold_id] = (
                                        prev_iter,
                                        scaffold_dir,
                                    )

        return all_scaffold_info

    def _get_most_recent_validation_scores(
        self, all_scaffold_info: Dict[str, Tuple[int, Path]], current_iteration: int
    ) -> Dict[str, float]:
        """Get the most recent validation scores for all scaffolds.

        Args:
            all_scaffold_info: Mapping of scaffold_id to (iteration, path)
            current_iteration: Current iteration number

        Returns:
            Dictionary mapping scaffold_id to most recent validation score (None if never validated)
        """
        most_recent_scores = {}

        # Look through all completed iterations to find most recent scores
        for scaffold_id, (scaffold_iter, scaffold_path) in all_scaffold_info.items():
            most_recent_scores[scaffold_id] = None

            # Look through all iterations after scaffold creation to find most recent validation
            # We need to look backwards from the current iteration to find the most recent

            for check_iter in range(current_iteration - 1, scaffold_iter, -1):
                train_scores, valid_scores = self.file_manager.load_scores(check_iter)
                if scaffold_id in valid_scores:
                    most_recent_scores[scaffold_id] = valid_scores[scaffold_id]
                    break

        return most_recent_scores

    def _select_top_scaffolds_smart_validation(
        self,
        iteration: int,
        all_scaffold_info: Dict[str, Tuple[int, Path]],
        most_recent_scores: Dict[str, float],
        validation_sample: List[DatasetExample],
    ) -> List[Tuple[str, int, Path]]:
        """Select top scaffolds using smart validation algorithm.

        Args:
            iteration: Current iteration number
            all_scaffold_info: Mapping of scaffold_id to (iteration, path)
            most_recent_scores: Most recent validation scores for each scaffold
            validation_sample: Validation examples to use for evaluation

        Returns:
            List of (scaffold_id, iteration, path) tuples for top scaffolds
        """
        self.current_iteration_scores = {}
        validated_scores = {}

        # Step 1: Separate scaffolds into new (from previous iteration) and historical
        new_scaffolds = []
        historical_scaffolds = []

        for scaffold_id, (scaffold_iter, scaffold_path) in all_scaffold_info.items():
            if scaffold_iter == iteration - 1:
                new_scaffolds.append(scaffold_id)
            else:
                historical_scaffolds.append(scaffold_id)

        # Step 2: Validate all new scaffolds first (they have no historical scores)
        for scaffold_id in new_scaffolds:
            score = self._evaluate_scaffold(
                iteration=iteration,
                scaffold_id=scaffold_id,
                validation_examples=validation_sample,
                source_iteration=all_scaffold_info[scaffold_id][0],
            )
            validated_scores[scaffold_id] = score
            self.current_iteration_scores[scaffold_id] = score

        # Step 3: Order all scaffolds by most recent scores (new scaffolds first since they have no historical scores)
        def get_sort_key(scaffold_id):
            if scaffold_id in validated_scores:
                return (
                    2,
                    validated_scores[scaffold_id],
                )  # New scaffolds, highest priority, ordered by current score
            elif most_recent_scores[scaffold_id] is not None:
                return (
                    1,
                    most_recent_scores[scaffold_id],
                )  # Historical scaffolds, medium priority, ordered by most recent score
            else:
                return (0, 0.0)  # Never validated scaffolds, lowest priority

        all_scaffold_ids = list(all_scaffold_info.keys())
        all_scaffold_ids.sort(key=get_sort_key, reverse=True)

        # Step 4: Smart validation - validate scaffolds as needed until top K are confirmed
        while True:
            # Get current top K scaffolds based on available scores
            def get_current_score(scaffold_id):
                if scaffold_id in validated_scores:
                    return validated_scores[scaffold_id]
                elif most_recent_scores[scaffold_id] is not None:
                    return most_recent_scores[scaffold_id]
                else:
                    return 0.0

            # Sort by current best known scores
            current_ranking = sorted(
                all_scaffold_ids, key=get_current_score, reverse=True
            )
            current_top_k = current_ranking[: self.scaffolds_per_iter]

            # Check if all top K are validated this iteration
            all_top_k_validated = all(
                scaffold_id in validated_scores for scaffold_id in current_top_k
            )

            if all_top_k_validated:
                break

            # Find next unvalidated scaffold in top K and validate it
            next_to_validate = None
            for scaffold_id in current_top_k:
                if scaffold_id not in validated_scores:
                    next_to_validate = scaffold_id
                    break

            if next_to_validate is None:
                # This shouldn't happen given the check above, but just in case
                raise RuntimeError(
                    f"All top {self.scaffolds_per_iter} scaffolds are validated this iteration"
                )

            score = self._evaluate_scaffold(
                iteration=iteration,
                scaffold_id=next_to_validate,
                validation_examples=validation_sample,
                source_iteration=all_scaffold_info[next_to_validate][0],
            )
            validated_scores[next_to_validate] = score
            self.current_iteration_scores[next_to_validate] = score

        # Create final top scaffolds list
        final_ranking = sorted(all_scaffold_ids, key=get_current_score, reverse=True)
        top_scaffolds = []
        for scaffold_id in final_ranking[: self.scaffolds_per_iter]:
            scaffold_iter, path = all_scaffold_info[scaffold_id]
            top_scaffolds.append((scaffold_id, scaffold_iter, path))
            self.logger.info(
                f"Selected scaffold {scaffold_id} (score: {get_current_score(scaffold_id):.3f}) for evolution"
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

        return current_scaffold_ids

    def _find_best_scaffold_from_scores(
        self,
        iteration: int,
        scores: Dict[str, float],
    ) -> Tuple[Optional[Path], float]:
        """Find the best scaffold from current iteration scores.

        Args:
            iteration: Current iteration number
            scores: Dictionary mapping scaffold_id to score

        Returns:
            Tuple of (best_scaffold_path, best_score) from this iteration
        """
        best_path = None
        best_score = -1.0

        for scaffold_id, score in scores.items():
            if score > best_score:
                best_score = score
                # Check if scaffold exists in current iteration, otherwise find its source iteration
                scaffold_path = self.file_manager.get_scaffold_path(
                    iteration, scaffold_id
                )
                if not scaffold_path.exists():
                    # Find the scaffold in previous iterations
                    for prev_iter in range(iteration):
                        prev_path = self.file_manager.get_scaffold_path(
                            prev_iter, scaffold_id
                        )
                        if prev_path.exists():
                            scaffold_path = prev_path
                            break
                best_path = scaffold_path

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
