import pytest
import tempfile
import json
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
from scaffold_learning.core.data_structures import LLMResponse


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

        def scoring_function(actual_output: str, scoring_data: dict) -> float:
            return 1.0 if actual_output == scoring_data["solution"] else 0.0

        return scoring_function

    def create_experiment_runner(
        self,
        num_iterations=1,
        scaffolds_per_iter=2,
        initial_scaffolds=3,
        num_training_examples=1,
        num_validation_examples=2,
        experiment_name="test_experiment",
    ):
        """Factory method to create ExperimentRunner with common defaults."""
        training_data, validation_data = self.create_test_data()
        scoring_fn = self.create_mock_scoring_function()
        mock_llm = Mock(spec=LLMInterface)

        return ExperimentRunner(
            experiment_name=experiment_name,
            training_data=training_data,
            validation_data=validation_data,
            scoring_fn=scoring_fn,
            scaffolder_llm=mock_llm,
            num_iterations=num_iterations,
            scaffolds_per_iter=scaffolds_per_iter,
            initial_scaffolds=initial_scaffolds,
            num_training_examples=num_training_examples,
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
                parent_scaffold_id=None,
                iteration=iteration,
            ),
        )

    def _mock_execute(
        self,
        scaffold_dir,
        log_file_path,
        input_string,
        model_spec,
        timeout=120,
        console_output=False,
    ):
        # Create a mock execution log that mimics what would be saved
        execution_log = f"""=== Scaffold Execution Log ===
Model: {model_spec}
Timestamp: 2024-01-01_12:00:00

=== INPUT ===
{input_string}

=== STDOUT ===
SEA

=== STDERR ===
Execution completed successfully
"""

        # Write the execution log directly to the file (to mimic the final result of streaming)
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_file_path, "w") as f:
            f.write(execution_log)

        return ScaffoldExecutionResult(
            output="SEA",
            stderr="Execution completed successfully",
            execution_time=1.0,
            error_message=None,
        )

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
        scoring_fn = self.create_mock_scoring_function()
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
                scoring_fn=scoring_fn,
                scaffolder_llm=mock_llm,
                num_iterations=1,
                scaffolds_per_iter=5,  # Too many
                initial_scaffolds=3,
                num_training_examples=1,
                num_validation_examples=2,
                base_dir=Path(self.temp_dir),
            )

    def test_log_structure(self):
        """Test that validation and training logs are created correctly."""
        runner = self.create_experiment_runner(
            num_iterations=2,
            num_training_examples=2,
            num_validation_examples=3,
        )
        training_data, validation_data = self.create_test_data()

        # Create mocks to track calls
        def mock_generate_func(
            examples,
            scaffolder_llm,
            iteration,
            scoring_fn_code=None,
            suggest_hack=False,
        ):
            return ScaffoldResult(
                code='def process_input(input_string: str) -> str:\n    return "SEA"',
                metadata=ScaffoldMetadata(
                    created_at="2024-01-01T00:00:00",
                    parent_scaffold_id=None,
                    iteration=iteration,
                ),
            )

        def mock_evolve_func(
            run_data,
            scaffolder_llm,
            iteration,
            parent_scaffold_id,
            scoring_fn_code=None,
            suggest_hack=False,
        ):
            return ScaffoldResult(
                code='def process_input(input_string: str) -> str:\n    return "SEA"',
                metadata=ScaffoldMetadata(
                    created_at="2024-01-01T00:00:00",
                    parent_scaffold_id=parent_scaffold_id,
                    iteration=iteration,
                ),
            )

        mock_generate = Mock(side_effect=mock_generate_func)
        mock_evolve = Mock(side_effect=mock_evolve_func)

        with patch(
            "scaffold_learning.core.experiment_runner.generate_scaffold",
            mock_generate,
        ), patch(
            "scaffold_learning.core.experiment_runner.evolve_scaffold",
            mock_evolve,
        ), patch(
            "scaffold_learning.core.experiment_runner.execute_scaffold",
            side_effect=self._mock_execute,
        ):
            runner.run()

        # Assert on generate_scaffold calls
        assert mock_generate.call_count == 3  # 3 initial scaffolds

        for call in mock_generate.call_args_list:
            _, kwargs = call
            assert kwargs["scaffolder_llm"] == runner.scaffolder_llm
            assert (
                len(kwargs["examples"]) == 2
            )  # Each gets num_training_examples training examples
            assert kwargs["examples"][0] in training_data

        # Assert on evolve_scaffold calls
        assert mock_evolve.call_count == 2  # Should have 2 calls in iteration 1

        # Check that evolve_scaffold receives proper ScaffoldRunData
        for call in mock_evolve.call_args_list:
            _, kwargs = call
            run_data_list = kwargs["run_data"]
            assert kwargs["scaffolder_llm"] == runner.scaffolder_llm
            assert len(run_data_list) == 2  # Expecting 2 training examples

            # Check each run_data item
            for run_data in run_data_list:
                assert (
                    run_data.code
                    == 'def process_input(input_string: str) -> str:\n    return "SEA"'
                )
                assert run_data.execution_log == "Execution completed successfully"
                assert run_data.actual_output == "SEA"
                assert run_data.score == 0.0
                assert run_data.example in training_data

        # Check that iteration 0 produced validation scores (initial scaffolds)
        try:
            scores_data = runner.file_manager.load_scores(0)
            assert len(scores_data["valid"]) > 0  # Initial scaffolds were validated
            assert len(scores_data["train"]) == 0  # No training in iteration 0
        except FileNotFoundError:
            pytest.fail(
                "No scores found for iteration 0 - initial validation logs were not properly created"
            )

        # Check that iteration 1 produced validation and training scores
        try:
            scores_data = runner.file_manager.load_scores(1)
            assert len(scores_data["valid"]) > 0  # Some scaffolds were validated
            assert len(scores_data["train"]) > 0  # Some scaffolds were trained
        except FileNotFoundError:
            pytest.fail(
                "No scores found for iteration 1 - logs were not properly created"
            )

    def test_scoring_is_correct(self):
        """Test that scoring.json contains correct average scores."""
        runner = self.create_experiment_runner(
            num_iterations=2,
            num_training_examples=2,
            num_validation_examples=3,
        )

        # Create mocks for scaffold generation and evolution
        def mock_generate_func(
            examples,
            scaffolder_llm,
            iteration,
            scoring_fn_code=None,
            suggest_hack=False,
        ):
            return ScaffoldResult(
                code='def process_input(input_string: str) -> str:\n    return "result"',
                metadata=ScaffoldMetadata(
                    created_at="2024-01-01T00:00:00",
                    parent_scaffold_id=None,
                    iteration=iteration,
                ),
            )

        def mock_evolve_func(
            run_data,
            scaffolder_llm,
            iteration,
            parent_scaffold_id,
            scoring_fn_code=None,
            suggest_hack=False,
        ):
            return ScaffoldResult(
                code='def process_input(input_string: str) -> str:\n    return "evolved"',
                metadata=ScaffoldMetadata(
                    created_at="2024-01-01T00:00:00",
                    parent_scaffold_id=parent_scaffold_id,
                    iteration=iteration,
                ),
            )

        # Create a custom mock execute that returns different outputs based on scaffold_id
        # This will help us test averaging of scores
        def mock_execute_custom(
            scaffold_dir,
            log_file_path,
            input_string,
            model_spec,
            timeout=120,
            console_output=False,
        ):
            # Extract scaffold_id from the scaffold_dir path
            scaffold_id = scaffold_dir.name

            # For scaffold "0": always return correct answer
            # For scaffold "1": return correct answer 50% of the time
            # For scaffold "2": never return correct answer

            if scaffold_id == "0":
                # Always correct - check for clues in input
                if "Ocean" in input_string:
                    output = "SEA"
                elif "Canine" in input_string:
                    output = "DOG"
                elif "Feline" in input_string and "Large" not in input_string:
                    output = "CAT"
                elif "Large feline" in input_string:
                    output = "LION"
                elif "Flying mammal" in input_string:
                    output = "BAT"
                else:
                    output = "correct"
            elif scaffold_id == "1":
                # Sometimes correct (for specific examples)
                if "Ocean" in input_string or "Flying mammal" in input_string:
                    # Correct for valid_1 and train_2
                    if "Ocean" in input_string:
                        output = "SEA"
                    else:
                        output = "BAT"
                else:
                    output = "wrong"
            else:
                # scaffold "2" - always wrong
                output = "wrong"

            return ScaffoldExecutionResult(
                output=output,
                stderr="",
                execution_time=0.1,
            )

        # Run the experiment with our mocks
        with patch(
            "scaffold_learning.core.experiment_runner.generate_scaffold",
            side_effect=mock_generate_func,
        ), patch(
            "scaffold_learning.core.experiment_runner.evolve_scaffold",
            side_effect=mock_evolve_func,
        ), patch(
            "scaffold_learning.core.experiment_runner.execute_scaffold",
            side_effect=mock_execute_custom,
        ):
            runner.run()

        # Check that scoring data contains correct average scores
        # Initial scaffolds are validated in iteration 0
        scores_data_0 = runner.file_manager.load_scores(0)

        # Verify structure for iteration 0 (validation only)
        assert "train" in scores_data_0
        assert "valid" in scores_data_0
        assert len(scores_data_0["train"]) == 0  # No training in iteration 0
        assert len(scores_data_0["valid"]) == 3  # All 3 initial scaffolds validated

        # Now check iteration 1 scores
        scores_data_1 = runner.file_manager.load_scores(1)

        # Verify structure
        assert "train" in scores_data_1
        assert "valid" in scores_data_1

        # Check validation scores based on our custom mock
        # From create_test_data: valid_1 expects "SEA", valid_2 expects "DOG", valid_3 expects "CAT"
        # All 3 initial scaffolds should be validated in iteration 0
        assert len(scores_data_0["valid"]) == 3

        # Check iteration 0 validation scores for all initial scaffolds
        for scaffold_id in ["0", "1", "2"]:
            assert scaffold_id in scores_data_0["valid"]
            # Check new format with mean_score and scores array
            assert "mean_score" in scores_data_0["valid"][scaffold_id]
            assert "scores" in scores_data_0["valid"][scaffold_id]
            assert isinstance(scores_data_0["valid"][scaffold_id]["scores"], list)
            assert (
                len(scores_data_0["valid"][scaffold_id]["scores"]) == 3
            )  # 3 validation examples

        # Check scaffold "0" validation scores (always correct)
        assert abs(scores_data_0["valid"]["0"]["mean_score"] - 1.0) < 0.001
        assert scores_data_0["valid"]["0"]["scores"] == [1.0, 1.0, 1.0]

        # Check scaffold "1" validation scores (correct for valid_1 only)
        assert abs(scores_data_0["valid"]["1"]["mean_score"] - 1 / 3) < 0.001
        # Should have exactly one 1.0 and two 0.0 scores (order may vary)
        scores_1 = scores_data_0["valid"]["1"]["scores"]
        assert sorted(scores_1) == [0.0, 0.0, 1.0]

        # Check scaffold "2" validation scores (never correct)
        assert abs(scores_data_0["valid"]["2"]["mean_score"] - 0.0) < 0.001
        assert scores_data_0["valid"]["2"]["scores"] == [0.0, 0.0, 0.0]

        # Now check iteration 1 - only evolved scaffolds should be validated
        # The exact scaffolds depend on which were selected as top performers
        # We expect 2 evolved scaffolds (top 2 from iteration 0)

        # For training: only top 2 scaffolds get training runs
        # The specific scaffolds and their scores depend on which training examples they receive
        # Since examples are randomly assigned, we just verify:
        # 1. Exactly 2 scaffolds have training scores
        # 2. The scores are in the new format with mean_score and scores array
        # 3. The scores represent correct values (0.0 or 1.0 for each example)
        assert len(scores_data_1["train"]) == 2  # Only top 2 scaffolds

        # Verify scores are in new format with correct structure
        for scaffold_id, score_data in scores_data_1["train"].items():
            assert "mean_score" in score_data
            assert "scores" in score_data
            assert isinstance(score_data["scores"], list)
            assert len(score_data["scores"]) == 2  # 2 training examples

            # Verify individual scores are 0.0 or 1.0
            for score in score_data["scores"]:
                assert score in [
                    0.0,
                    1.0,
                ], f"Invalid score {score} for scaffold {scaffold_id}"

            # Verify mean is correct
            expected_mean = sum(score_data["scores"]) / len(score_data["scores"])
            assert abs(score_data["mean_score"] - expected_mean) < 0.001

            if scaffold_id == "0":
                assert score_data["mean_score"] == 1.0
                assert score_data["scores"] == [1.0, 1.0]

        # Verify that scaffold "0" is in training (it should be top performer)
        assert "0" in scores_data_1["train"]

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

        scoring_fn = lambda expected, actual: (
            1.0 if actual.get("solution") == expected else 0.0
        )
        mock_llm = Mock(spec=LLMInterface)

        runner = ExperimentRunner(
            experiment_name="test_inputs",
            training_data=training_data,
            validation_data=validation_data,
            scoring_fn=scoring_fn,
            scaffolder_llm=mock_llm,
            num_iterations=2,
            scaffolds_per_iter=1,
            initial_scaffolds=2,
            num_training_examples=1,
            num_validation_examples=1,
            base_dir=Path(self.temp_dir),
        )

        # Create mocks that track calls automatically
        def mock_generate_func(
            examples,
            scaffolder_llm,
            iteration,
            scoring_fn_code=None,
            suggest_hack=False,
        ):
            return ScaffoldResult(
                code='def process_input(input_string: str) -> str:\n    return "result"',
                metadata=ScaffoldMetadata(
                    created_at="2024-01-01T00:00:00",
                    parent_scaffold_id=None,
                    iteration=iteration,
                    scaffolder_prompt=f"prompt with {examples[0].input}",
                    scaffolder_response=LLMResponse(
                        content=f"output for {examples[0].input}",
                    ),
                ),
            )

        def mock_evolve_func(
            run_data,
            scaffolder_llm,
            iteration,
            parent_scaffold_id,
            scoring_fn_code=None,
            suggest_hack=False,
        ):
            # run_data is a list of ScaffoldRunData objects
            first_run_data = run_data[0]
            return ScaffoldResult(
                code='def process_input(input_string: str) -> str:\n    return "evolved"',
                metadata=ScaffoldMetadata(
                    created_at="2024-01-01T00:00:00",
                    parent_scaffold_id=parent_scaffold_id,
                    iteration=iteration,
                    scaffolder_prompt=f"evolve prompt for {first_run_data.example.input}",
                    scaffolder_response=LLMResponse(
                        content=f"evolved output for {first_run_data.example.input}",
                    ),
                ),
            )

        mock_generate = Mock(side_effect=mock_generate_func)
        mock_evolve = Mock(side_effect=mock_evolve_func)

        with patch(
            "scaffold_learning.core.experiment_runner.generate_scaffold",
            mock_generate,
        ), patch(
            "scaffold_learning.core.experiment_runner.evolve_scaffold",
            mock_evolve,
        ), patch(
            "scaffold_learning.core.experiment_runner.execute_scaffold",
            side_effect=self._mock_execute,
        ):
            runner.run()

        # Check generate_scaffold inputs using Mock's built-in tracking
        assert mock_generate.call_count == 2

        # Check each call's arguments
        for call in mock_generate.call_args_list:
            _, kwargs = call
            assert kwargs["scaffolder_llm"] == runner.scaffolder_llm
            assert len(kwargs["examples"]) == 1
            assert kwargs["examples"][0] in training_data

        # Check evolve_scaffold inputs
        assert mock_evolve.call_count == 1  # Only top 1 scaffold evolved

        # Get the arguments from the first (and only) call
        _, kwargs = mock_evolve.call_args
        run_data_list = kwargs["run_data"]
        scaffolder_llm = kwargs["scaffolder_llm"]

        # Verify run_data is a list with one ScaffoldRunData
        assert isinstance(run_data_list, list)
        assert len(run_data_list) == 1
        run_data = run_data_list[0]

        # Verify ScaffoldRunData structure
        assert isinstance(run_data.code, str)
        assert "def process_input" in run_data.code
        assert isinstance(run_data.execution_log, str)
        assert run_data.example in training_data
        assert isinstance(run_data.actual_output, str)
        assert isinstance(run_data.score, float)

        # Check that the execution log contains expected content
        assert (
            "Execution completed" in run_data.execution_log
            or "Error" in run_data.execution_log
        )

        # Verify metadata was saved correctly
        scaffold_0 = runner.file_manager.load_scaffold("0")
        assert scaffold_0.metadata.scaffolder_prompt is not None
        assert scaffold_0.metadata.scaffolder_response is not None
        assert "prompt with" in scaffold_0.metadata.scaffolder_prompt
        assert "output for" in scaffold_0.metadata.scaffolder_response.content

    def _run_scaffold_selection_test(self, test_case):
        """Test that scaffold selection works correctly based on validation scores."""
        runner = self.create_experiment_runner(
            num_iterations=test_case["num_iterations"],
            scaffolds_per_iter=test_case["scaffolds_per_iter"],
            initial_scaffolds=test_case["initial_scaffolds"],
            num_training_examples=1,
            num_validation_examples=1,
        )
        training_data, validation_data = self.create_test_data()

        expected_validation_scores = test_case["validation_scores"]

        def mock_scoring_function(actual_output, scoring_data):
            # Parse the output which should be "scaffold_id:iteration:run_type"
            parts = actual_output.split(":")
            scaffold_id = parts[0]
            current_iteration = int(parts[1])
            run_type = parts[2]

            # Only check validation calls against expected scores
            if run_type == "train":
                # Training calls - return a default score, don't validate against expectations
                return 0.5  # Arbitrary training score

            # This is a validation call - check against expectations
            if current_iteration < len(expected_validation_scores):
                iter_scores = expected_validation_scores[current_iteration]
                if scaffold_id in iter_scores:
                    return iter_scores[scaffold_id]

            # Fail hard if we try to validate an unexpected scaffold
            raise AssertionError(
                f"Unexpected validation request for scaffold {scaffold_id} in iteration {current_iteration}"
            )

        def mock_execute_func(
            scaffold_dir,
            log_file_path,
            input_string,
            model_spec,
            timeout=120,
            console_output=False,
        ):
            # Extract scaffold_id from the scaffold_dir path
            scaffold_id = scaffold_dir.name
            # Extract iteration from the log_file_path
            iteration = int(log_file_path.parent.parent.name)
            # Extract run_type (train/valid) from log file name
            log_filename = log_file_path.stem  # e.g., "1_train" or "2_valid"
            run_type = "valid" if "valid" in log_filename else "train"
            return ScaffoldExecutionResult(
                output=f"{scaffold_id}:{iteration}:{run_type}",  # Include run_type for scoring
                stderr="",
                execution_time=0.1,
            )

        def mock_generate_func(
            examples,
            scaffolder_llm,
            iteration,
            scoring_fn_code=None,
            suggest_hack=False,
        ):
            return ScaffoldResult(
                code='def process_input(input_string: str) -> str:\n    return "result"',
                metadata=ScaffoldMetadata(
                    created_at="2024-01-01T00:00:00",
                    parent_scaffold_id=None,
                    iteration=iteration,
                ),
            )

        def mock_evolve_func(
            run_data,
            scaffolder_llm,
            iteration,
            parent_scaffold_id,
            scoring_fn_code=None,
            suggest_hack=False,
        ):
            return ScaffoldResult(
                code='def process_input(input_string: str) -> str:\n    return "evolved"',
                metadata=ScaffoldMetadata(
                    created_at="2024-01-01T00:00:00",
                    parent_scaffold_id=parent_scaffold_id,
                    iteration=iteration,
                ),
            )

        # Override the runner's scoring function
        runner.scoring_fn = mock_scoring_function

        mock_generate = Mock(side_effect=mock_generate_func)
        mock_evolve = Mock(side_effect=mock_evolve_func)

        with patch(
            "scaffold_learning.core.experiment_runner.generate_scaffold",
            mock_generate,
        ), patch(
            "scaffold_learning.core.experiment_runner.evolve_scaffold", mock_evolve
        ), patch(
            "scaffold_learning.core.experiment_runner.execute_scaffold",
            side_effect=mock_execute_func,
        ):
            runner.run()

        # Now verify behavior by checking the actual output files
        expected_new_scaffolds = test_case["expected_new_scaffolds"]

        # Verify scaffold creation using file manager
        for iteration in range(test_case["num_iterations"]):
            if iteration < len(expected_new_scaffolds):
                expected_scaffolds = expected_new_scaffolds[iteration]
            else:
                expected_scaffolds = set()  # No scaffolds expected for this iteration

            # Check that all expected scaffolds exist by verifying we can load them
            for scaffold_id in expected_scaffolds:
                try:
                    scaffold_result = runner.file_manager.load_scaffold(scaffold_id)
                    assert (
                        scaffold_result.code is not None
                    ), f"Scaffold {scaffold_id} has no code"
                except FileNotFoundError:
                    raise AssertionError(
                        f"Expected scaffold {scaffold_id} to exist in iteration {iteration} at"
                    )

            # Verify we can get validation scores for existing scaffolds
            all_scores = runner.file_manager.get_most_recent_validation_scores()
            for scaffold_id in expected_scaffolds:
                assert (
                    scaffold_id in all_scores
                ), f"Scaffold {scaffold_id} not found in validation scores"

            # Check for unexpected scaffolds - find scaffolds that were created but not expected
            # We need to determine which scaffolds were created in this specific iteration
            # Since we can't easily determine iteration from scaffold structure in flat layout,
            # we'll check at the end of all iterations instead of per-iteration

        # Final check: verify that ONLY the expected scaffolds exist, no more, no less
        all_expected_scaffolds = set()
        for scaffolds_set in expected_new_scaffolds:
            all_expected_scaffolds.update(scaffolds_set)

        all_actual_scaffolds = set(
            runner.file_manager.get_most_recent_validation_scores().keys()
        )

        if all_expected_scaffolds != all_actual_scaffolds:
            unexpected_scaffolds = all_actual_scaffolds - all_expected_scaffolds
            missing_scaffolds = all_expected_scaffolds - all_actual_scaffolds

            if unexpected_scaffolds:
                # Try to figure out which iteration these unexpected scaffolds were created in
                # For the error message format expected by the test
                unexpected_list = sorted(list(unexpected_scaffolds))
                # Use the highest iteration number for the error message
                max_iteration = test_case["num_iterations"] - 1
                raise AssertionError(
                    f"Iteration {max_iteration}: expected scaffolds [], got {unexpected_list}"
                )
            elif missing_scaffolds:
                missing_list = sorted(list(missing_scaffolds))
                raise AssertionError(f"Missing expected scaffolds: {missing_list}")

        # Verify validation scores using file manager
        # Now iteration 0 should have validation scores for initial scaffolds
        for iteration in range(test_case["num_iterations"]):
            if iteration < len(expected_validation_scores):
                expected_validated_scaffolds = set(
                    expected_validation_scores[iteration].keys()
                )
            else:
                expected_validated_scaffolds = (
                    set()
                )  # No validation expected for this iteration

            try:
                scores_data = runner.file_manager.load_scores(iteration)
                actual_validated_scaffolds = set(scores_data["valid"].keys())

                assert (
                    expected_validated_scaffolds == actual_validated_scaffolds
                ), f"Iteration {iteration}: expected validation for {sorted(expected_validated_scaffolds)}, got {sorted(actual_validated_scaffolds)}"

                # Verify the actual scores match expectations
                for scaffold_id, expected_score in expected_validation_scores[
                    iteration
                ].items():
                    actual_score = scores_data["valid"][scaffold_id]["mean_score"]
                    assert (
                        actual_score == expected_score
                    ), f"Iteration {iteration}, scaffold {scaffold_id}: expected score {expected_score}, got {actual_score}"

            except FileNotFoundError:
                if expected_validated_scaffolds:
                    raise AssertionError(
                        f"Expected scoring file for iteration {iteration} with scaffolds {expected_validated_scaffolds}, but file doesn't exist"
                    )

    def test_simplified_scaffold_selection(self):
        """Test that scaffolds are selected based on their validation scores."""
        runner = self.create_experiment_runner(
            num_iterations=3,
            scaffolds_per_iter=2,
            initial_scaffolds=3,
            num_training_examples=1,
            num_validation_examples=1,
        )

        def mock_scoring_function(actual_output, scoring_data):
            # Create predictable scores: scaffold 2 > scaffold 0 > scaffold 1
            scaffold_id = actual_output.split(":", 1)[0]

            score_map = {
                "0": 0.7,
                "1": 0.3,
                "2": 0.9,
                "2-0": 0.95,  # Evolved from best scaffold becomes even better
                "0-0": 0.75,  # Evolved from second best improves slightly
            }
            return score_map.get(scaffold_id, 0.5)

        def mock_execute_func(
            scaffold_dir,
            log_file_path,
            input_string,
            model_spec,
            timeout=120,
            console_output=False,
        ):
            scaffold_id = scaffold_dir.name
            iteration = int(log_file_path.parent.parent.name)
            return ScaffoldExecutionResult(
                output=f"{scaffold_id}:{iteration}",
                stderr="",
                execution_time=0.1,
            )

        def mock_generate_func(
            examples,
            scaffolder_llm,
            iteration,
            scoring_fn_code=None,
            suggest_hack=False,
        ):
            return ScaffoldResult(
                code='def process_input(s): return "result"',
                metadata=ScaffoldMetadata(
                    created_at="2024-01-01T00:00:00",
                    parent_scaffold_id=None,
                    iteration=iteration,
                ),
            )

        def mock_evolve_func(
            run_data,
            scaffolder_llm,
            iteration,
            parent_scaffold_id,
            scoring_fn_code=None,
            suggest_hack=False,
        ):
            return ScaffoldResult(
                code='def process_input(s): return "evolved"',
                metadata=ScaffoldMetadata(
                    created_at="2024-01-01T00:00:00",
                    parent_scaffold_id=parent_scaffold_id,
                    iteration=iteration,
                ),
            )

        runner.scoring_fn = mock_scoring_function

        with patch(
            "scaffold_learning.core.experiment_runner.generate_scaffold",
            side_effect=mock_generate_func,
        ), patch(
            "scaffold_learning.core.experiment_runner.evolve_scaffold",
            side_effect=mock_evolve_func,
        ), patch(
            "scaffold_learning.core.experiment_runner.execute_scaffold",
            side_effect=mock_execute_func,
        ):
            best_scaffold_id, best_score = runner.run()

        # Verify the best scaffold is the one with the highest score
        assert best_scaffold_id == "2-0"  # Should be the evolved version of scaffold 2
        assert abs(best_score - 0.95) < 0.01

        # Verify that scores were saved correctly
        # Initial scaffolds validated in iteration 0
        iteration_0_scores = runner.file_manager.load_scores(0)
        assert len(iteration_0_scores["valid"]) == 3

        # Check that the scores match what we expect for initial scaffolds
        assert abs(iteration_0_scores["valid"]["0"]["mean_score"] - 0.7) < 0.01
        assert abs(iteration_0_scores["valid"]["1"]["mean_score"] - 0.3) < 0.01
        assert abs(iteration_0_scores["valid"]["2"]["mean_score"] - 0.9) < 0.01

        # Evolved scaffolds validated in their creation iterations
        iteration_1_scores = runner.file_manager.load_scores(1)
        assert len(iteration_1_scores["valid"]) == 2  # Top 2 scaffolds evolved
        assert abs(iteration_1_scores["valid"]["0-0"]["mean_score"] - 0.75) < 0.01
        assert abs(iteration_1_scores["valid"]["2-0"]["mean_score"] - 0.95) < 0.01

        iteration_2_scores = runner.file_manager.load_scores(2)
        assert len(iteration_2_scores["valid"]) == 2  # Next generation evolved

    # Normal test cases (expect success)
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
                    {"0": 0.3},  # Initial scaffolds validated in iteration 0
                    {"0-0": 0.5},  # Evolved scaffolds validated in iteration 1
                    {"0-0-0": 0.7},  # Evolved scaffolds validated in iteration 2
                ],
                # Each entry in the list is a set of scaffold ids that should be created
                # in the corresponding iteration.
                "expected_new_scaffolds": [
                    {"0"},  # 0 is generated in iteration 0
                    {"0-0"},  # 0-0 is evolved from 0 in iteration 1
                    {"0-0-0"},  # 0-0-0 is evolved from 0-0 in iteration 2
                ],
            },
        ],
    )
    def test_scaffold_selection_based_on_scores(self, test_case):
        """Test that scaffold selection works correctly based on validation scores."""
        self._run_scaffold_selection_test(test_case)

    # Meta-test cases (expect specific failures to validate test framework)
    @pytest.mark.parametrize(
        "test_case",
        [
            {
                "name": "test_fails_with_extra_validation_call",
                "num_iterations": 2,
                "scaffolds_per_iter": 1,
                "initial_scaffolds": 1,
                "validation_scores": [
                    {"0": 0.3},  # Initial scaffold validated in iteration 0
                    {
                        "0-0": 0.5,
                        "extra": 0.5,  # Extra validation call that shouldn't happen
                    },
                ],
                "expected_new_scaffolds": [
                    {"0"},
                    {"0-0"},
                ],
                "test_should_fail_with_error": "Iteration 1: expected validation for ['0-0', 'extra'], got ['0-0']",
            },
            {
                "name": "test_fails_with_missing_validation_call",
                "num_iterations": 2,
                "scaffolds_per_iter": 1,
                "initial_scaffolds": 1,
                "validation_scores": [
                    {"0": 0.3},  # Initial scaffold validated in iteration 0
                    # Missing validation call for 0-0 in iteration 1
                ],
                "expected_new_scaffolds": [
                    {"0"},
                    {"0-0"},
                ],
                "test_should_fail_with_error": "Unexpected validation request for scaffold 0-0 in iteration 1",
            },
            {
                "name": "test_fails_with_wrong_validation_call",
                "num_iterations": 2,
                "scaffolds_per_iter": 1,
                "initial_scaffolds": 1,
                "validation_scores": [
                    {"0": 0.3},  # Initial scaffold validated in iteration 0
                    {"WRONG": 0.5},  # Wrong scaffold id in iteration 1
                ],
                "expected_new_scaffolds": [
                    {"0"},
                    {"0-0"},
                ],
                "test_should_fail_with_error": "Unexpected validation request for scaffold 0-0 in iteration 1",
            },
            {
                "name": "test_fails_with_missing_new_scaffold",
                "num_iterations": 2,
                "scaffolds_per_iter": 1,
                "initial_scaffolds": 1,
                "validation_scores": [
                    {"0": 0.3},  # Initial scaffold validated in iteration 0
                    {
                        "0-0": 0.5
                    },  # Scaffold that gets created but shouldn't per expected list
                ],
                "expected_new_scaffolds": [
                    {"0"},
                    # Missing iteration 1 - expect no scaffolds but 0-0 gets created
                ],
                "test_should_fail_with_error": "Iteration 1: expected scaffolds [], got ['0-0']",
            },
            {
                "name": "test_fails_with_wrong_scaffold",
                "num_iterations": 2,
                "scaffolds_per_iter": 1,
                "initial_scaffolds": 1,
                "validation_scores": [
                    {"0": 0.3},  # Initial scaffold validated in iteration 0
                    {"0-0": 0.5},  # Scaffold validated in iteration 1
                ],
                "expected_new_scaffolds": [
                    {"0"},
                    {"WRONG"},  # Wrong scaffold id expected
                ],
                "test_should_fail_with_error": "Expected scaffold WRONG to exist in iteration 1 at",
            },
        ],
    )
    def test_scaffold_selection_meta_validation(self, test_case):
        """Test that the scaffold selection test framework correctly catches errors."""
        expected_error = test_case["test_should_fail_with_error"]
        with pytest.raises(AssertionError) as exc_info:
            self._run_scaffold_selection_test(test_case)

        # Check that the actual error message contains the expected substring
        actual_error = str(exc_info.value)
        assert (
            expected_error in actual_error
        ), f"Expected error message to contain '{expected_error}', but got: {actual_error}"

    def test_run_complete_experiment(self):
        runner = self.create_experiment_runner(
            num_iterations=2,
            scaffolds_per_iter=1,
            initial_scaffolds=2,
            num_training_examples=1,
            num_validation_examples=1,
        )

        # Mock scaffold generation using helper methods
        mock_scaffold_result = self.create_mock_scaffold_result(
            code="def process_input(s): return 'SEA'"
        )

        with patch(
            "scaffold_learning.core.experiment_runner.generate_scaffold",
            return_value=mock_scaffold_result,
        ), patch(
            "scaffold_learning.core.experiment_runner.evolve_scaffold",
            return_value=mock_scaffold_result,
        ), patch(
            "scaffold_learning.core.experiment_runner.execute_scaffold",
            side_effect=self._mock_execute,
        ):
            best_scaffold_id, best_score = runner.run()

        # Should return a valid scaffold ID and score
        assert best_scaffold_id is not None
        assert isinstance(best_scaffold_id, str)
        assert isinstance(best_score, float)

        # Should have created scaffolds and metadata
        # Verify scaffolds exist by checking we can get validation scores
        scores = runner.file_manager.get_most_recent_validation_scores()
        assert len(scores) > 0  # Should have some scaffolds

        # Verify we can load at least one scaffold
        scaffold_ids = list(scores.keys())
        scaffold_result = runner.file_manager.load_scaffold(scaffold_ids[0])
        assert scaffold_result.code is not None
