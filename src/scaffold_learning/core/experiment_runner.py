import numpy as np
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Callable, Tuple, Any
from collections import defaultdict
import concurrent.futures
import io
import contextlib
from scaffold_learning.core.data_structures import (
    DatasetExample,
    ScaffoldRunData,
    ScaffoldExecutionTask,
)
from scaffold_learning.core.data_structures import ScaffolderPromptConfig
from scaffold_learning.core.strategy_generation import generate_strategies
from scaffold_learning.core.llm_interfaces import LLMInterface
from scaffold_learning.core.experiment_files import ExperimentFileManager
from scaffold_learning.core.scaffold_generation import (
    generate_scaffold,
    evolve_scaffold,
)
from scaffold_learning.core.scaffold_execution import (
    execute_scaffolds,
    ScaffoldExecutionResult,
)
from scaffold_learning.core.dataset_utils import ExampleSampler
from scaffold_learning.core.hydra_config import ExperimentConfig


class ExperimentRunner:
    """Orchestrates scaffold learning experiments."""

    def __init__(
        self,
        config: ExperimentConfig,
        data: Dict[str, List[DatasetExample]],
        scoring_fn: Callable[[str, Dict], float],
        scaffolder_llm: LLMInterface,
        output_dir: Path,
        strategy_llm: Optional[LLMInterface] = None,
        scoring_fn_code: Optional[str] = None,
    ):
        """Initialize an experiment runner with structured configuration.

        Args:
            config: Experiment configuration
            data: Dictionary with 'train' and 'valid' dataset splits
            scoring_fn: Function that takes (expected, scoring_data) and returns score 0-1
            scaffolder_llm: LLM to use for generating/improving scaffolds
            output_dir: Directory for experiment outputs
            strategy_llm: Optional LLM interface for strategy generation
            scoring_fn_code: Optional scoring function code to include in prompts
        """
        self.config = config
        self.training_data = data["train"]
        self.validation_data = data["valid"]
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

        # Set up experiment directory - use Hydra's output directory
        self.file_manager = ExperimentFileManager(output_dir)

        # Initialize scaffold ID tracking
        self.scaffold_counters = {}  # parent_id -> next_counter
        self.next_initial_id = 0

        # Set up logging
        self.logger = logging.getLogger(__name__)

        # Save experiment metadata
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        metadata = {
            "experiment_name": config.experiment_name,
            "created_at": timestamp,
            "num_iterations": config.num_iterations,
            "scaffolds_per_iter": config.scaffolds_per_iter,
            "initial_scaffolds": config.initial_scaffolds,
            "num_training_examples": config.num_training_examples,
            "num_validation_examples": config.num_validation_examples,
            "train_seed": config.train_seed,
            "valid_seed": config.valid_seed,
            "scaffold_timeout": config.scaffold_timeout,
        }
        self.file_manager.save_experiment_metadata(metadata)

        self.logger.info(f"Initialized experiment: {config.experiment_name}")
        self.logger.info(f"Random training seed: {config.train_seed}")
        self.logger.info(f"Random validation seed: {config.valid_seed}")

    def run(self) -> Tuple[Optional[str], float]:
        """Run the complete experiment.

        Creates initial scaffolds, runs iterations of evaluation and evolution,
        and returns the best performing scaffold.

        Returns:
            Tuple of (best_scaffold_id, best_score)
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

        # Run iterations
        for iteration in range(self.config.num_iterations):
            self.logger.info(f"Starting iteration {iteration}")

            if iteration == 0:
                # Create and validate initial scaffolds
                validation_scores = self._run_initial_iteration(validation_sample)
            else:
                # Run normal evolution iteration
                validation_scores = self._run_evolution_iteration(
                    iteration, validation_sample
                )

            # Find best scaffold from current iteration scores
            if validation_scores:
                iter_best_scaffold_id, iter_best_score = (
                    self._find_best_scaffold_from_scores(iteration, validation_scores)
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
        return best_scaffold_id, best_score

    def _run_evolution_iteration(
        self,
        iteration: int,
        validation_sample: List[DatasetExample],
    ) -> Dict[str, List[float]]:
        """Run one iteration of scaffold evolution.

        Args:
            iteration: Current iteration number
            validation_sample: Validation examples to use for evaluation

        Returns:
            A dictionary mapping scaffold_id to a list of scores
        """
        # Select top scaffolds to evolve (using pre-computed scores)
        top_scaffold_ids = self._select_top_scaffolds()

        # Run training examples for top scaffolds
        top_scaffold_runs = self._run_training(
            iteration=iteration,
            scaffold_ids=top_scaffold_ids,
        )

        # Evolve selected scaffolds and get new scaffold IDs
        new_scaffold_ids = self._evolve_scaffolds(iteration, top_scaffold_runs)

        validation_scores = self._validate_scaffolds(
            iteration, new_scaffold_ids, validation_sample
        )

        return validation_scores

    def _run_initial_iteration(
        self, validation_sample: List[DatasetExample]
    ) -> Dict[str, List[float]]:
        """Run iteration 0: create and validate initial scaffolds.

        Args:
            validation_sample: Validation examples to use for evaluation

        Returns:
            A dictionary mapping scaffold_id to a list of scores
        """
        scaffold_ids = self._create_initial_scaffolds()
        validation_scores = self._validate_scaffolds(0, scaffold_ids, validation_sample)
        return validation_scores

    def _validate_scaffolds(
        self,
        iteration: int,
        scaffold_ids: List[str],
        validation_sample: List[DatasetExample],
        max_workers: Optional[int] = None,
    ) -> Dict[str, List[float]]:
        """Validate a list of scaffolds and return their scores.

        Args:
            iteration: Current iteration number
            scaffold_ids: List of scaffold IDs to validate
            validation_sample: Validation examples to use
            max_workers: Maximum workers for parallel scaffold execution.
                If None, uses self.max_execute_workers

        Returns:
            Dictionary mapping scaffold_id to list of validation scores
        """
        if max_workers is None:
            max_workers = self.config.max_execute_workers

        validation_scores = {}
        for scaffold_id in scaffold_ids:
            scores = self._run_scaffold_on_examples(
                iteration,
                scaffold_id,
                validation_sample,
                "valid",
                max_workers=max_workers,
            )
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

        # Create evolution tasks
        generation_tasks = []
        for parent_id, run_data_list in top_scaffold_runs.items():
            new_scaffold_id = self._get_next_scaffold_id(parent_id)
            current_scaffold_ids.append(new_scaffold_id)

            def evolve_func(
                run_data_list=run_data_list, parent_id=parent_id
            ):  # Capture by value
                config = ScaffolderPromptConfig(
                    evolve_examples=run_data_list,
                    scoring_fn_code=self.scoring_fn_code,
                    suggest_hack=self.config.suggest_hack,
                    domain=self.config.domain,
                )
                return evolve_scaffold(
                    config=config,
                    scaffolder_llm=self.scaffolder_llm,
                    iteration=iteration,
                    parent_scaffold_id=parent_id,
                )

            generation_tasks.append((new_scaffold_id, evolve_func))

        # Execute the evolution tasks
        self._execute_scaffold_generation_batch(
            generation_tasks, "evolved", self.config.max_generate_workers
        )

        return current_scaffold_ids

    def _find_best_scaffold_from_scores(
        self,
        iteration: int,
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

    def _execute_scaffold_generation_batch(
        self,
        generation_tasks: List[Tuple[str, Callable]],
        scaffold_type: str,
        max_workers: int,
        strategies: Optional[List[Optional[str]]] = None,
    ) -> None:
        """Execute a batch of scaffold generation tasks using ThreadPoolExecutor.

        Args:
            generation_tasks: List of (scaffold_id, generation_function) tuples
            scaffold_type: Type of scaffold (e.g., "initial", "evolved"), used for logging
            max_workers: Maximum workers for parallel execution (1 for sequential)
            strategies: Optional list of strategies corresponding to each task (for initial scaffolds)
        """
        total_tasks = len(generation_tasks)

        if max_workers > 1:
            self.logger.info(
                f"Creating {total_tasks} {scaffold_type} scaffolds (up to {max_workers} in parallel)"
            )
        else:
            self.logger.info(f"Creating {total_tasks} {scaffold_type} scaffolds")

        completed = 0
        # Create mapping from scaffold_id to strategy
        strategy_map = {}
        if strategies:
            for i, (scaffold_id, _) in enumerate(generation_tasks):
                if i < len(strategies):
                    strategy_map[scaffold_id] = strategies[i]

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_id = {
                executor.submit(generation_func): scaffold_id
                for scaffold_id, generation_func in generation_tasks
            }

            for future in concurrent.futures.as_completed(future_to_id):
                scaffold_id = future_to_id[future]
                try:
                    result = future.result()
                    self.file_manager.save_scaffold(
                        scaffold_id=scaffold_id, result=result
                    )
                    completed += 1
                    log_message = f"Created {scaffold_type} scaffold {scaffold_id}"
                    if max_workers > 1:
                        log_message += f" ({completed}/{total_tasks})"
                    self.logger.info(log_message)
                except Exception as e:
                    self.logger.error(
                        f"Failed to create {scaffold_type} scaffold {scaffold_id}: {e}"
                    )
                    raise

    def _generate_strategies(
        self, base_prompt_kwargs: Dict[str, Any]
    ) -> List[Optional[str]]:
        """Generate strategies if strategy model is specified.

        Args:
            base_prompt_kwargs: Base prompt kwargs to use for strategy generation

        Returns:
            List of strategies, or list of None if no strategy model is specified
        """
        if not self.strategy_llm:
            return [None] * self.config.initial_scaffolds

        self.logger.info(
            f"Generating {self.config.initial_scaffolds} strategies using {self.strategy_llm.get_model_info()}"
        )

        # Get a single list of training examples for the strategy generation prompt
        examples = next(iter(self._get_training_examples([""]).values()))

        strategy_config = ScaffolderPromptConfig(
            **base_prompt_kwargs,
            generate_examples=examples,
        )

        # Generate strategies in batches
        all_strategies = []
        batch_size = self.config.strategy_batch_size or self.config.initial_scaffolds
        num_batches = self.config.initial_scaffolds // batch_size

        for batch_idx in range(num_batches):
            if num_batches > 1:
                self.logger.info(
                    f"Generating strategy batch {batch_idx + 1}/{num_batches}"
                )

            batch_strategies = generate_strategies(
                llm=self.strategy_llm,
                scaffolder_prompt_config=strategy_config,
                num_strategies=batch_size,
            )
            all_strategies.extend(batch_strategies)

        return all_strategies

    def _create_initial_scaffolds(self) -> List[str]:
        """Create initial scaffolds using random training examples.

        Returns:
            List of scaffold IDs created
        """
        # This will end up just being ["0", "1", "2", ...]
        scaffold_ids = [
            self._get_next_scaffold_id() for _ in range(self.config.initial_scaffolds)
        ]

        # Get all training examples upfront
        examples_by_scaffold = self._get_training_examples(scaffold_ids)

        base_prompt_kwargs = {
            "scoring_fn_code": self.scoring_fn_code,
            "suggest_hack": self.config.suggest_hack,
            "domain": self.config.domain,
        }

        # Generate strategies (possibly None)
        strategies = self._generate_strategies(base_prompt_kwargs)

        # Create generation tasks
        generation_tasks = []
        for (scaffold_id, examples), strategy in zip(
            examples_by_scaffold.items(), strategies
        ):

            def generate_func(
                examples=examples,
                strategy=strategy,
            ):  # Capture examples and strategy by value using default parameter
                config = ScaffolderPromptConfig(
                    **base_prompt_kwargs,
                    generate_examples=examples,
                    strategy=strategy,
                )
                return generate_scaffold(
                    config=config,
                    scaffolder_llm=self.scaffolder_llm,
                    iteration=0,
                )

            generation_tasks.append((scaffold_id, generate_func))

        # Execute the generation tasks
        self._execute_scaffold_generation_batch(
            generation_tasks, "initial", self.config.max_generate_workers
        )

        return scaffold_ids

    def _log_scaffold_scores(
        self, scaffold_id: str, scores: List[float], log_type: str
    ) -> None:
        """Log scaffold scores with proper formatting."""
        log_type_str = "validation" if log_type == "valid" else "training"
        scores_str = ", ".join(f"{s:.3f}" for s in scores)
        if len(scores) > 1:
            maybe_s, average_str = "s", f" (avg {np.mean(scores):.3f})"
        else:
            maybe_s, average_str = "", ""
        self.logger.info(
            f"Scaffold {scaffold_id} {log_type_str} score{maybe_s}: {scores_str}{average_str}"
        )

    def _prepare_execution_tasks(
        self,
        iteration: int,
        scaffold_id: str,
        examples: List[DatasetExample],
        log_type: str,
    ) -> List[ScaffoldExecutionTask]:
        """Create ScaffoldExecutionTask objects for a list of examples.

        Args:
            iteration: Current iteration number (where to save logs)
            scaffold_id: ID of scaffold to run
            examples: Examples to test the scaffold on
            log_type: Type of log ("train" or "valid")

        Returns:
            List of ScaffoldExecutionTask objects
        """
        tasks = []
        for example in examples:
            task = ScaffoldExecutionTask(
                scaffold_dir=str(self.file_manager.get_scaffold_dir(scaffold_id)),
                log_file_path=str(
                    self.file_manager.get_new_execution_log_path(
                        iteration, scaffold_id, log_type
                    )
                ),
                input_string=example.input,
                model_spec=self.config.executor,
                timeout=self.config.scaffold_timeout,
                console_output=False,
                thinking_budget_tokens=0,
            )
            tasks.append(task)
        return tasks

    @contextlib.contextmanager
    def _capture_logging(self, output_stream):
        """Temporarily capture all logging to the given stream."""
        log_handler = logging.StreamHandler(output_stream)
        log_handler.setLevel(logging.INFO)
        root_logger = logging.getLogger()
        original_handlers = root_logger.handlers[:]
        original_level = root_logger.level

        # Remove all existing handlers and add only our capture handler
        for handler in original_handlers:
            root_logger.removeHandler(handler)
        root_logger.addHandler(log_handler)
        root_logger.setLevel(logging.INFO)

        try:
            yield
        finally:
            # Restore original handlers and level
            root_logger.removeHandler(log_handler)
            for handler in original_handlers:
                root_logger.addHandler(handler)
            root_logger.setLevel(original_level)

    def _write_score_to_log(
        self, log_file_path: str, score_output: str, score: float
    ) -> None:
        """Write score to the log file."""
        # TODO: consider sharing this code with make_and_run.py.
        with open(log_file_path, "a") as f:
            f.write("\n=== SCORE ===\n")
            if score_output:
                f.write(score_output)
                if not score_output.endswith("\n"):
                    f.write("\n")
            f.write(f"Final score: {score}\n")

    def _process_execution_results(
        self,
        scaffold_id: str,
        examples: List[DatasetExample],
        execution_results: List[ScaffoldExecutionResult],
        log_file_paths: List[str],
        run_data_list: Optional[List[ScaffoldRunData]] = None,
        scaffold_code: Optional[str] = None,
    ) -> List[float]:
        """Score execution results and optionally create ScaffoldRunData.

        Args:
            scaffold_id: ID of scaffold that was executed
            examples: Examples that were tested
            execution_results: Results from scaffold execution
            log_file_paths: List of log file paths to append scoring info to
            run_data_list: Optional list to append ScaffoldRunData to
            scaffold_code: Required if run_data_list is provided

        Returns:
            List of scores in order of examples
        """
        scores = []
        for example, result, log_file_path in zip(
            examples, execution_results, log_file_paths, strict=True
        ):
            # Capture scoring output
            score_output = io.StringIO()

            # Calculate score with output capture
            if result.error_message is None:
                with self._capture_logging(score_output):
                    score = self.scoring_fn(result.output, example.scoring_data)
            else:
                logging.warning(
                    f"Scaffold {scaffold_id} failed to execute: {result.error_message}"
                )
                score = 0.0  # Failed execution gets 0 score

            scores.append(score)

            self._write_score_to_log(log_file_path, score_output.getvalue(), score)

            # For training, create ScaffoldRunData
            if run_data_list is not None:
                if scaffold_code is None:
                    raise ValueError("Scaffold code is required for ScaffoldRunData")
                run_data_list.append(
                    ScaffoldRunData(
                        code=scaffold_code,
                        execution_log=result.stderr,
                        example=example,
                        actual_output=result.output,
                        score=score,
                    )
                )

        return scores

    def _run_scaffold_on_examples(
        self,
        iteration: int,
        scaffold_id: str,
        examples: List[DatasetExample],
        log_type: str,
        run_data_list: Optional[List[ScaffoldRunData]] = None,
        scaffold_code: Optional[str] = None,
        max_workers: int = 1,
    ) -> List[float]:
        """Run a scaffold on examples and return scores and run data.

        Args:
            iteration: Current iteration number (where to save logs)
            scaffold_id: ID of scaffold to run
            examples: Examples to test the scaffold on
            log_type: Type of log ("train" or "valid")
            run_data_list: List of ScaffoldRunData to append to. Requires scaffold_code.
            scaffold_code: Scaffold code to use for ScaffoldRunData.
            max_workers: Maximum workers for parallel execution of examples

        Returns:
            A list of scores, in order of examples
        """
        # Prepare execution tasks
        tasks = self._prepare_execution_tasks(
            iteration, scaffold_id, examples, log_type
        )

        # Execute all tasks
        execution_results = execute_scaffolds(tasks, max_workers=max_workers)

        # Extract log file paths from tasks for scoring append
        log_file_paths = [task.log_file_path for task in tasks]

        # Process results and calculate scores
        scores = self._process_execution_results(
            scaffold_id,
            examples,
            execution_results,
            log_file_paths,
            run_data_list,
            scaffold_code,
        )

        # Log scores
        self._log_scaffold_scores(scaffold_id, scores, log_type)
        self.file_manager.save_scores(iteration, scaffold_id, scores, log_type)

        return scores

    def _get_training_examples(
        self, scaffold_ids: List[str]
    ) -> Dict[str, List[DatasetExample]]:
        """Sample training examples using the stateful train_sampler."""
        examples_by_scaffold = {}
        for scaffold_id in scaffold_ids:
            examples_by_scaffold[scaffold_id] = self.train_sampler.sample(
                self.config.num_training_examples
            )
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
                max_workers=self.config.max_execute_workers,
            )

        return training_runs
