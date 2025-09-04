import io
import json
import logging
import contextlib
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Callable, Union, Any
from scaffold_learning.core.data_structures import (
    DatasetExample,
    ScaffoldRunData,
    ScaffoldExecutionTask,
    ScaffoldExecutionResult,
)
from scaffold_learning.core.experiment_files import ExperimentFileManager
from scaffold_learning.core.scaffold_execution import execute_scaffolds


class ScaffoldEvaluator:
    """Handles execution and evaluation of scaffolds on dataset examples."""

    def __init__(
        self,
        scoring_fn: Callable[[str, Dict], float],
        file_manager: ExperimentFileManager,
        executor_model: str,
        scaffold_timeout: int,
        max_execute_workers: int,
        executor_reasoning_effort: str = "minimal",
    ):
        """Initialize the scaffold evaluator.

        Args:
            scoring_fn: Function that takes (expected, scoring_data) and returns score 0-1
            file_manager: Manager for experiment file operations and scaffold loading
            executor_model: Model specification for executor LLM
            scaffold_timeout: Timeout in seconds for scaffold execution
            max_execute_workers: Max workers for parallel execution
            executor_reasoning_effort: Reasoning effort level for executor LLM
        """
        self.scoring_fn = scoring_fn
        self.file_manager = file_manager
        self.executor_model = executor_model
        self.scaffold_timeout = scaffold_timeout
        self.max_execute_workers = max_execute_workers
        self.executor_reasoning_effort = executor_reasoning_effort
        self.logger = logging.getLogger(__name__)

    def evaluate_scaffold(
        self,
        iteration: Union[int, str],
        scaffold_id: str,
        examples: List[DatasetExample],
        log_type: str,
    ) -> List[ScaffoldRunData]:
        """Execute a scaffold on examples and return run data with scores.

        Args:
            iteration: Current iteration number or "test" for test runs
            scaffold_id: ID of scaffold to run
            examples: Examples to test the scaffold on
            log_type: Type of log ("train", "valid", or "test")

        Returns:
            List of ScaffoldRunData objects containing results and scores
        """
        # Load scaffold code from file manager
        scaffold_result = self.file_manager.load_scaffold(scaffold_id)
        scaffold_code = scaffold_result.code

        # Prepare execution tasks
        tasks = self._prepare_execution_tasks(
            iteration, scaffold_id, examples, log_type
        )

        # Execute all tasks
        execution_results = execute_scaffolds(
            tasks, max_workers=self.max_execute_workers
        )

        # Extract log file paths from tasks for scoring append
        log_file_paths = [task.log_file_path for task in tasks]

        # Process results and create ScaffoldRunData
        run_data = self._process_execution_results(
            scaffold_id, examples, execution_results, log_file_paths, scaffold_code
        )

        # Extract scores for logging and saving
        scores = [rd.score for rd in run_data]

        # Log scores
        self._log_scaffold_scores(scaffold_id, scores, log_type)

        # Save scores to scoring files (test scores are handled by _save_detailed_results)
        if log_type != "test":
            self.file_manager.save_scores(iteration, scaffold_id, scores, log_type)

        # Create and save detailed results.json
        self._save_detailed_results(
            iteration, scaffold_id, log_type, examples, execution_results, scores, tasks
        )

        return run_data

    def _prepare_execution_tasks(
        self,
        iteration: Union[int, str],
        scaffold_id: str,
        examples: List[DatasetExample],
        log_type: str,
    ) -> List[ScaffoldExecutionTask]:
        """Create ScaffoldExecutionTask objects for a list of examples.

        Args:
            iteration: Current iteration number or "test" for test runs
            scaffold_id: ID of scaffold to run
            examples: Examples to test the scaffold on
            log_type: Type of log ("train", "valid", or "test")

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
                model_spec=self.executor_model,
                timeout=self.scaffold_timeout,
                console_output=False,
                reasoning_effort=self.executor_reasoning_effort,
            )
            tasks.append(task)
        return tasks

    def _process_execution_results(
        self,
        scaffold_id: str,
        examples: List[DatasetExample],
        execution_results: List[ScaffoldExecutionResult],
        log_file_paths: List[str],
        scaffold_code: str,
    ) -> List[ScaffoldRunData]:
        """Score execution results and create ScaffoldRunData.

        Args:
            scaffold_id: ID of scaffold that was executed
            examples: Examples that were tested
            execution_results: Results from scaffold execution
            log_file_paths: List of log file paths to append scoring info to
            scaffold_code: Scaffold code for ScaffoldRunData

        Returns:
            List of ScaffoldRunData objects with scores
        """
        run_data = []
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

            self._write_score_to_log(log_file_path, score_output.getvalue(), score)

            # Create ScaffoldRunData
            run_data.append(
                ScaffoldRunData(
                    code=scaffold_code,
                    execution_log=result.stderr,
                    example=example,
                    actual_output=result.output,
                    score=score,
                )
            )

        return run_data

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
        # Ensure parent directory exists
        log_path = Path(log_file_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        with open(log_file_path, "a") as f:
            f.write("\n=== SCORE ===\n")
            if score_output:
                f.write(score_output)
                if not score_output.endswith("\n"):
                    f.write("\n")
            f.write(f"Final score: {score}\n")

    def _log_scaffold_scores(
        self, scaffold_id: str, scores: List[float], log_type: str
    ) -> None:
        """Log scaffold scores with proper formatting."""
        log_type_str = (
            "validation"
            if log_type == "valid"
            else "training" if log_type == "train" else "test"
        )
        scores_str = ", ".join(f"{s:.3f}" for s in scores)
        if len(scores) > 1:
            maybe_s, average_str = "s", f" (avg {np.mean(scores):.3f})"
        else:
            maybe_s, average_str = "", ""
        self.logger.info(
            f"Scaffold {scaffold_id} {log_type_str} score{maybe_s}: {scores_str}{average_str}"
        )

    def _save_detailed_results(
        self,
        iteration: Union[int, str],
        scaffold_id: str,
        log_type: str,
        examples: List[DatasetExample],
        execution_results: List[ScaffoldExecutionResult],
        scores: List[float],
        tasks: List[ScaffoldExecutionTask],
    ) -> None:
        """Save detailed results.json file for a scaffold run.

        Args:
            iteration: Current iteration number or "test" for test runs
            scaffold_id: Scaffold identifier
            log_type: Type of run ("train", "valid", or "test")
            examples: Examples that were tested
            execution_results: Results from scaffold execution
            scores: Calculated scores
            tasks: Original execution tasks
        """
        # Create results directory
        logs_dir = self.file_manager._get_docker_logs_dir(iteration, scaffold_id)
        results_dir = logs_dir
        results_dir.mkdir(parents=True, exist_ok=True)

        # Build results structure similar to make_and_run.py
        results = {
            "scaffold_id": scaffold_id,
            "iteration": iteration,
            "log_type": log_type,
            "executor_model": self.executor_model,
            "timestamp": datetime.now().isoformat(),
            "mode": "evaluation",
            "num_examples": len(examples),
            "scores": scores,
            "mean_score": float(np.mean(scores)),
            "std_score": float(np.std(scores)),
            "execution_times": [r.execution_time for r in execution_results],
            "mean_execution_time": float(
                np.mean([r.execution_time for r in execution_results])
            ),
            "outputs": [],
        }

        # Add individual outputs
        for example, result, score in zip(examples, execution_results, scores):
            output_info = {
                "example_id": example.id,
                "score": score,
                "output": result.output,
                "error": result.error_message,
                "execution_time": result.execution_time,
            }
            results["outputs"].append(output_info)

        # Save results.json with run type prefix
        results_path = results_dir / f"{log_type}_results.json"
        with open(results_path, "w") as f:
            json.dump(results, f, indent=2)

        # For test runs, also save a summary to scoring/test.json
        if log_type == "test":
            self._save_test_summary_to_scoring(results)

    def _save_test_summary_to_scoring(self, detailed_results: Dict[str, Any]) -> None:
        """Save a test summary to scoring/test.json from detailed results.

        Args:
            detailed_results: The full results dict from _save_detailed_results
        """
        # Create test summary by extracting subset of fields
        test_summary = {
            "scaffold_id": detailed_results["scaffold_id"],
            "mode": "test_evaluation",
            "num_examples": detailed_results["num_examples"],
            "scores": detailed_results["scores"],
            "mean_score": detailed_results["mean_score"],
            "std_score": detailed_results["std_score"],
            "timestamp": detailed_results["timestamp"],
        }

        # Save to scoring/test.json
        scoring_dir = self.file_manager.experiment_dir / "scoring"
        scoring_dir.mkdir(parents=True, exist_ok=True)
        test_file = scoring_dir / "test.json"
        with open(test_file, "w") as f:
            import json

            json.dump(test_summary, f, indent=2)
