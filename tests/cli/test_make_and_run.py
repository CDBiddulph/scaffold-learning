"""Tests for the unified scaffold make and run CLI."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from argparse import ArgumentError
import tempfile
import shutil

from scaffold_learning.cli.make_and_run import parse_args, ScaffoldConfig


class TestArgumentParsing:
    """Test argument parsing for different command modes."""

    def test_parse_args_make_baseline(self):
        """Test parsing make with baseline flag."""
        args = parse_args(
            [
                "make",
                "--baseline",
                "--data-dir",
                "data/crosswords",
                "--name",
                "my-baseline",
                "--num-train-examples",
                "5",
                "--show-scoring-function",
            ]
        )

        assert args.do_make is True
        assert args.do_run is False
        assert args.baseline is True
        assert args.data_dir == Path("data/crosswords")
        assert args.name == "my-baseline"
        assert args.num_train_examples == 5
        assert args.show_scoring_function is True
        assert args.scaffolder_model is None
        assert args.task is None

    def test_parse_args_make_from_examples(self):
        """Test parsing make from examples with scaffolder model."""
        args = parse_args(
            [
                "make",
                "--data-dir",
                "data/crosswords",
                "--scaffolder-model",
                "gpt-4o",
                "--name",
                "from-examples",
                "--num-train-examples",
                "10",
                "--train-seed",
                "42",
            ]
        )

        assert args.do_make is True
        assert args.do_run is False
        assert args.baseline is False
        assert args.data_dir == Path("data/crosswords")
        assert args.scaffolder_model == "gpt-4o"
        assert args.name == "from-examples"
        assert args.num_train_examples == 10
        assert args.train_seed == 42
        assert args.task is None

    def test_parse_args_make_from_task(self):
        """Test parsing make from task description."""
        args = parse_args(
            [
                "make",
                "--task",
                "solve crosswords",
                "--scaffolder-model",
                "haiku",
                "--name",
                "task-based",
                "--suggest-hack",
            ]
        )

        assert args.do_make is True
        assert args.do_run is False
        assert args.task == "solve crosswords"
        assert args.scaffolder_model == "haiku"
        assert args.name == "task-based"
        assert args.suggest_hack is True
        assert args.baseline is False
        assert args.data_dir is None
        assert args.num_train_examples is None

    def test_parse_args_run_only_single_input(self):
        """Test parsing run with single input string."""
        args = parse_args(
            [
                "run",
                "--name",
                "existing-scaffold",
                "--base-dir",
                "scaffolds/generated",
                "--executor-model",
                "gpt-4o",
                "--input",
                "test input",
                "--timeout",
                "300",
            ]
        )

        assert args.do_make is False
        assert args.do_run is True
        assert args.name == "existing-scaffold"
        assert args.base_dir == Path("scaffolds/generated")
        assert args.executor_model == "gpt-4o"
        assert args.input_string == "test input"
        assert args.timeout == 300
        assert args.data_dir is None
        assert args.domain is None

    def test_parse_args_run_only_file_input(self):
        """Test parsing run with file input."""
        args = parse_args(
            [
                "run",
                "--name",
                "scaffold",
                "--base-dir",
                "experiments/exp_123/scaffolds",
                "--executor-model",
                "haiku",
                "--file",
                "input.txt",
                "--thinking-budget",
                "1000",
            ]
        )

        assert args.do_run is True
        assert args.input_file == Path("input.txt")
        assert args.thinking_budget == 1000
        assert args.input_string is None

    def test_parse_args_run_only_dataset_eval(self):
        """Test parsing run with dataset evaluation."""
        args = parse_args(
            [
                "run",
                "--name",
                "scaffold",
                "--base-dir",
                "scaffolds/baselines",
                "--executor-model",
                "gpt-4o",
                "--data-dir",
                "data/crosswords",
                "--num-test-examples",
                "20",
                "--domain",
                "crosswords",
                "--test-seed",
                "123",
            ]
        )

        assert args.do_run is True
        assert args.data_dir == Path("data/crosswords")
        assert args.num_test_examples == 20
        assert args.domain == "crosswords"
        assert args.test_seed == 123
        assert args.input_string is None
        assert args.input_file is None

    def test_parse_args_make_run_combined(self):
        """Test parsing combined make and run."""
        args = parse_args(
            [
                "make",
                "run",
                "--baseline",
                "--data-dir",
                "data/test",
                "--name",
                "combined",
                "--num-train-examples",
                "3",
                "--num-test-examples",
                "5",
                "--executor-model",
                "haiku",
                "--domain",
                "crosswords",
                "--train-seed",
                "123",
                "--test-seed",
                "456",
                "--timeout",
                "300",
            ]
        )

        assert args.do_make is True
        assert args.do_run is True
        assert args.baseline is True
        assert args.name == "combined"
        assert args.num_train_examples == 3
        assert args.num_test_examples == 5
        assert args.executor_model == "haiku"
        assert args.domain == "crosswords"

    def test_parse_args_no_build_flag(self):
        """Test --no-build flag parsing."""
        args = parse_args(
            [
                "run",
                "--name",
                "test",
                "--base-dir",
                "scaffolds/generated",
                "--executor-model",
                "gpt-4o",
                "--input",
                "test",
                "--no-build",
            ]
        )

        assert args.no_build is True

    def test_parse_args_console_output_flag(self):
        """Test --console-output flag parsing."""
        args = parse_args(
            [
                "run",
                "--name",
                "test",
                "--base-dir",
                "scaffolds/generated",
                "--executor-model",
                "gpt-4o",
                "--input",
                "test",
                "--timeout",
                "120",
                "--console-output",
            ]
        )

        assert args.console_output is True

    def test_parse_args_console_output_default_false(self):
        """Test console_output defaults to False."""
        args = parse_args(
            [
                "run",
                "--name",
                "test",
                "--base-dir",
                "scaffolds/generated",
                "--executor-model",
                "gpt-4o",
                "--input",
                "test",
                "--timeout",
                "120",
            ]
        )

        assert args.console_output is False


class TestArgumentValidation:
    """Test validation of argument combinations."""

    def test_validate_baseline_requires_data_dir(self):
        """Test that baseline mode requires data-dir."""
        from scaffold_learning.cli.make_and_run import _validate_arguments
        
        config = ScaffoldConfig(
            do_make=True,
            name="test",
            baseline=True,
            # Missing data_dir
        )
        
        with pytest.raises(ValueError, match="Must specify exactly one generation mode"):
            _validate_arguments(config)

    def test_validate_scaffolder_model_forbidden_with_baseline(self):
        """Test that scaffolder-model is forbidden with baseline."""
        from scaffold_learning.cli.make_and_run import _validate_arguments
        
        config = ScaffoldConfig(
            do_make=True,
            name="test",
            baseline=True,
            data_dir=Path("data"),
            scaffolder_model="gpt-4o",  # Should be forbidden
            num_train_examples=5,
            train_seed=42,
        )
        
        with pytest.raises(ValueError, match="--scaffolder-model cannot be used with --baseline"):
            _validate_arguments(config)

    def test_validate_domain_required_for_show_scoring_function(self):
        """Test that domain is required when using --show-scoring-function with --data-dir."""
        from scaffold_learning.cli.make_and_run import _validate_arguments
        
        config = ScaffoldConfig(
            do_make=True,
            name="test",
            baseline=True,
            data_dir=Path("data"),
            num_train_examples=5,
            train_seed=42,
            show_scoring_function=True,
            # Missing domain
        )
        
        with pytest.raises(ValueError, match="--domain is required when using --show-scoring-function"):
            _validate_arguments(config)

    def test_validate_domain_required_for_run_evaluation(self):
        """Test that domain is required when using --data-dir for run."""
        from scaffold_learning.cli.make_and_run import _validate_arguments
        
        config = ScaffoldConfig(
            do_run=True,
            name="test",
            base_dir=Path("scaffolds"),
            executor_model="gpt-4o",
            data_dir=Path("data"),
            num_test_examples=5,
            test_seed=42,
            timeout=120,
            # Missing domain
        )
        
        with pytest.raises(ValueError, match="--domain is required when using --data-dir for run"):
            _validate_arguments(config)

    def test_validate_train_seed_required_with_data_dir(self):
        """Test that train-seed is required when using --data-dir for make."""
        from scaffold_learning.cli.make_and_run import _validate_arguments
        
        config = ScaffoldConfig(
            do_make=True,
            name="test",
            baseline=True,
            data_dir=Path("data"),
            num_train_examples=5,
            # Missing train_seed
        )
        
        with pytest.raises(ValueError, match="--train-seed is required when using --data-dir"):
            _validate_arguments(config)

    def test_validate_test_seed_required_with_data_dir_run(self):
        """Test that test-seed is required when using --data-dir for run."""
        from scaffold_learning.cli.make_and_run import _validate_arguments
        
        config = ScaffoldConfig(
            do_run=True,
            name="test",
            base_dir=Path("scaffolds"),
            executor_model="gpt-4o",
            data_dir=Path("data"),
            num_test_examples=5,
            domain="crosswords",
            timeout=120,
            # Missing test_seed
        )
        
        with pytest.raises(ValueError, match="--test-seed is required when using --data-dir for run"):
            _validate_arguments(config)

    def test_validate_timeout_required_for_run(self):
        """Test that timeout is required for run mode."""
        from scaffold_learning.cli.make_and_run import _validate_arguments
        
        config = ScaffoldConfig(
            do_run=True,
            name="test",
            base_dir=Path("scaffolds"),
            executor_model="gpt-4o",
            input_string="test input",
            # Missing timeout
        )
        
        with pytest.raises(ValueError, match="--timeout is required for run"):
            _validate_arguments(config)

    def test_validate_exactly_one_generation_mode(self):
        """Test that exactly one generation mode is required for make."""
        from scaffold_learning.cli.make_and_run import _validate_arguments
        
        # No generation mode
        config = ScaffoldConfig(
            do_make=True,
            name="test",
        )
        
        with pytest.raises(ValueError, match="Must specify exactly one generation mode"):
            _validate_arguments(config)

    def test_validate_run_requires_input(self):
        """Test that run requires exactly one input method."""
        from scaffold_learning.cli.make_and_run import _validate_arguments
        
        config = ScaffoldConfig(
            do_run=True,
            name="test",
            base_dir=Path("scaffolds"),
            executor_model="gpt-4o",
            timeout=120,
            # No input method specified
        )
        
        with pytest.raises(ValueError, match="Must specify exactly one input mode"):
            _validate_arguments(config)

    def test_validate_console_output_only_with_run(self):
        """Test that console-output can only be used with run mode."""
        from scaffold_learning.cli.make_and_run import _validate_arguments
        
        config = ScaffoldConfig(
            do_make=True,
            name="test",
            baseline=True,
            data_dir=Path("data"),
            num_train_examples=5,
            train_seed=42,
            console_output=True,  # Should be forbidden in make-only mode
        )
        
        with pytest.raises(ValueError, match="--console-output can only be used with run mode"):
            _validate_arguments(config)

    def test_validate_valid_configurations_pass(self):
        """Test that valid configurations pass validation."""
        from scaffold_learning.cli.make_and_run import _validate_arguments
        
        # Valid baseline make
        config = ScaffoldConfig(
            do_make=True,
            name="test",
            baseline=True,
            data_dir=Path("data"),
            num_train_examples=5,
            train_seed=42,
        )
        _validate_arguments(config)  # Should not raise
        
        # Valid run with evaluation
        config = ScaffoldConfig(
            do_run=True,
            name="test",
            base_dir=Path("scaffolds"),
            executor_model="gpt-4o",
            data_dir=Path("data"),
            num_test_examples=5,
            test_seed=42,
            domain="crosswords",
            timeout=120,
        )
        _validate_arguments(config)  # Should not raise
        
        # Valid run with single input
        config = ScaffoldConfig(
            do_run=True,
            name="test",
            base_dir=Path("scaffolds"),
            executor_model="gpt-4o",
            input_string="test input",
            timeout=120,
        )
        _validate_arguments(config)  # Should not raise
        
        # Valid run with console output
        config = ScaffoldConfig(
            do_run=True,
            name="test",
            base_dir=Path("scaffolds"),
            executor_model="gpt-4o",
            input_string="test input",
            timeout=120,
            console_output=True,
        )
        _validate_arguments(config)  # Should not raise


class TestHelperFunctions:
    """Test helper functions for directory management and input handling."""

    def test_infer_base_dir_baseline(self):
        """Test base directory inference for baseline scaffolds."""
        from scaffold_learning.cli.make_and_run import _infer_base_dir

        config = ScaffoldConfig(
            do_make=True,
            do_run=False,
            baseline=True,
            name="test",
            data_dir=Path("data"),
            num_train_examples=5,
            # Other fields with defaults...
        )

        base_dir = _infer_base_dir(config)
        assert base_dir == Path("scaffolds/baselines")

    def test_infer_base_dir_generated(self):
        """Test base directory inference for generated scaffolds."""
        from scaffold_learning.cli.make_and_run import _infer_base_dir

        config = ScaffoldConfig(
            do_make=True,
            do_run=False,
            baseline=False,
            name="test",
            scaffolder_model="gpt-4o",
            # Other fields...
        )

        base_dir = _infer_base_dir(config)
        assert base_dir == Path("scaffolds/generated")

    def test_setup_run_directory(self):
        """Test creation of timestamped run directory."""
        from scaffold_learning.cli.make_and_run import _setup_run_directory

        with tempfile.TemporaryDirectory() as tmpdir:
            scaffold_dir = Path(tmpdir) / "test-scaffold"
            scaffold_dir.mkdir()

            run_dir = _setup_run_directory(scaffold_dir)

            assert run_dir.parent == scaffold_dir / "runs"
            assert run_dir.name.startswith("eval_")
            assert run_dir.exists()

    def test_get_input_string_from_string(self):
        """Test getting input from string argument."""
        from scaffold_learning.cli.make_and_run import _get_input_string

        config = ScaffoldConfig(
            do_run=True,
            input_string="test input",
            input_file=None,
            # Other fields...
        )

        result = _get_input_string(config)
        assert result == "test input"

    def test_get_input_string_from_file(self):
        """Test getting input from file."""
        from scaffold_learning.cli.make_and_run import _get_input_string

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("file content")
            f.flush()

            config = ScaffoldConfig(
                do_run=True,
                input_string=None,
                input_file=Path(f.name),
                # Other fields...
            )

            result = _get_input_string(config)
            assert result == "file content"

            Path(f.name).unlink()


class TestIntegrationWorkflows:
    """Test complete workflows combining make and run operations."""

    @patch("scaffold_learning.cli.make_and_run.LLMFactory")
    @patch("scaffold_learning.cli.make_and_run.build_docker_image")
    @patch("scaffold_learning.cli.make_and_run.execute_scaffold")
    def test_make_run_baseline_workflow(
        self, mock_execute, mock_docker, mock_llm_factory
    ):
        """Test creating and running a baseline scaffold."""
        # Setup mocks
        mock_docker.return_value = None
        mock_execute.return_value = Mock(
            output="test output", error_message=None, execution_time=1.5
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test data files
            data_dir = Path(tmpdir) / "data"
            data_dir.mkdir()

            train_file = data_dir / "train.jsonl"
            train_file.write_text(
                '{"input": "test1", "scoring_data": {"solution": "answer1"}}\n'
            )

            test_file = data_dir / "test.jsonl"
            test_file.write_text(
                '{"input": "test2", "scoring_data": {"solution": "answer2"}}\n'
            )

            # This would be the full integration test
            # Implementation depends on the actual make_and_run module
            pass

    @patch("scaffold_learning.cli.make_and_run.LLMFactory")
    @patch("scaffold_learning.cli.make_and_run.generate_scaffold")
    def test_make_from_task_workflow(self, mock_generate, mock_llm_factory):
        """Test generating scaffold from task description."""
        # Setup mocks
        mock_llm = Mock()
        mock_llm_factory.create_llm.return_value = mock_llm
        mock_generate.return_value = Mock(
            code='def process_input(input_string): return "result"', metadata=Mock()
        )

        # This would test the make-only workflow
        pass

    def test_run_existing_scaffold_single_input(self):
        """Test running an existing scaffold with single input."""
        # This would test run-only workflow with single input
        pass

    def test_run_experiment_scaffold(self):
        """Test running a scaffold from experiments directory."""
        # This would test running scaffolds from experiments structure
        pass
