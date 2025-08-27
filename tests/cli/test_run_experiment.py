"""Tests for run_experiment CLI with Hydra configuration."""

import pytest
from unittest.mock import patch, Mock, MagicMock
from pathlib import Path
import tempfile
from scaffold_learning.cli.run_experiment import main
from omegaconf import DictConfig


@patch("scaffold_learning.cli.run_experiment.HydraConfig")
@patch("scaffold_learning.cli.run_experiment.ExperimentRunner")
@patch("scaffold_learning.cli.run_experiment.load_datasets")
@patch("scaffold_learning.cli.run_experiment.create_scoring_function")
@patch("scaffold_learning.cli.run_experiment.LLMFactory")
@patch("scaffold_learning.cli.run_experiment.build_docker_image")
def test_domain_params_passed_to_scoring_function(
    mock_build,
    mock_llm_factory,
    mock_scoring,
    mock_load,
    mock_runner,
    mock_hydra_config,
):
    """Test that domain params are correctly passed to create_scoring_function."""
    # Mock the necessary returns
    mock_load.return_value = {"train": [], "valid": [], "test": []}
    mock_scoring.return_value = lambda x, y: 0.0
    mock_llm_factory.create_llm.return_value = Mock()
    mock_runner_instance = mock_runner.return_value
    mock_runner_instance.run.return_value = ("scaffold-0", 0.5, None)

    # Mock HydraConfig output directory
    mock_hydra_instance = Mock()
    mock_hydra_instance.runtime.output_dir = "/tmp/test_output"
    mock_hydra_config.get.return_value = mock_hydra_instance

    # Create temporary data directory
    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir)
        (data_dir / "train.jsonl").touch()
        (data_dir / "valid.jsonl").touch()
        (data_dir / "test.jsonl").touch()

        # Create Hydra config with domain params
        cfg = DictConfig(
            {
                "experiment_name": "test_experiment",
                "data_dir": str(data_dir),
                "domain": "reward-model",
                "domain_params": {
                    "rm": "llm:haiku",
                    "temperature": "0.7",
                },
                "num_iterations": 1,
                "scaffolds_per_iter": 1,
                "initial_scaffolds": 1,
                "num_validation_examples": 1,
                "num_training_examples": 1,
                "scaffolder": "haiku",
                "executor": "haiku",
                "strategy": None,
                "strategy_batch_size": None,
                "show_scoring_function": False,
                "suggest_hack": "none",
                "train_seed": 42,
                "valid_seed": 42,
                "test_seed": 42,
                "num_test_examples": 0,
                "scaffold_timeout": 120,
                "max_generate_workers": 1,
                "max_execute_workers": 1,
                "thinking_budget": None,
                "base_dir": str(tmpdir),
                "build_docker": False,
                "model_specs": {},
            }
        )

        main(cfg)

        # Verify create_scoring_function was called with domain_params
        mock_scoring.assert_called_once()
        call_args = mock_scoring.call_args

        # Check positional argument
        assert call_args[0][0] == "reward-model"

        # Check keyword argument domain_params
        assert "domain_params" in call_args[1]
        assert call_args[1]["domain_params"] == {
            "rm": "llm:haiku",
            "temperature": "0.7",
        }


@patch("scaffold_learning.cli.run_experiment.HydraConfig")
@patch("scaffold_learning.cli.run_experiment.ExperimentRunner")
@patch("scaffold_learning.cli.run_experiment.load_datasets")
@patch("scaffold_learning.cli.run_experiment.create_scoring_function")
@patch("scaffold_learning.cli.run_experiment.LLMFactory")
@patch("scaffold_learning.cli.run_experiment.build_docker_image")
def test_crosswords_domain_param_mode(
    mock_build,
    mock_llm_factory,
    mock_scoring,
    mock_load,
    mock_runner,
    mock_hydra_config,
):
    """Test crosswords domain with mode parameter."""
    # Mock the necessary returns
    mock_load.return_value = {"train": [], "valid": [], "test": []}
    mock_scoring.return_value = lambda x, y: 0.0
    mock_llm_factory.create_llm.return_value = Mock()
    mock_runner_instance = mock_runner.return_value
    mock_runner_instance.run.return_value = ("scaffold-0", 0.8, None)

    # Mock HydraConfig output directory
    mock_hydra_instance = Mock()
    mock_hydra_instance.runtime.output_dir = "/tmp/test_output"
    mock_hydra_config.get.return_value = mock_hydra_instance

    # Create temporary data directory
    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir)
        (data_dir / "train.jsonl").touch()
        (data_dir / "valid.jsonl").touch()
        (data_dir / "test.jsonl").touch()

        # Create Hydra config with crosswords domain and mode param
        cfg = DictConfig(
            {
                "experiment_name": "crosswords_test",
                "data_dir": str(data_dir),
                "domain": "crosswords",
                "domain_params": {
                    "mode": "lenient",
                },
                "num_iterations": 1,
                "scaffolds_per_iter": 1,
                "initial_scaffolds": 1,
                "num_validation_examples": 1,
                "num_training_examples": 1,
                "scaffolder": "haiku",
                "executor": "haiku",
                "strategy": None,
                "strategy_batch_size": None,
                "show_scoring_function": False,
                "suggest_hack": "none",
                "train_seed": 42,
                "valid_seed": 42,
                "test_seed": 42,
                "num_test_examples": 0,
                "scaffold_timeout": 120,
                "max_generate_workers": 1,
                "max_execute_workers": 1,
                "thinking_budget": None,
                "base_dir": str(tmpdir),
                "build_docker": False,
                "model_specs": {},
            }
        )

        main(cfg)

        # Verify create_scoring_function was called with mode=lenient
        mock_scoring.assert_called_once()
        call_args = mock_scoring.call_args

        # Check positional argument
        assert call_args[0][0] == "crosswords"

        # Check keyword argument domain_params
        assert "domain_params" in call_args[1]
        assert call_args[1]["domain_params"] == {"mode": "lenient"}


