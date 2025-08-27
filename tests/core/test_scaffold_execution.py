import re
import json
from unittest.mock import Mock, patch
from pathlib import Path
import tempfile
from scaffold_learning.core.scaffold_execution import (
    execute_scaffolds,
    _execute_scaffold,
)
from scaffold_learning.core.data_structures import ScaffoldExecutionTask
from scaffold_learning.core.data_structures import ScaffoldExecutionResult
from scaffold_learning.core.experiment_files import ExperimentFileManager
from scaffold_learning.core.data_structures import ScaffoldResult, ScaffoldMetadata


class TestScaffoldExecution:
    def create_test_scaffold(self, temp_dir: str, scaffold_id: str = "test-scaffold"):
        """Helper to create a test scaffold and file manager."""
        experiment_dir = Path(temp_dir) / "experiment"
        file_manager = ExperimentFileManager(experiment_dir)

        metadata = ScaffoldMetadata(
            created_at="2024-01-01T12:00:00",
            parent_scaffold_id=None,
            iteration=0,
        )
        scaffold_result = ScaffoldResult(
            code="def process_input(s): return s", metadata=metadata
        )
        file_manager.save_scaffold(scaffold_id=scaffold_id, result=scaffold_result)

        return file_manager

    def execute_single_scaffold(
        self, file_manager, scaffold_id="test-scaffold", **kwargs
    ):
        """Helper to execute a single scaffold using the new API."""
        task = ScaffoldExecutionTask(
            scaffold_dir=str(file_manager.get_scaffold_dir(scaffold_id)),
            log_file_path=str(
                file_manager.get_new_execution_log_path(0, scaffold_id, "train")
            ),
            input_string=kwargs.get("input_string", "test input"),
            model_spec=kwargs.get("model_spec", "mock"),
            timeout=kwargs.get("timeout", 120),
            console_output=kwargs.get("console_output", False),
            thinking_budget_tokens=kwargs.get("thinking_budget_tokens", 0),
        )
        results = execute_scaffolds([task], max_workers=1)
        return results[0]

    def create_mock_hostname_result(self):
        """Helper to create a mock hostname detection result."""
        hostname_result = Mock()
        hostname_result.returncode = 0
        hostname_result.stdout = "192.168.1.100 "
        return hostname_result

    def create_mock_process(
        self, stdout_lines, stderr_lines, returncode=0, poll_sequence=None
    ):
        """Helper to create a mock process with streaming behavior."""
        mock_process = Mock()
        mock_process.returncode = returncode

        # Default poll sequence: running for len(lines)-1 times, then finished
        if poll_sequence is None:
            poll_sequence = [None] * (max(len(stdout_lines), len(stderr_lines)) - 1) + [
                returncode
            ]

        # Make poll() handle unlimited calls using a custom function
        # The streaming loop may call poll() many times due to timeout checks
        poll_count = [0]  # Use list so inner function can modify

        def mock_poll():
            if poll_count[0] < len(poll_sequence):
                result = poll_sequence[poll_count[0]]
                poll_count[0] += 1
                return result
            else:
                # Return final value indefinitely
                return poll_sequence[-1]

        mock_process.poll.side_effect = mock_poll

        # Add empty string to end lines if not present (EOF marker)
        if stdout_lines and stdout_lines[-1] != "":
            stdout_lines = stdout_lines + [""]
        if stderr_lines and stderr_lines[-1] != "":
            stderr_lines = stderr_lines + [""]

        mock_process.stdout.readline.side_effect = stdout_lines
        mock_process.stderr.readline.side_effect = stderr_lines

        return mock_process

    def run_execute_scaffold_test(
        self,
        stdout_lines,
        stderr_lines,
        returncode=0,
        poll_sequence=None,
        timeout=120,
        model_spec="mock",
    ):
        """Helper to run execute_scaffold with common test setup"""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_manager = self.create_test_scaffold(temp_dir)

            mock_process = self.create_mock_process(
                stdout_lines=stdout_lines,
                stderr_lines=stderr_lines,
                returncode=returncode,
                poll_sequence=poll_sequence,
            )

            # Create a time mock that handles unlimited calls
            time_counter = [0]  # Use list so inner function can modify it

            def mock_time():
                current_time = time_counter[0] * 0.1
                time_counter[0] += 1
                return current_time

            # Create a mock results directory and file for successful executions
            def mock_mkdtemp():
                results_dir = Path(temp_dir) / "mock_results"
                results_dir.mkdir()
                # Create results file if execution is successful
                if returncode == 0 and model_spec != "human/human":
                    results_file = results_dir / "results.json"
                    output = "".join(stdout_lines).strip()
                    results_data = {
                        "output": output,
                        "execution_time": 1.5,  # Mock execution time
                    }
                    with open(results_file, "w") as f:
                        json.dump(results_data, f)
                return str(results_dir)

            with patch(
                "subprocess.run", return_value=self.create_mock_hostname_result()
            ):
                with patch("subprocess.Popen", return_value=mock_process):
                    with patch("time.time", side_effect=mock_time):
                        with patch("tempfile.mkdtemp", side_effect=mock_mkdtemp):
                            result = self.execute_single_scaffold(
                                file_manager,
                                input_string="test input",
                                model_spec=model_spec,
                                timeout=timeout,
                            )

            return result, mock_process

    def test_execute_scaffold_success(self):
        result, _ = self.run_execute_scaffold_test(
            stdout_lines=["result output"], stderr_lines=[]
        )

        assert isinstance(result, ScaffoldExecutionResult)
        assert result.output.strip() == "result output"
        assert result.stderr.strip() == ""
        assert result.error_message is None
        assert result.execution_time == 1.5  # From mock results file

    def test_execute_scaffold_with_timeout(self):
        result, _ = self.run_execute_scaffold_test(
            stdout_lines=["Starting\n", "Processing\n"],
            stderr_lines=[""],
            returncode=124,  # Exit code 124 indicates timeout from timeout command
            poll_sequence=[None, None, 124],  # Process finishes with timeout exit code
            timeout=2,
        )

        assert "Starting" in result.output
        assert result.error_message is not None
        assert result.error_message == "Execution timed out after 2 seconds"

    def test_execute_scaffold_with_error(self):
        result, _ = self.run_execute_scaffold_test(
            stdout_lines=[], stderr_lines=["Error: syntax error"], returncode=1
        )

        assert (
            result.error_message
            == "Error from scaffold (exit code 1):\nError: syntax error"
        )
        assert result.stderr.strip() == "Error: syntax error"
        assert result.execution_time == 0.0  # No timing info available for early errors

    def test_execute_scaffold_multiple_output_lines(self):
        result, _ = self.run_execute_scaffold_test(
            stdout_lines=["Line 1\n", "Line 2\n", "Line 3\n"],
            stderr_lines=["Error 1\n", "Error 2\n"],
        )

        assert result.output.strip() == "Line 1\nLine 2\nLine 3"
        assert result.stderr.strip() == "Error 1\nError 2"

    def test_execute_scaffold_docker_command_construction(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_manager = self.create_test_scaffold(temp_dir)

            mock_process = self.create_mock_process(["output"], [])

            with patch(
                "subprocess.run", return_value=self.create_mock_hostname_result()
            ):
                with patch("subprocess.Popen") as mock_popen:
                    mock_popen.return_value = mock_process

                    with patch("time.time", side_effect=[0.0, 0.0, 0.1, 0.2, 0.3, 1.0]):
                        self.execute_single_scaffold(
                            file_manager,
                            input_string="test input",
                            model_spec="gpt-4o",
                            timeout=300,
                        )

                call_args = mock_popen.call_args[0][0]
                assert "docker" in call_args
                assert "run" in call_args
                assert "--rm" in call_args

                command_str = " ".join(call_args)
                assert "/workspace/scaffold:ro" in command_str
                # Check for security constraints
                assert "--memory" in call_args
                assert "--cpus" in call_args
                assert "--read-only" in call_args
                assert "--pids-limit" in call_args

    def test_execute_scaffold_logs_saved_correctly(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_manager = self.create_test_scaffold(temp_dir)

            mock_process = self.create_mock_process(["test output"], ["test stderr"])

            with patch(
                "subprocess.run", return_value=self.create_mock_hostname_result()
            ):
                with patch("subprocess.Popen", return_value=mock_process):
                    with patch(
                        "time.time", side_effect=[0.0, 0.0, 0.1, 0.2, 0.3, 0.4, 2.0]
                    ):
                        self.execute_single_scaffold(
                            file_manager,
                            input_string="test input",
                            model_spec="mock",
                        )

            logs_dir = (
                Path(temp_dir) / "experiment" / "logs" / "0" / "test-scaffold" / "train"
            )
            log_files = list(logs_dir.glob("*.log"))
            assert len(log_files) == 1

            log_content = log_files[0].read_text()
            expected_content = ["test input", "test output", "test stderr", "mock/mock"]
            assert all(content in log_content for content in expected_content)

    def test_execute_scaffold_environment_variables(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_manager = self.create_test_scaffold(temp_dir)
            mock_process = self.create_mock_process(["output"], [])

            with patch(
                "subprocess.run", return_value=self.create_mock_hostname_result()
            ):
                with patch("subprocess.Popen") as mock_popen:
                    mock_popen.return_value = mock_process
                    with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
                        with patch(
                            "time.time", side_effect=[0.0, 0.0, 0.1, 0.2, 0.3, 1.0]
                        ):
                            self.execute_single_scaffold(
                                file_manager,
                                input_string="test input",
                                model_spec="mock",
                            )

                call_args = mock_popen.call_args[0][0]
                assert any("OPENAI_API_KEY" in str(arg) for arg in call_args)

    def test_execute_scaffold_custom_timeout(self):
        result, _ = self.run_execute_scaffold_test(
            stdout_lines=["output"], stderr_lines=[], timeout=600
        )

        assert result.output.strip() == "output"

    def test_execute_scaffold_console_output_mode(self):
        """Test that console_output=True creates log file with streaming format"""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_manager = self.create_test_scaffold(temp_dir)
            mock_process = self.create_mock_process(
                ["Line 1\n", "Line 2\n"], ["Error 1\n"]
            )

            with patch(
                "subprocess.run", return_value=self.create_mock_hostname_result()
            ):
                with patch("subprocess.Popen", return_value=mock_process):
                    with patch(
                        "time.time",
                        side_effect=[0.0, 0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 1.0],
                    ):
                        result = self.execute_single_scaffold(
                            file_manager,
                            input_string="test input",
                            model_spec="mock",
                            console_output=True,
                        )

            # Should still return correct result
            assert result.output.strip() == "Line 1\nLine 2"
            assert result.stderr.strip() == "Error 1"

            # Should create streaming log file (not through file_manager)
            logs_dir = Path(temp_dir) / "experiment" / "logs" / "0" / "test-scaffold"
            # Log files are now in run_type subdirectory
            train_logs_dir = logs_dir / "train"
            log_files = list(train_logs_dir.glob("*.log"))
            assert len(log_files) == 1

            log_content = log_files[0].read_text()
            expected_pattern = r"""=== Scaffold Execution Log ===
Model: mock/mock
Timestamp: \d{8}_\d{6}

=== INPUT ===
test input

=== STDOUT ===
Line 1
Line 2

=== STDERR ===
Error 1
"""
            assert re.match(expected_pattern, log_content)

    def test_execute_scaffold_human_interactive_mode(self):
        """Test that human/human model uses interactive Docker mode"""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_manager = self.create_test_scaffold(temp_dir)

            with patch("subprocess.run") as mock_run:
                # Mock the hostname detection call first, then the Docker execution call
                docker_result = Mock()
                docker_result.returncode = 0

                mock_run.side_effect = [
                    self.create_mock_hostname_result(),
                    docker_result,
                ]

                with patch("time.time", side_effect=[0.0, 0.0, 0.1, 0.2, 0.3, 1.0]):
                    result = self.execute_single_scaffold(
                        file_manager,
                        input_string="test input",
                        model_spec="human",
                    )

            # Should call subprocess.run twice: once for hostname, once for Docker
            assert mock_run.call_count == 2
            # First call should be hostname detection
            first_call_args = mock_run.call_args_list[0][0][0]
            assert first_call_args == ["hostname", "-I"]
            # Second call should be Docker command
            second_call_args = mock_run.call_args_list[1][0][0]
            assert "docker" in second_call_args

            # Docker command should include -it flags
            call_args = mock_run.call_args[0][0]
            assert "-it" in call_args

            # Should return result with placeholder output
            assert isinstance(result, ScaffoldExecutionResult)
            assert (
                result.output
                == "Note: Human model execution - no output captured\nUser interaction occurred directly in terminal."
            )
            assert result.error_message is None

            # Check that log file contains the stdout section
            logs_dir = Path(temp_dir) / "experiment" / "logs" / "0" / "test-scaffold"
            # Log files are now in run_type subdirectory
            train_logs_dir = logs_dir / "train"
            log_files = list(train_logs_dir.glob("*.log"))
            assert len(log_files) == 1

            expected_pattern = r"""=== Scaffold Execution Log ===
Model: human/human
Timestamp: \d{8}_\d{6}

=== INPUT ===
test input

=== STDOUT ===
Note: Human model execution - no output captured
User interaction occurred directly in terminal\."""
            assert re.match(expected_pattern, log_files[0].read_text())


class TestParallelScaffoldExecution:
    def test_execute_scaffolds_sequential(self):
        """Test execute_scaffolds with max_workers=1 (sequential)"""

        # Mock _execute_scaffold to return predictable results
        with patch(
            "scaffold_learning.core.scaffold_execution._execute_scaffold"
        ) as mock_execute:
            # Set up mock results
            mock_results = [
                ScaffoldExecutionResult(
                    output=f"output{i}",
                    stderr="",
                    error_message=None,
                    execution_time=0.1 * i,
                )
                for i in range(3)
            ]
            mock_execute.side_effect = mock_results

            # Create execution tasks
            tasks = [
                ScaffoldExecutionTask(
                    scaffold_dir=f"/path/to/scaffold{i}",
                    log_file_path=f"/path/to/log{i}.log",
                    input_string=f"input{i}",
                    model_spec="mock",
                    timeout=120,
                    console_output=False,
                    thinking_budget_tokens=0,
                )
                for i in range(3)
            ]

            # Execute
            results = execute_scaffolds(tasks, max_workers=1)

            # Verify results
            assert len(results) == 3
            for i, result in enumerate(results):
                assert result.output == f"output{i}"
                assert result.execution_time == 0.1 * i

            # Verify calls were made sequentially
            assert mock_execute.call_count == 3
