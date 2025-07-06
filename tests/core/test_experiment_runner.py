import pytest
import tempfile
from unittest.mock import Mock, patch
from pathlib import Path
from scaffold_learning.core.experiment_runner import ExperimentRunner
from scaffold_learning.core.data_structures import (
    DatasetExample, ScaffoldResult, ScaffoldMetadata, ScaffoldExecutionResult
)
from scaffold_learning.core.llm_interfaces import LLMInterface


class TestExperimentRunner:
    def create_test_data(self):
        """Create test training and validation data."""
        training_data = [
            DatasetExample(
                id="train_1",
                input="5 across: Large feline (4)",
                scoring_data={"solution": "LION"}
            ),
            DatasetExample(
                id="train_2", 
                input="1 down: Flying mammal (3)",
                scoring_data={"solution": "BAT"}
            )
        ]
        
        validation_data = [
            DatasetExample(
                id="valid_1",
                input="3 across: Ocean (3)",
                scoring_data={"solution": "SEA"}
            ),
            DatasetExample(
                id="valid_2",
                input="2 down: Canine (3)",
                scoring_data={"solution": "DOG"}
            )
        ]
        
        return training_data, validation_data

    def create_mock_scoring_function(self):
        """Create a mock scoring function."""
        def scoring_function(expected: str, scoring_data: dict) -> float:
            actual = scoring_data.get("solution", "")
            return 1.0 if actual == expected else 0.0
        return scoring_function

    def test_experiment_runner_init(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            training_data, validation_data = self.create_test_data()
            scoring_function = self.create_mock_scoring_function()
            mock_llm = Mock(spec=LLMInterface)
            
            runner = ExperimentRunner(
                experiment_name="test_experiment",
                training_data=training_data,
                validation_data=validation_data,
                scoring_function=scoring_function,
                scaffolder_llm=mock_llm,
                num_iterations=2,
                scaffolds_per_iter=2,
                initial_scaffolds=3,
                num_validation_examples=2,
                base_dir=Path(temp_dir)
            )
            
            assert runner.experiment_name == "test_experiment"
            assert len(runner.training_data) == 2
            assert len(runner.validation_data) == 2
            assert runner.num_iterations == 2
            assert runner.scaffolds_per_iter == 2
            assert runner.initial_scaffolds == 3

    def test_scaffold_id_generation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            training_data, validation_data = self.create_test_data()
            scoring_function = self.create_mock_scoring_function()
            mock_llm = Mock(spec=LLMInterface)
            
            runner = ExperimentRunner(
                experiment_name="test_experiment",
                training_data=training_data,
                validation_data=validation_data,
                scoring_function=scoring_function,
                scaffolder_llm=mock_llm,
                num_iterations=1,
                scaffolds_per_iter=2,
                initial_scaffolds=3,
                num_validation_examples=2,
                base_dir=Path(temp_dir)
            )
            
            # Test initial scaffold IDs
            assert runner._get_next_scaffold_id(None) == "0"
            assert runner._get_next_scaffold_id(None) == "1"
            assert runner._get_next_scaffold_id(None) == "2"
            
            # Test derived scaffold IDs
            assert runner._get_next_scaffold_id("0") == "0-0"
            assert runner._get_next_scaffold_id("0") == "0-1"
            assert runner._get_next_scaffold_id("2-0") == "2-0-0"

    def test_create_initial_scaffolds(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            training_data, validation_data = self.create_test_data()
            scoring_function = self.create_mock_scoring_function()
            mock_llm = Mock(spec=LLMInterface)
            
            # Mock the scaffold generation
            mock_result = ScaffoldResult(
                code="def process_input(s): return 'test'",
                metadata=ScaffoldMetadata(
                    created_at="2024-01-01",
                    model=None,
                    parent_scaffold_id=None,
                    iteration=0
                )
            )
            
            with patch('scaffold_learning.core.experiment_runner.generate_scaffold', return_value=mock_result):
                runner = ExperimentRunner(
                    experiment_name="test_experiment",
                    training_data=training_data,
                    validation_data=validation_data,
                    scoring_function=scoring_function,
                    scaffolder_llm=mock_llm,
                    num_iterations=1,
                    scaffolds_per_iter=2,
                    initial_scaffolds=3,
                    num_validation_examples=2,
                    base_dir=Path(temp_dir)
                )
                
                scaffold_ids = runner._create_initial_scaffolds("test prompt")
                
                assert len(scaffold_ids) == 3
                assert scaffold_ids == ["0", "1", "2"]

    def test_evaluate_scaffold(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            training_data, validation_data = self.create_test_data()
            scoring_function = self.create_mock_scoring_function()
            mock_llm = Mock(spec=LLMInterface)
            
            runner = ExperimentRunner(
                experiment_name="test_experiment",
                training_data=training_data,
                validation_data=validation_data,
                scoring_function=scoring_function,
                scaffolder_llm=mock_llm,
                num_iterations=1,
                scaffolds_per_iter=2,
                initial_scaffolds=3,
                num_validation_examples=2,
                base_dir=Path(temp_dir)
            )
            
            # Mock scaffold execution
            mock_execution_result = ScaffoldExecutionResult(
                output="SEA",
                stderr="",
                exit_code=0,
                execution_time=1.0
            )
            
            with patch('scaffold_learning.core.experiment_runner.execute_scaffold', return_value=mock_execution_result):
                score = runner._evaluate_scaffold(
                    iteration=0,
                    scaffold_id="0",
                    validation_examples=[validation_data[0]]  # "SEA"
                )
                
                # Should get perfect score since output matches expected
                assert score == 1.0

    def test_select_top_scaffolds(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            training_data, validation_data = self.create_test_data()
            scoring_function = self.create_mock_scoring_function()
            mock_llm = Mock(spec=LLMInterface)
            
            runner = ExperimentRunner(
                experiment_name="test_experiment",
                training_data=training_data,
                validation_data=validation_data,
                scoring_function=scoring_function,
                scaffolder_llm=mock_llm,
                num_iterations=1,
                scaffolds_per_iter=2,
                initial_scaffolds=3,
                num_validation_examples=2,
                base_dir=Path(temp_dir)
            )
            
            # Set up mock scores
            runner.current_iteration_scores = {
                "0": 0.8,
                "1": 0.6,
                "2": 0.9
            }
            
            # Mock scaffold paths
            scaffold_paths = {
                "0": Path(temp_dir) / "scaffold0",
                "1": Path(temp_dir) / "scaffold1", 
                "2": Path(temp_dir) / "scaffold2"
            }
            
            for path in scaffold_paths.values():
                path.mkdir(parents=True)
            
            top_scaffolds = runner._select_top_scaffolds(
                scaffolds_per_iter=2,
                scaffold_paths=scaffold_paths
            )
            
            # Should return top 2 scaffolds: "2" (0.9) and "0" (0.8)
            assert len(top_scaffolds) == 2
            assert top_scaffolds[0][0] == "2"  # scaffold_id
            assert top_scaffolds[1][0] == "0"  # scaffold_id

    def test_run_training_example(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            training_data, validation_data = self.create_test_data()
            scoring_function = self.create_mock_scoring_function()
            mock_llm = Mock(spec=LLMInterface)
            
            runner = ExperimentRunner(
                experiment_name="test_experiment",
                training_data=training_data,
                validation_data=validation_data,
                scoring_function=scoring_function,
                scaffolder_llm=mock_llm,
                num_iterations=1,
                scaffolds_per_iter=2,
                initial_scaffolds=3,
                num_validation_examples=2,
                base_dir=Path(temp_dir)
            )
            
            # Mock scaffold execution and loading
            mock_execution_result = ScaffoldExecutionResult(
                output="LION",
                stderr="",
                exit_code=0,
                execution_time=1.0
            )
            
            mock_scaffold_result = ScaffoldResult(
                code="def process_input(s): return 'LION'",
                metadata=ScaffoldMetadata(
                    created_at="2024-01-01",
                    model=None,
                    parent_scaffold_id=None,
                    iteration=0
                )
            )
            
            with patch('scaffold_learning.core.experiment_runner.execute_scaffold', return_value=mock_execution_result):
                with patch.object(runner.file_manager, 'load_scaffold', return_value=mock_scaffold_result):
                    run_data = runner._run_training_example(
                        iteration=1,
                        scaffold_id="0",
                        example=training_data[0]  # "LION"
                    )
                    
                    assert run_data.actual_output == "LION"
                    assert run_data.score == 1.0  # Perfect match
                    assert run_data.example == training_data[0]

    def test_validation_parameter_check(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            training_data, validation_data = self.create_test_data()
            scoring_function = self.create_mock_scoring_function()
            mock_llm = Mock(spec=LLMInterface)
            
            # Should raise error when scaffolds_per_iter > initial_scaffolds
            with pytest.raises(ValueError, match="scaffolds_per_iter.*cannot be greater than initial_scaffolds"):
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
                    base_dir=Path(temp_dir)
                )

    def test_failed_scaffold_execution_gets_zero_score(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            training_data, validation_data = self.create_test_data()
            scoring_function = self.create_mock_scoring_function()
            mock_llm = Mock(spec=LLMInterface)
            
            runner = ExperimentRunner(
                experiment_name="test_experiment",
                training_data=training_data,
                validation_data=validation_data,
                scoring_function=scoring_function,
                scaffolder_llm=mock_llm,
                num_iterations=1,
                scaffolds_per_iter=2,
                initial_scaffolds=3,
                num_validation_examples=2,
                base_dir=Path(temp_dir)
            )
            
            # Mock failed scaffold execution
            mock_execution_result = ScaffoldExecutionResult(
                output="",
                stderr="Error: scaffold failed",
                exit_code=1,
                execution_time=1.0
            )
            
            with patch('scaffold_learning.core.experiment_runner.execute_scaffold', return_value=mock_execution_result):
                score = runner._evaluate_scaffold(
                    iteration=0,
                    scaffold_id="0",
                    validation_examples=[validation_data[0]]
                )
                
                # Failed execution should get score 0
                assert score == 0.0

    def test_run_complete_experiment(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            training_data, validation_data = self.create_test_data()
            scoring_function = self.create_mock_scoring_function()
            mock_llm = Mock(spec=LLMInterface)
            
            runner = ExperimentRunner(
                experiment_name="test_experiment",
                training_data=training_data,
                validation_data=validation_data,
                scoring_function=scoring_function,
                scaffolder_llm=mock_llm,
                num_iterations=1,
                scaffolds_per_iter=1,
                initial_scaffolds=2,
                num_validation_examples=1,
                base_dir=Path(temp_dir)
            )
            
            # Mock scaffold generation
            mock_scaffold_result = ScaffoldResult(
                code="def process_input(s): return 'SEA'",
                metadata=ScaffoldMetadata(
                    created_at="2024-01-01",
                    model=None,
                    parent_scaffold_id=None,
                    iteration=0
                )
            )
            
            # Mock scaffold execution (successful)
            mock_execution_result = ScaffoldExecutionResult(
                output="SEA",
                stderr="",
                exit_code=0,
                execution_time=1.0
            )
            
            with patch('scaffold_learning.core.experiment_runner.generate_scaffold', return_value=mock_scaffold_result):
                with patch('scaffold_learning.core.experiment_runner.improve_scaffold', return_value=mock_scaffold_result):
                    with patch('scaffold_learning.core.experiment_runner.execute_scaffold', return_value=mock_execution_result):
                        with patch.object(runner.file_manager, 'load_scaffold', return_value=mock_scaffold_result):
                            best_path = runner.run()
                            
                            # Should return a valid path
                            assert best_path is not None
                            assert isinstance(best_path, Path)
                            
                            # Should have created experiment directory structure
                            assert (runner.file_manager.experiment_dir / "iterations" / "0").exists()
                            assert (runner.file_manager.experiment_dir / "metadata.json").exists()