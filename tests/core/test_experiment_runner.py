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
    LLMResponse,
)
from scaffold_learning.core.scaffold_execution import (
    ScaffoldExecutionResult,
    ScaffoldExecutionTask,
)
from scaffold_learning.core.llm_interfaces import LLMInterface
from scaffold_learning.core.hydra_config import ExperimentConfig


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

        # Create ExperimentConfig
        config = ExperimentConfig(
            experiment_name=experiment_name,
            data_dir=str(Path(self.temp_dir) / "data"),
            domain="test_domain",
            domain_params={},
            num_iterations=num_iterations,
            scaffolds_per_iter=scaffolds_per_iter,
            initial_scaffolds=initial_scaffolds,
            num_validation_examples=num_validation_examples,
            num_training_examples=num_training_examples,
            scaffolder="test_scaffolder",
            executor="gpt-4",
            strategy=None,
            strategy_batch_size=None,
            show_scoring_function=False,
            suggest_hack="none",
            train_seed=42,
            valid_seed=42,
            test_seed=42,
            num_test_examples=0,  # Set to 0 to avoid test evaluation in unit tests
            scaffold_timeout=120,
            max_generate_workers=1,
            max_execute_workers=1,
            base_dir=str(Path(self.temp_dir)),
            build_docker=False,
            executor_reasoning_effort="minimal",
            scaffolder_reasoning_effort="minimal",
        )

        data = {"train": training_data, "valid": validation_data, "test": []}

        return ExperimentRunner(
            config=config,
            data=data,
            scoring_fn=scoring_fn,
            scaffolder_llm=mock_llm,
            output_dir=Path(self.temp_dir),
        )

    def create_mock_scaffold_result(
        self, code="def process_input(s): return 'output'", iteration=0, parent_id=None
    ):
        """Helper to create ScaffoldResult objects for testing."""
        return ScaffoldResult(
            code=code,
            metadata=ScaffoldMetadata(
                created_at="2024-01-01T00:00:00",
                parent_scaffold_id=parent_id,
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
        reasoning_effort="minimal",
    ):
        """Mock scaffold execution to return success with fixed output."""
        return ScaffoldExecutionResult(
            output="SEA",
            stderr="Mock execution stderr",
            execution_time=0.1,
            error_message=None,
        )

    def test_experiment_runner_init(self):
        """Test that ExperimentRunner initializes correctly."""
        runner = self.create_experiment_runner()
        assert runner.config.experiment_name == "test_experiment"
        assert runner.is_baseline == False
        assert runner.scaffold_evaluator is not None

    def test_validation_parameter_check(self):
        """Test parameter validation during init."""
        runner = self.create_experiment_runner(
            num_validation_examples=1, num_training_examples=2
        )
        assert len(runner.validation_data) >= 1
        assert len(runner.training_data) >= 1

    def test_log_structure(self):
        """Test the log directory structure is created correctly."""
        runner = self.create_experiment_runner()

        # Check basic directory structure
        base_path = Path(runner.file_manager.experiment_dir)
        assert base_path.exists()

        # Check that experiment metadata was saved
        metadata_file = base_path / "metadata.json"
        assert metadata_file.exists()

        with open(metadata_file) as f:
            metadata = json.load(f)
            assert metadata["experiment_name"] == "test_experiment"

    def test_scoring_is_correct(self):
        """Test that scoring.json contains correct average scores."""
        runner = self.create_experiment_runner(
            num_iterations=1,
            num_training_examples=1,
            num_validation_examples=2,
        )

        # Mock the actual execution but let scoring logic run
        with patch(
            "scaffold_learning.core.scaffold_execution._execute_scaffold"
        ) as mock_execute:
            mock_execute.return_value = ScaffoldExecutionResult(
                output="test_output",
                stderr="test_stderr",
                execution_time=1.0,
                error_message=None,
            )

            # Mock generate_scaffold
            with patch(
                "scaffold_learning.core.scaffold_generator.generate_scaffold"
            ) as mock_generate:
                mock_generate.return_value = self.create_mock_scaffold_result()
                runner.run()

        # Check that scoring directory was created
        scoring_dir = runner.file_manager.experiment_dir / "scoring"
        assert scoring_dir.exists()

        # Check that experiment completed successfully
        metadata_file = runner.file_manager.experiment_dir / "metadata.json"
        assert metadata_file.exists()

    def test_generate_and_evolve_inputs(self):
        """Test that scaffold generation and evolution receive correct inputs."""
        runner = self.create_experiment_runner(
            num_iterations=2, scaffolds_per_iter=1, initial_scaffolds=1
        )

        # Mock scaffold execution but let evaluation logic run
        with patch(
            "scaffold_learning.core.scaffold_execution._execute_scaffold"
        ) as mock_execute:
            mock_execute.return_value = ScaffoldExecutionResult(
                output="test_output",
                stderr="test_stderr",
                execution_time=1.0,
                error_message=None,
            )

            with patch(
                "scaffold_learning.core.scaffold_generator.generate_scaffold"
            ) as mock_generate, patch(
                "scaffold_learning.core.scaffold_generator.evolve_scaffold"
            ) as mock_evolve:

                mock_generate.return_value = self.create_mock_scaffold_result()
                mock_evolve.return_value = self.create_mock_scaffold_result(
                    parent_id="0"
                )

                runner.run()

        # Verify generation was called for initial scaffolds
        assert mock_generate.called
        # Verify evolution was called for subsequent iterations
        assert mock_evolve.called

    def test_experiment_creates_scaffolds_and_runs(self):
        """Test that experiment creates scaffolds and runs successfully."""
        runner = self.create_experiment_runner(
            num_iterations=1,
            initial_scaffolds=2,
            num_training_examples=1,
            num_validation_examples=1,
        )

        # Mock scaffold evaluator to return predictable results
        with patch.object(
            runner.scaffold_evaluator, "evaluate_scaffold"
        ) as mock_evaluate:
            mock_evaluate.return_value = [Mock(score=0.9)]

            with patch(
                "scaffold_learning.core.scaffold_generator.generate_scaffold"
            ) as mock_generate:
                mock_generate.return_value = self.create_mock_scaffold_result()

                best_scaffold_id, best_score, test_score = runner.run()

        # Verify results
        assert best_scaffold_id is not None
        assert best_score > 0
        assert mock_generate.call_count == 2  # 2 initial scaffolds
        assert mock_evaluate.call_count == 2  # 2 scaffolds evaluated

    def test_different_examples_per_scaffold(self):
        """Test that scaffolds can be generated with different examples."""
        runner = self.create_experiment_runner(
            num_iterations=1,
            initial_scaffolds=2,
            num_training_examples=2,
            num_validation_examples=1,
        )

        # Mock scaffold execution and generation
        with patch(
            "scaffold_learning.core.scaffold_execution._execute_scaffold"
        ) as mock_execute:
            mock_execute.return_value = ScaffoldExecutionResult(
                output="test_output",
                stderr="test_stderr",
                execution_time=1.0,
                error_message=None,
            )

            with patch(
                "scaffold_learning.core.scaffold_generator.generate_scaffold"
            ) as mock_generate:
                mock_generate.return_value = self.create_mock_scaffold_result()
                runner.run()

        # Verify that generate_scaffold was called for each initial scaffold
        assert mock_generate.call_count == 2  # Should match initial_scaffolds

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
            "scaffold_learning.core.scaffold_generator.generate_scaffold",
            return_value=mock_scaffold_result,
        ), patch(
            "scaffold_learning.core.scaffold_generator.evolve_scaffold",
            return_value=mock_scaffold_result,
        ), patch(
            "scaffold_learning.core.scaffold_execution._execute_scaffold"
        ) as mock_execute:
            mock_execute.return_value = ScaffoldExecutionResult(
                output="SEA",
                stderr="test_stderr",
                execution_time=1.0,
                error_message=None,
            )
            best_scaffold_id, best_score, test_score = runner.run()

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
