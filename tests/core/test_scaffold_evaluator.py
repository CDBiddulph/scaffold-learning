import pytest
import tempfile
import json
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from scaffold_learning.core.scaffold_evaluator import ScaffoldEvaluator
from scaffold_learning.core.data_structures import (
    DatasetExample,
    ScaffoldResult,
    ScaffoldMetadata,
    ScaffoldExecutionResult,
    ScaffoldRunData,
)
from scaffold_learning.core.experiment_files import ExperimentFileManager


class TestScaffoldEvaluator:
    @pytest.fixture(autouse=True)
    def setup_temp_dir(self):
        """Automatically provide a temporary directory for each test."""
        with tempfile.TemporaryDirectory() as temp_dir:
            self.temp_dir = Path(temp_dir)
            yield

    @pytest.fixture
    def mock_file_manager(self):
        """Create a mock file manager."""
        file_manager = Mock(spec=ExperimentFileManager)
        file_manager.experiment_dir = self.temp_dir

        # Create scaffold directory structure
        scaffold_dir = self.temp_dir / "scaffolds" / "test_scaffold"
        scaffold_dir.mkdir(parents=True)
        file_manager.get_scaffold_dir.return_value = scaffold_dir

        # Mock load_scaffold to return test scaffold code
        file_manager.load_scaffold.return_value = ScaffoldResult(
            code='def process_input(input_string: str) -> str:\n    return "output"',
            metadata=ScaffoldMetadata(
                created_at="2024-01-01T00:00:00",
                parent_scaffold_id=None,
                iteration=0,
            ),
        )

        # Mock getting log paths
        file_manager.get_new_execution_log_path.side_effect = (
            lambda iteration, scaffold_id, log_type: (
                self.temp_dir / "logs" / f"{iteration}_{scaffold_id}_{log_type}.log"
            )
        )

        # Mock _get_docker_logs_dir
        file_manager._get_docker_logs_dir.side_effect = lambda iteration, scaffold_id: (
            self.temp_dir
            / "docker_logs"
            / f"iter_{iteration}"
            / f"scaffold_{scaffold_id}"
        )

        return file_manager

    @pytest.fixture
    def mock_scoring_fn(self):
        """Create a mock scoring function."""

        def scoring_function(actual_output: str, scoring_data: dict) -> float:
            # Simple scoring based on whether output matches expected
            return 1.0 if actual_output == scoring_data.get("expected", "") else 0.5

        return scoring_function

    @pytest.fixture
    def test_examples(self):
        """Create test dataset examples."""
        return [
            DatasetExample(
                id="example_1",
                input="test input 1",
                scoring_data={"expected": "output"},
            ),
            DatasetExample(
                id="example_2",
                input="test input 2",
                scoring_data={"expected": "different"},
            ),
            DatasetExample(
                id="example_3",
                input="test input 3",
                scoring_data={"expected": "output"},
            ),
        ]

    def test_evaluate_scaffold_returns_run_data(
        self, mock_file_manager, mock_scoring_fn, test_examples
    ):
        """Test that evaluate_scaffold returns a list of ScaffoldRunData."""
        evaluator = ScaffoldEvaluator(
            scoring_fn=mock_scoring_fn,
            file_manager=mock_file_manager,
            executor_model="gpt-4",
            scaffold_timeout=120,
            max_execute_workers=1,
        )

        # Mock execute_scaffolds to return successful results
        with patch(
            "scaffold_learning.core.scaffold_evaluator.execute_scaffolds"
        ) as mock_execute:
            mock_execute.return_value = [
                ScaffoldExecutionResult(
                    output="output",
                    stderr="execution log 1",
                    execution_time=1.0,
                    error_message=None,
                ),
                ScaffoldExecutionResult(
                    output="different",
                    stderr="execution log 2",
                    execution_time=1.5,
                    error_message=None,
                ),
                ScaffoldExecutionResult(
                    output="output",
                    stderr="execution log 3",
                    execution_time=1.2,
                    error_message=None,
                ),
            ]

            # Execute evaluation
            run_data = evaluator.evaluate_scaffold(
                iteration=0,
                scaffold_id="test_scaffold",
                examples=test_examples,
                log_type="train",
            )

        # Verify the result
        assert len(run_data) == 3
        assert all(isinstance(rd, ScaffoldRunData) for rd in run_data)

        # Check first result
        assert (
            run_data[0].code
            == 'def process_input(input_string: str) -> str:\n    return "output"'
        )
        assert run_data[0].execution_log == "execution log 1"
        assert run_data[0].example == test_examples[0]
        assert run_data[0].actual_output == "output"
        assert run_data[0].score == 1.0  # Matches expected

        # Check second result
        assert run_data[1].score == 1.0  # Output matches expected "different"

        # Check third result
        assert run_data[2].score == 1.0  # Matches expected

    def test_evaluate_scaffold_handles_execution_errors(
        self, mock_file_manager, mock_scoring_fn, test_examples
    ):
        """Test that evaluate_scaffold handles execution errors correctly."""
        evaluator = ScaffoldEvaluator(
            scoring_fn=mock_scoring_fn,
            file_manager=mock_file_manager,
            executor_model="gpt-4",
            scaffold_timeout=120,
            max_execute_workers=1,
        )

        # Mock execute_scaffolds to return one error
        with patch(
            "scaffold_learning.core.scaffold_evaluator.execute_scaffolds"
        ) as mock_execute:
            mock_execute.return_value = [
                ScaffoldExecutionResult(
                    output="output",
                    stderr="execution log 1",
                    execution_time=1.0,
                    error_message=None,
                ),
                ScaffoldExecutionResult(
                    output="",
                    stderr="error log",
                    execution_time=0.5,
                    error_message="Execution failed: timeout",
                ),
                ScaffoldExecutionResult(
                    output="output",
                    stderr="execution log 3",
                    execution_time=1.2,
                    error_message=None,
                ),
            ]

            # Execute evaluation
            run_data = evaluator.evaluate_scaffold(
                iteration=1,
                scaffold_id="test_scaffold",
                examples=test_examples,
                log_type="valid",
            )

        # Verify results
        assert len(run_data) == 3

        # First and third should have normal scores
        assert run_data[0].score == 1.0
        assert run_data[2].score == 1.0

        # Second should have score of 0 due to error
        assert run_data[1].score == 0.0
        assert run_data[1].actual_output == ""

    def test_evaluate_scaffold_saves_scores_and_results(
        self, mock_file_manager, mock_scoring_fn, test_examples
    ):
        """Test that evaluate_scaffold saves scores and detailed results."""
        evaluator = ScaffoldEvaluator(
            scoring_fn=mock_scoring_fn,
            file_manager=mock_file_manager,
            executor_model="gpt-4",
            scaffold_timeout=120,
            max_execute_workers=2,
        )

        with patch(
            "scaffold_learning.core.scaffold_evaluator.execute_scaffolds"
        ) as mock_execute:
            mock_execute.return_value = [
                ScaffoldExecutionResult(
                    output="output",
                    stderr="log",
                    execution_time=1.0,
                    error_message=None,
                )
                for _ in test_examples
            ]

            # Execute evaluation
            run_data = evaluator.evaluate_scaffold(
                iteration=0,
                scaffold_id="scaffold_1",
                examples=test_examples,
                log_type="train",
            )

        # Verify that save_scores was called (not for test log_type)
        mock_file_manager.save_scores.assert_called_once_with(
            0, "scaffold_1", [1.0, 0.5, 1.0], "train"
        )

    def test_evaluate_scaffold_test_type_no_save_scores(
        self, mock_file_manager, mock_scoring_fn, test_examples
    ):
        """Test that evaluate_scaffold doesn't call save_scores for test log_type."""
        evaluator = ScaffoldEvaluator(
            scoring_fn=mock_scoring_fn,
            file_manager=mock_file_manager,
            executor_model="gpt-4",
            scaffold_timeout=120,
            max_execute_workers=1,
        )

        with patch(
            "scaffold_learning.core.scaffold_evaluator.execute_scaffolds"
        ) as mock_execute:
            mock_execute.return_value = [
                ScaffoldExecutionResult(
                    output="output",
                    stderr="log",
                    execution_time=1.0,
                    error_message=None,
                )
                for _ in test_examples
            ]

            # Execute evaluation with test log_type
            run_data = evaluator.evaluate_scaffold(
                iteration="test",
                scaffold_id="best_scaffold",
                examples=test_examples,
                log_type="test",
            )

        # Verify that save_scores was NOT called for test type
        mock_file_manager.save_scores.assert_not_called()

    def test_evaluate_scaffold_parallel_execution(
        self, mock_file_manager, mock_scoring_fn, test_examples
    ):
        """Test that evaluate_scaffold uses max_execute_workers for parallel execution."""
        evaluator = ScaffoldEvaluator(
            scoring_fn=mock_scoring_fn,
            file_manager=mock_file_manager,
            executor_model="gpt-4",
            scaffold_timeout=120,
            max_execute_workers=4,  # Set parallel workers
        )

        with patch(
            "scaffold_learning.core.scaffold_evaluator.execute_scaffolds"
        ) as mock_execute:
            mock_execute.return_value = [
                ScaffoldExecutionResult(
                    output="output",
                    stderr="log",
                    execution_time=1.0,
                    error_message=None,
                )
                for _ in test_examples
            ]

            # Execute evaluation
            run_data = evaluator.evaluate_scaffold(
                iteration=2,
                scaffold_id="parallel_scaffold",
                examples=test_examples,
                log_type="valid",
            )

            # Verify execute_scaffolds was called with correct max_workers
            mock_execute.assert_called_once()
            call_kwargs = mock_execute.call_args[1]
            assert call_kwargs["max_workers"] == 4

    def test_evaluate_scaffold_creates_proper_execution_tasks(
        self, mock_file_manager, mock_scoring_fn, test_examples
    ):
        """Test that evaluate_scaffold creates proper ScaffoldExecutionTask objects."""
        evaluator = ScaffoldEvaluator(
            scoring_fn=mock_scoring_fn,
            file_manager=mock_file_manager,
            executor_model="claude-3",
            scaffold_timeout=60,
            max_execute_workers=1,
        )

        with patch(
            "scaffold_learning.core.scaffold_evaluator.execute_scaffolds"
        ) as mock_execute:
            mock_execute.return_value = [
                ScaffoldExecutionResult(
                    output="output",
                    stderr="log",
                    execution_time=1.0,
                    error_message=None,
                )
                for _ in test_examples
            ]

            # Execute evaluation
            run_data = evaluator.evaluate_scaffold(
                iteration=0,
                scaffold_id="task_test",
                examples=test_examples,
                log_type="train",
            )

            # Check the tasks that were created
            call_args = mock_execute.call_args[0]
            tasks = call_args[0]

            assert len(tasks) == 3
            for i, task in enumerate(tasks):
                assert task.input_string == test_examples[i].input
                assert task.model_spec == "claude-3"
                assert task.timeout == 60
                assert task.console_output == False
                assert task.reasoning_effort == "minimal"
