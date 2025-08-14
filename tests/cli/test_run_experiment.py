"""Tests for run_experiment CLI, specifically domain-param parsing."""

import pytest
from unittest.mock import patch, Mock
from pathlib import Path
import tempfile



@patch("scaffold_learning.cli.run_experiment.ExperimentRunner")
@patch("scaffold_learning.cli.run_experiment.load_datasets")
@patch("scaffold_learning.cli.run_experiment.create_scoring_function")
@patch("scaffold_learning.cli.run_experiment.LLMFactory")
@patch("scaffold_learning.cli.run_experiment.build_docker_image")
def test_domain_params_passed_to_scoring_function(
    mock_build, mock_llm_factory, mock_scoring, mock_load, mock_runner
):
    """Test that domain params are correctly passed to create_scoring_function."""
    # Mock the necessary returns
    mock_load.return_value = {"train": [], "valid": []}
    mock_scoring.return_value = lambda x, y: 0.0
    mock_llm_factory.create_llm.return_value = Mock()
    mock_runner_instance = mock_runner.return_value
    mock_runner_instance.run.return_value = ("scaffold-0", 0.5)

    # Create temporary data directory
    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir)
        (data_dir / "train.jsonl").touch()
        (data_dir / "valid.jsonl").touch()

        # Test with domain params
        test_args = [
            "run_experiment.py",
            "test_experiment",
            str(data_dir),
            "--domain",
            "reward-model",
            "--domain-param",
            "rm=llm:haiku",
            "--domain-param",
            "temperature=0.7",
            "--no-build",
        ]

        with patch("sys.argv", test_args):
            from scaffold_learning.cli.run_experiment import main

            main()

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


@patch("scaffold_learning.cli.run_experiment.ExperimentRunner")
@patch("scaffold_learning.cli.run_experiment.load_datasets")
@patch("scaffold_learning.cli.run_experiment.create_scoring_function")
@patch("scaffold_learning.cli.run_experiment.LLMFactory")
@patch("scaffold_learning.cli.run_experiment.build_docker_image")
def test_crosswords_domain_param_mode(
    mock_build, mock_llm_factory, mock_scoring, mock_load, mock_runner
):
    """Test crosswords domain with mode parameter."""
    # Mock the necessary returns
    mock_load.return_value = {"train": [], "valid": []}
    mock_scoring.return_value = lambda x, y: 0.0
    mock_llm_factory.create_llm.return_value = Mock()
    mock_runner_instance = mock_runner.return_value
    mock_runner_instance.run.return_value = ("scaffold-0", 0.8)

    # Create temporary data directory
    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir)
        (data_dir / "train.jsonl").touch()
        (data_dir / "valid.jsonl").touch()

        # Test crosswords with lenient mode
        test_args = [
            "run_experiment.py",
            "crosswords_test",
            str(data_dir),
            "--domain",
            "crosswords",
            "--domain-param",
            "mode=lenient",
            "--no-build",
        ]

        with patch("sys.argv", test_args):
            from scaffold_learning.cli.run_experiment import main

            main()

        # Verify create_scoring_function was called with mode=lenient
        mock_scoring.assert_called_once()
        call_args = mock_scoring.call_args

        # Check positional argument
        assert call_args[0][0] == "crosswords"

        # Check keyword argument domain_params
        assert "domain_params" in call_args[1]
        assert call_args[1]["domain_params"] == {"mode": "lenient"}


@patch("scaffold_learning.cli.run_experiment.ExperimentRunner")
@patch("scaffold_learning.cli.run_experiment.load_datasets")
@patch("scaffold_learning.cli.run_experiment.create_scoring_function")
@patch("scaffold_learning.cli.run_experiment.LLMFactory")
@patch("scaffold_learning.cli.run_experiment.build_docker_image")
def test_strategy_model_passed_to_experiment_runner(
    mock_build, mock_llm_factory, mock_scoring, mock_load, mock_runner
):
    """Test that strategy model and thinking budget are correctly passed to ExperimentRunner."""
    # Mock the necessary returns
    mock_load.return_value = {"train": [], "valid": []}
    mock_scoring.return_value = lambda x, y: 0.0
    mock_llm_factory.create_llm.return_value = Mock()
    mock_runner_instance = mock_runner.return_value
    mock_runner_instance.run.return_value = ("scaffold-0", 0.9)

    # Create temporary data directory
    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir)
        (data_dir / "train.jsonl").touch()
        (data_dir / "valid.jsonl").touch()

        # Test with strategy model and thinking budget
        test_args = [
            "run_experiment.py",
            "strategy_test",
            str(data_dir),
            "--strategy-model",
            "gpt-4o",
            "--thinking-budget",
            "5000",
            "--no-build",
        ]

        with patch("sys.argv", test_args):
            from scaffold_learning.cli.run_experiment import main

            main()

        # Verify ExperimentRunner was called with strategy_llm
        mock_runner.assert_called_once()
        call_kwargs = mock_runner.call_args[1]
        
        assert "strategy_llm" in call_kwargs
        assert call_kwargs["strategy_llm"] is not None
        
        # Verify both scaffolder and strategy LLMs were created with thinking budget
        assert mock_llm_factory.create_llm.call_count == 2
        mock_llm_factory.create_llm.assert_any_call("haiku", thinking_budget_tokens=5000)
        mock_llm_factory.create_llm.assert_any_call("gpt-4o", thinking_budget_tokens=5000)
