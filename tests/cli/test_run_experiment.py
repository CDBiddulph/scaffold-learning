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