@patch("scaffold_learning.cli.run_experiment.HydraConfig")
@patch("scaffold_learning.cli.run_experiment.ExperimentRunner")
@patch("scaffold_learning.cli.run_experiment.load_datasets")
@patch("scaffold_learning.cli.run_experiment.create_scoring_function")
@patch("scaffold_learning.cli.run_experiment.LLMFactory")
@patch("scaffold_learning.cli.run_experiment.build_docker_image")
def test_strategy_model_passed_to_experiment_runner(
    mock_build,
    mock_llm_factory,
    mock_scoring,
    mock_load,
    mock_runner,
    mock_hydra_config,
):
    """Test that strategy model is correctly passed to ExperimentRunner."""
    # Mock the necessary returns
    mock_load.return_value = {"train": [], "valid": [], "test": []}
    mock_scoring.return_value = lambda x, y: 0.0

    # Create mock LLM instances
    mock_scaffolder_llm = Mock()
    mock_strategy_llm = Mock()
    mock_llm_factory.create_llm.side_effect = [mock_scaffolder_llm, mock_strategy_llm]

    mock_runner_instance = mock_runner.return_value
    mock_runner_instance.run.return_value = ("scaffold-0", 0.9, None)

    # Mock HydraConfig output directory
    mock_hydra_instance = Mock()
    mock_hydra_instance.runtime.output_dir = "/tmp/test_output"
    mock_hydra_config.get.return_value = mock_hydra_instance

    # Create temporary data directory
    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir)
        (data_dir / "train.jsonl").touch()
        (data_dir / "valid.jsonl").touch()
        (data_dir / "test.jsonl").touch()

        # Create Hydra config with strategy model
        cfg = DictConfig(
            {
                "experiment_name": "strategy_test",
                "data_dir": str(data_dir),
                "domain": "test_domain",
                "domain_params": {},
                "num_iterations": 1,
                "scaffolds_per_iter": 1,
                "initial_scaffolds": 1,
                "num_validation_examples": 1,
                "num_training_examples": 1,
                "scaffolder": "haiku",
                "executor": "haiku",
                "strategy": "gpt-4o",
                "strategy_batch_size": None,
                "show_scoring_function": False,
                "suggest_hack": "none",
                "train_seed": 42,
                "valid_seed": 42,
                "test_seed": 42,
                "num_test_examples": 0,
                "scaffold_timeout": 120,
                "max_generate_workers": 1,
                "max_execute_workers": 1,
                "thinking_budget": 5000,
                "base_dir": str(tmpdir),
                "build_docker": False,
                "model_specs": {
                    "haiku": {"thinking_budget": 0},
                    "gpt-4o": {"thinking_budget": 3000},
                },
            }
        )

        main(cfg)

        # Verify ExperimentRunner was called with strategy_llm
        mock_runner.assert_called_once()
        call_args = mock_runner.call_args

        # ExperimentRunner is called with positional args:
        # (config, data, scoring_fn, scaffolder_llm, output_dir, strategy_llm, scoring_fn_code)
        # Check that strategy_llm (6th positional arg) was passed
        assert len(call_args[0]) >= 6
        assert call_args[0][5] == mock_strategy_llm

        # Verify both scaffolder and strategy LLMs were created
        assert mock_llm_factory.create_llm.call_count == 2

        # Check that scaffolder was created with thinking budget
        first_call = mock_llm_factory.create_llm.call_args_list[0]
        assert first_call[0][0] == "haiku"
        assert first_call[1]["thinking_budget_tokens"] == 5000  # Uses override

        # Check that strategy was created with thinking budget
        second_call = mock_llm_factory.create_llm.call_args_list[1]
        assert second_call[0][0] == "gpt-4o"
        assert second_call[1]["thinking_budget_tokens"] == 5000  # Uses override
