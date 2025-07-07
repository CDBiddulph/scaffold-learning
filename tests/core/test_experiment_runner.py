import pytest
import tempfile
from unittest.mock import Mock, patch
from pathlib import Path
from scaffold_learning.core.experiment_runner import ExperimentRunner
from scaffold_learning.core.data_structures import (
    DatasetExample,
    ScaffoldResult,
    ScaffoldMetadata,
    ScaffoldExecutionResult,
)
from scaffold_learning.core.llm_interfaces import LLMInterface


class TestExperimentRunner:
    @pytest.fixture(autouse=True)
    def setup_temp_dir(self):
        """Automatically provide a temporary directory for each test."""
        with tempfile.TemporaryDirectory() as temp_dir:
            self.temp_dir = temp_dir
            yield

    def create_test_data(self):
        """Create test training and validation data."""
        training_data = [
            DatasetExample(
                id="train_1",
                input="5 across: Large feline (4)",
                scoring_data={"solution": "LION"},
            ),
            DatasetExample(
                id="train_2",
                input="1 down: Flying mammal (3)",
                scoring_data={"solution": "BAT"},
            ),
        ]

        validation_data = [
            DatasetExample(
                id="valid_1",
                input="3 across: Ocean (3)",
                scoring_data={"solution": "SEA"},
            ),
            DatasetExample(
                id="valid_2",
                input="2 down: Canine (3)",
                scoring_data={"solution": "DOG"},
            ),
            DatasetExample(
                id="valid_3",
                input="4 across: Feline (3)",
                scoring_data={"solution": "CAT"},
            ),
        ]

        return training_data, validation_data

    def create_mock_scoring_function(self):
        """Create a mock scoring function."""

        def scoring_function(expected: str, scoring_data: dict) -> float:
            actual = scoring_data.get("solution", "")
            return 1.0 if actual == expected else 0.0

        return scoring_function

    def create_experiment_runner(
        self,
        num_iterations=1,
        scaffolds_per_iter=2,
        initial_scaffolds=3,
        num_validation_examples=2,
        experiment_name="test_experiment",
    ):
        """Factory method to create ExperimentRunner with common defaults."""
        training_data, validation_data = self.create_test_data()
        scoring_function = self.create_mock_scoring_function()
        mock_llm = Mock(spec=LLMInterface)

        return ExperimentRunner(
            experiment_name=experiment_name,
            training_data=training_data,
            validation_data=validation_data,
            scoring_function=scoring_function,
            scaffolder_llm=mock_llm,
            num_iterations=num_iterations,
            scaffolds_per_iter=scaffolds_per_iter,
            initial_scaffolds=initial_scaffolds,
            num_validation_examples=num_validation_examples,
            base_dir=Path(self.temp_dir),
        )

    def create_mock_scaffold_result(
        self, code="def process_input(s): return 'test'", iteration=0
    ):
        """Factory method for creating mock ScaffoldResult objects."""
        return ScaffoldResult(
            code=code,
            metadata=ScaffoldMetadata(
                created_at="2024-01-01T00:00:00",
                model="mock",
                parent_scaffold_id=None,
                iteration=iteration,
            ),
        )

    def create_mock_execution_result(self, output="SEA", exit_code=0):
        """Factory method for creating mock ScaffoldExecutionResult objects."""
        return ScaffoldExecutionResult(
            output=output, stderr="", exit_code=exit_code, execution_time=1.0
        )

    def create_mock_execute_function(self):
        """Create a mock execute_scaffold function that creates log files."""

        def mock_execute(scaffold_dir, input_string, model, logs_path, timeout=120):
            # Create a simple log file
            logs_path.parent.mkdir(parents=True, exist_ok=True)
            with open(logs_path, "w") as f:
                f.write("=== Scaffold Execution Log ===\n")
                f.write(f"Model: {model}\n")
                f.write(f"Input: {input_string}\n")
                f.write("Output: SEA\n")
            return ScaffoldExecutionResult(
                output="SEA", stderr="", exit_code=0, execution_time=0.1
            )

        return mock_execute

    def test_experiment_runner_init(self):
        runner = self.create_experiment_runner(num_iterations=2)

        assert runner.experiment_name == "test_experiment"
        assert len(runner.training_data) == 2
        assert len(runner.validation_data) == 3
        assert runner.num_iterations == 2
        assert runner.scaffolds_per_iter == 2
        assert runner.initial_scaffolds == 3
        assert runner.executor_model == "gpt-4"  # Default value

    def test_validation_parameter_check(self):
        training_data, validation_data = self.create_test_data()
        scoring_function = self.create_mock_scoring_function()
        mock_llm = Mock(spec=LLMInterface)

        # Should raise error when scaffolds_per_iter > initial_scaffolds
        with pytest.raises(
            ValueError,
            match="scaffolds_per_iter.*cannot be greater than initial_scaffolds",
        ):
            ExperimentRunner(
                experiment_name="test_experiment",
                training_data=training_data,
                validation_data=validation_data,
                scoring_function=scoring_function,
                scaffolder_llm=mock_llm,
                num_iterations=1,
                scaffolds_per_iter=5,  # Too many
                initial_scaffolds=3,
                num_validation_examples=2,
                base_dir=Path(self.temp_dir),
            )

    def test_validation_log_structure(self):
        """Test that validation logs are created correctly for multiple examples."""
        runner = self.create_experiment_runner(
            num_iterations=2, num_validation_examples=3
        )
        training_data, validation_data = self.create_test_data()

        # Create mocks to track calls
        def mock_generate_func(prompt, scaffolder_llm, examples):
            return ScaffoldResult(
                code='def process_input(input_string: str) -> str:\n    return "SEA"',
                metadata=ScaffoldMetadata(
                    created_at="2024-01-01T00:00:00",
                    model="mock",
                    parent_scaffold_id=None,
                    iteration=0,
                ),
            )

        def mock_evolve_func(run_data, scaffolder_llm):
            return ScaffoldResult(
                code='def process_input(input_string: str) -> str:\n    return "SEA"',
                metadata=ScaffoldMetadata(
                    created_at="2024-01-01T00:00:00",
                    model="mock",
                    parent_scaffold_id=None,
                    iteration=1,
                ),
            )

        mock_generate = Mock(side_effect=mock_generate_func)
        mock_evolve = Mock(side_effect=mock_evolve_func)

        mock_execute = self.create_mock_execute_function()

        with patch(
            "scaffold_learning.core.experiment_runner.generate_scaffold",
            mock_generate,
        ), patch(
            "scaffold_learning.core.experiment_runner.evolve_scaffold",
            mock_evolve,
        ), patch(
            "scaffold_learning.core.experiment_runner.execute_scaffold",
            side_effect=mock_execute,
        ):
            runner.run()

        # Assert on generate_scaffold calls
        assert mock_generate.call_count == 3  # 3 initial scaffolds

        for call in mock_generate.call_args_list:
            _, kwargs = call
            assert (
                kwargs["prompt"]
                == "Generate a Python script that solves crossword clues"
            )
            assert kwargs["scaffolder_llm"] == runner.scaffolder_llm
            assert len(kwargs["examples"]) == 1  # Each gets one random training example
            assert kwargs["examples"][0] in training_data

        # Assert on evolve_scaffold calls
        assert mock_evolve.call_count == 2  # Should have 2 calls in iteration 1

        # Check that evolve_scaffold receives proper ScaffoldRunData
        for call in mock_evolve.call_args_list:
            _, kwargs = call
            run_data = kwargs["run_data"]
            assert kwargs["scaffolder_llm"] == runner.scaffolder_llm
            assert hasattr(run_data, "code")
            assert hasattr(run_data, "execution_log")
            assert hasattr(run_data, "example")
            assert hasattr(run_data, "actual_output")
            assert hasattr(run_data, "score")
            # The example should be from training data
            assert run_data.example in training_data

        # Check iteration 0 logs (should have validation logs for initial scaffolds)
        iter0_logs = runner.file_manager.experiment_dir / "iterations" / "0" / "logs"
        assert iter0_logs.exists()

        # Should have logs for scaffolds 0, 1, 2
        for scaffold_id in ["0", "1", "2"]:
            scaffold_logs = iter0_logs / scaffold_id
            assert scaffold_logs.exists()

            # Should have 3 validation log files (one per validation example)
            log_files = list(scaffold_logs.glob("valid_*.log"))
            assert len(log_files) == 3
            assert (scaffold_logs / "valid_0.log").exists()
            assert (scaffold_logs / "valid_1.log").exists()
            assert (scaffold_logs / "valid_2.log").exists()

        # Check iteration 1 logs
        iter1_logs = runner.file_manager.experiment_dir / "iterations" / "1" / "logs"
        assert iter1_logs.exists()

        # Should have validation logs for ALL scaffolds from iteration 0
        for scaffold_id in ["0", "1", "2"]:
            scaffold_logs = iter1_logs / scaffold_id
            assert scaffold_logs.exists()

            # Should have 3 validation log files
            log_files = list(scaffold_logs.glob("valid_*.log"))
            assert len(log_files) == 3

        # Should also have training logs for evolved scaffolds
        # The evolved scaffolds will have IDs like "0-0", "1-0" (from top 2 scaffolds)
        training_logs_found = False
        for scaffold_dir in iter1_logs.iterdir():
            if (scaffold_dir / "train.log").exists():
                training_logs_found = True
                break
        assert training_logs_found

    def test_generate_and_evolve_inputs(self):
        """Test that generate_scaffold and evolve_scaffold receive correct inputs."""
        # Use custom data for this test
        training_data = [
            DatasetExample(id="t1", input="Input 1", scoring_data={"solution": "OUT1"}),
            DatasetExample(id="t2", input="Input 2", scoring_data={"solution": "OUT2"}),
        ]
        validation_data = [
            DatasetExample(id="v1", input="Val 1", scoring_data={"solution": "VOUT1"}),
        ]

        scoring_function = lambda expected, actual: (
            1.0 if actual.get("solution") == expected else 0.0
        )
        mock_llm = Mock(spec=LLMInterface)

        runner = ExperimentRunner(
            experiment_name="test_inputs",
            training_data=training_data,
            validation_data=validation_data,
            scoring_function=scoring_function,
            scaffolder_llm=mock_llm,
            num_iterations=2,
            scaffolds_per_iter=1,
            initial_scaffolds=2,
            num_validation_examples=1,
            base_dir=Path(self.temp_dir),
        )

        # Create mocks that track calls automatically
        def mock_generate_func(prompt, scaffolder_llm, examples):
            return ScaffoldResult(
                code='def process_input(input_string: str) -> str:\n    return "result"',
                metadata=ScaffoldMetadata(
                    created_at="2024-01-01T00:00:00",
                    model="mock",
                    parent_scaffold_id=None,
                    iteration=0,
                    scaffolder_prompt=f"prompt with {examples[0].input}",
                    scaffolder_output=f"output for {examples[0].input}",
                ),
            )

        def mock_evolve_func(run_data, scaffolder_llm):
            return ScaffoldResult(
                code='def process_input(input_string: str) -> str:\n    return "evolved"',
                metadata=ScaffoldMetadata(
                    created_at="2024-01-01T00:00:00",
                    model="mock",
                    parent_scaffold_id=run_data.example.id,  # Use example id to track
                    iteration=1,
                    scaffolder_prompt=f"evolve prompt for {run_data.example.input}",
                    scaffolder_output=f"evolved output for {run_data.example.input}",
                ),
            )

        mock_generate = Mock(side_effect=mock_generate_func)
        mock_evolve = Mock(side_effect=mock_evolve_func)

        mock_execute = self.create_mock_execute_function()

        with patch(
            "scaffold_learning.core.experiment_runner.generate_scaffold",
            mock_generate,
        ), patch(
            "scaffold_learning.core.experiment_runner.evolve_scaffold",
            mock_evolve,
        ), patch(
            "scaffold_learning.core.experiment_runner.execute_scaffold",
            side_effect=mock_execute,
        ):
            runner.run()

        # Check generate_scaffold inputs using Mock's built-in tracking
        assert mock_generate.call_count == 2

        # Check each call's arguments
        for call in mock_generate.call_args_list:
            _, kwargs = call
            assert (
                "Generate a Python script that solves crossword clues"
                in kwargs["prompt"]
            )
            assert kwargs["scaffolder_llm"] == runner.scaffolder_llm
            assert len(kwargs["examples"]) == 1
            assert kwargs["examples"][0] in training_data

        # Check evolve_scaffold inputs
        assert mock_evolve.call_count == 1  # Only top 1 scaffold evolved

        # Get the arguments from the first (and only) call
        _, kwargs = mock_evolve.call_args
        run_data = kwargs["run_data"]
        scaffolder_llm = kwargs["scaffolder_llm"]

        # Verify ScaffoldRunData structure
        assert isinstance(run_data.code, str)
        assert "def process_input" in run_data.code
        assert isinstance(run_data.execution_log, str)
        assert run_data.example in training_data
        assert isinstance(run_data.actual_output, str)
        assert isinstance(run_data.score, float)

        # Check that the execution log contains expected content
        assert (
            "Scaffold Execution Log" in run_data.execution_log
            or "Error" in run_data.execution_log
        )

        # Verify metadata was saved correctly
        scaffold_0 = runner.file_manager.load_scaffold(0, "0")
        assert scaffold_0.metadata.scaffolder_prompt is not None
        assert scaffold_0.metadata.scaffolder_output is not None
        assert "prompt with" in scaffold_0.metadata.scaffolder_prompt
        assert "output for" in scaffold_0.metadata.scaffolder_output

    @pytest.mark.parametrize(
        "test_case",
        [
            {
                "name": "basic",
                "num_iterations": 3,
                "scaffolds_per_iter": 1,
                "initial_scaffolds": 1,
                # Each entry in the list represents an iteration.
                # The value is a dictionary of scaffold id to validation score.
                "validation_scores": [
                    {},  # No validation calls in iteration 0
                    {"0": 0.3},
                    {"0-0": 0.5},
                    # For now, we don't score 0-0-0 at all because it doesn't
                    # affect any future iterations
                ],
                # Each entry in the list is a set of scaffold ids that should be created
                # in the corresponding iteration.
                "expected_new_scaffolds": [
                    {"0"},  # 0 is generated in iteration 0
                    {"0-0"},  # 0-0 is evolved from 0 in iteration 1
                    {"0-0-0"},  # 0-0-0 is evolved from 0-0 in iteration 2
                ],
            },
            {
                # This is a test that the parameterized test itself fails as expected.
                # This is the same as the basic test, but with an extra validation call
                # in the expectations.
                "name": "test_fails_with_extra_validation_call",
                "num_iterations": 3,
                "scaffolds_per_iter": 1,
                "initial_scaffolds": 1,
                "validation_scores": [
                    {},
                    {
                        "0": 0.3,
                        "0-0": 0.5,  # 0-0 is not actually validated in iteration 1
                    },
                    {"0-0": 0.5},
                ],
                "expected_new_scaffolds": [
                    {"0"},
                    {"0-0"},
                    {"0-0-0"},
                ],
                "test_should_fail_with_error": "Expected validation call for 0-0 in iteration 1",
            },
            {
                # This is a test that the parameterized test itself fails as expected.
                # This is the same as the basic test, but with a validation call missing
                # in the expectations.
                "name": "test_fails_with_missing_validation_call",
                "num_iterations": 3,
                "scaffolds_per_iter": 1,
                "initial_scaffolds": 1,
                # The key is the scaffold id.
                # The value is a dictionary of iteration in which the scaffold is
                # validated to the validation score in that iteration.
                "validation_scores": [
                    {},
                    {"0": 0.3},
                    # Missing validation call for 0-0
                ],
                "expected_new_scaffolds": [
                    {"0"},
                    {"0-0"},
                    {"0-0-0"},
                ],
                "test_should_fail_with_error": "Got validation call for 0-0 in iteration 2",
            },
            {
                # This is a test that the parameterized test itself fails as expected.
                # This is the same as the basic test, but with a new scaffold missing
                # in the expectations.
                "name": "test_fails_with_missing_new_scaffold",
                "num_iterations": 3,
                "scaffolds_per_iter": 1,
                "initial_scaffolds": 1,
                "validation_scores": [
                    {},
                    {"0": 0.3},
                    {"0-0": 0.5},
                ],
                "expected_new_scaffolds": [
                    {"0"},
                    {"0-0-0"},
                ],
                "test_should_fail_with_error": "Got new scaffold 0-0 in iteration 1",
            },
            {
                # In this test, 0-0 is not one of the top two scaffolds of all time
                # in iteration 2, so we have to continue validating more scaffolds.
                # Scaffold 1 does slightly worse than before, but it's still one of the
                # top two scaffolds in iteration 2, so we choose 1 and 1-0.
                "name": "one_evolved_scaffold_is_worse_than_past",
                "num_iterations": 3,
                "scaffolds_per_iter": 2,
                "initial_scaffolds": 2,
                "validation_scores": [
                    {},
                    {"0": 0.3, "1": 0.5},
                    {"0-0": 0.4, "1-0": 0.6, "1": 0.45},
                ],
                "expected_new_scaffolds": [
                    {"0", "1"},
                    {"0-0", "1-0"},
                    {"1-1", "1-0-0"},  # evolved from 1 (0.45) and 1-0 (0.6)
                ],
            },
            {
                # In this test, both new scaffolds are worse than the past scaffolds.
                # We have to run every scaffold and conclude that 0 and 1 are the best.
                "name": "both_new_scaffolds_are_worse_than_past",
                "num_iterations": 3,
                "scaffolds_per_iter": 2,
                "initial_scaffolds": 2,
                "validation_scores": [
                    {},
                    {"0": 0.3, "1": 0.5},
                    {"0-0": 0.1, "1-0": 0.2, "1": 0.45, "0": 0.25},
                ],
                "expected_new_scaffolds": [
                    {"0", "1"},
                    {"0-0", "1-0"},
                    {"0-1", "1-1"},  # evolved from 0 (0.25) and 1 (0.45)
                ],
            },
            {
                # In this test, both new scaffolds are worse than the past scaffolds were
                # in the past, but when we run the past scaffolds, they actually score worse
                # than they did in the past, so the new scaffolds are still the best.
                "name": "past_scaffolds_both_become_worse",
                "num_iterations": 3,
                "scaffolds_per_iter": 2,
                "initial_scaffolds": 2,
                "validation_scores": [
                    {},
                    {"0": 0.4, "1": 0.5},
                    {"0-0": 0.2, "1-0": 0.3, "1": 0.0, "0": 0.1},
                ],
                "expected_new_scaffolds": [
                    {"0", "1"},
                    {"0-0", "1-0"},
                    {"0-0-0", "1-0-0"},  # evolved from 0-0 (0.2) and 1-0 (0.3)
                ],
            },
            {
                "name": "more_initial_scaffolds",
                "num_iterations": 3,
                "scaffolds_per_iter": 2,
                "initial_scaffolds": 3,
                "validation_scores": [
                    {},
                    {"0": 0.4, "1": 0.5, "2": 0.6},
                    {"1-0": 0.55, "2-0": 0.65, "2": 0.59},
                ],
                "expected_new_scaffolds": [
                    {"0", "1", "2"},
                    {"1-0", "2-0"},
                    {"2-0-0", "2-1"},  # evolved from 2-0 (0.65) and 2 (0.59)
                ],
            },
            {
                "name": "validation_of_top_historical_scaffolds",
                "num_iterations": 3,
                "scaffolds_per_iter": 2,
                "initial_scaffolds": 4,
                "validation_scores": [
                    {},
                    {"0": 0.1, "1": 0.2, "2": 0.6, "3": 0.5},
                    {"2-0": 0.3, "3-0": 0.4, "2": 0.35, "3": 0.45},
                ],
                "expected_new_scaffolds": [
                    {"0", "1", "2", "3"},
                    {"2-0", "3-0"},
                    {"3-1", "3-0-0"},  # evolved from 3 (0.45) and 3-0 (0.4)
                ],
            },
            {
                "name": "extra_validation_no_effect_on_selection",
                "num_iterations": 3,
                "scaffolds_per_iter": 2,
                "initial_scaffolds": 5,
                "validation_scores": [
                    {},
                    {"0": 0.1, "1": 0.2, "2": 0.8, "3": 0.7, "4": 0.6},
                    {"2-0": 0.5, "3-0": 0.4, "2": 0.3, "3": 0.25, "4": 0.15},
                ],
                "expected_new_scaffolds": [
                    {"0", "1", "2", "3", "4"},
                    {"2-0", "3-0"},
                    {"2-0-0", "3-0-0"},  # evolved from 2-0 (0.5) and 3-0 (0.4)
                ],
            },
            {
                "name": "extra_validation_changes_final_selection",
                "num_iterations": 3,
                "scaffolds_per_iter": 2,
                "initial_scaffolds": 5,
                "validation_scores": [
                    {},
                    {"0": 0.1, "1": 0.2, "2": 0.8, "3": 0.7, "4": 0.6},
                    {"2-0": 0.5, "3-0": 0.4, "2": 0.3, "3": 0.25, "4": 0.45},
                ],
                "expected_new_scaffolds": [
                    {"0", "1", "2", "3", "4"},
                    {"2-0", "3-0"},
                    {"2-0-0", "4-0"},  # evolved from 2-0 (0.5) and 4 (0.45)
                ],
            },
            {
                "name": "new_scaffolds_are_better_than_all_past",
                "num_iterations": 3,
                "scaffolds_per_iter": 2,
                "initial_scaffolds": 4,
                "validation_scores": [
                    {},
                    {"0": 0.4, "1": 0.5, "2": 0.6, "3": 0.7},
                    {"3-0": 0.9, "2-0": 0.8},
                ],
                "expected_new_scaffolds": [
                    {"0", "1", "2", "3"},
                    {"3-0", "2-0"},
                    {"3-0-0", "2-0-0"},  # evolved from 3-0 (0.9) and 2-0 (0.8)
                ],
            },
            {
                "name": "more_scaffolds_per_iter_and_all_new_scaffolds_are_worse",
                "num_iterations": 3,
                "scaffolds_per_iter": 3,
                "initial_scaffolds": 6,
                "validation_scores": [
                    {},
                    {"0": 0.5, "1": 0.6, "2": 0.7, "3": 0.8, "4": 0.9, "5": 0.4},
                    {
                        "4-0": 0.1,
                        "3-0": 0.05,
                        "2-0": 0.02,
                        "4": 0.85,
                        "3": 0.75,
                        "2": 0.65,
                    },
                ],
                "expected_new_scaffolds": [
                    {"0", "1", "2", "3", "4", "5"},
                    {"4-0", "3-0", "2-0"},
                    {"4-1", "3-1", "2-1"},  # evolved from 4 (0.85), 3 (0.75), 2 (0.65)
                ],
            },
            {
                "name": "more_iterations",
                "num_iterations": 5,
                "scaffolds_per_iter": 2,
                "initial_scaffolds": 4,
                "validation_scores": [
                    {},  # Iteration 0: Generate 4 initial scaffolds
                    {"0": 0.3, "1": 0.6, "2": 0.4, "3": 0.7},  # 3,1 selected (top 2)
                    {
                        "3-0": 0.8,
                        "1-0": 0.7,
                        # Even though 3 and 1-0 have the same score, we refrain from
                        # rescoring 3 because we already have our top 2.
                    },
                    {
                        "3-0-0": 0.85,
                        "1-0-0": 0.65,
                        # Current ranking:
                        # 3-0-0 (0.85), 3-0 (0.8), [1-0 (0.7), 3 (0.7)] (tie), 1-0-0 (0.65),
                        # 1 (0.6), 2 (0.4), 0 (0.3)
                        "3-0": 0.75,
                        # Select 3-0-0 (0.85) and 3-0 (0.75)
                    },
                    {
                        "3-0-0-0": 0.9,
                        "3-0-1": 0.8,
                        # Current ranking:
                        # 3-0-0-0 (0.9), 3-0-0 (0.85), [3-0 (0.8), 3-0-1 (0.8)] (tie), ...
                        "3-0-0": 0.82,
                        # Select 3-0-0-0 (0.9) and 3-0-0 (0.82)
                    },
                    {
                        "3-0-0-0-0": 0.95,
                        "3-0-0-0": 0.9,
                        # These at least tie with all other scaffolds
                    },
                ],
                "expected_new_scaffolds": [
                    {"0", "1", "2", "3"},
                    {"3-0", "1-0"},  # Evolved from 3 and 1
                    {"3-0-0", "1-0-0"},  # Evolved from 3-0 and 1-0
                    {"3-0-0-0", "3-0-1"},  # Evolved from 3-0-0 and 3-0
                    {"3-0-0-0-0", "3-0-0-0"},  # Evolved from 3-0-0-0 and 3-0-0
                    {"3-0-0-0-0-0", "3-0-0-0-1"},  # Evolved from 3-0-0-0-0 and 3-0-0-0
                ],
            },
        ],
    )
    def test_scaffold_selection_based_on_scores(self, test_case):
        """Test that scaffold selection works correctly based on validation scores."""
        raise NotImplementedError("Not implemented")

    def test_run_complete_experiment(self):
        runner = self.create_experiment_runner(
            num_iterations=1,
            scaffolds_per_iter=1,
            initial_scaffolds=2,
            num_validation_examples=1,
        )

        # Mock scaffold generation using helper methods
        mock_scaffold_result = self.create_mock_scaffold_result(
            code="def process_input(s): return 'SEA'"
        )
        mock_execution_result = self.create_mock_execution_result()

        with patch(
            "scaffold_learning.core.experiment_runner.generate_scaffold",
            return_value=mock_scaffold_result,
        ), patch(
            "scaffold_learning.core.experiment_runner.evolve_scaffold",
            return_value=mock_scaffold_result,
        ), patch(
            "scaffold_learning.core.experiment_runner.execute_scaffold",
            return_value=mock_execution_result,
        ), patch.object(
            runner.file_manager,
            "load_scaffold",
            return_value=mock_scaffold_result,
        ):
            best_path = runner.run()

            # Should return a valid path
            assert best_path is not None
            assert isinstance(best_path, Path)

            # Should have created experiment directory structure
            assert (runner.file_manager.experiment_dir / "iterations" / "0").exists()
            assert (runner.file_manager.experiment_dir / "metadata.json").exists()
