import re
from unittest.mock import Mock, patch
from pathlib import Path
import tempfile
from scaffold_learning.core.scaffold_execution import execute_scaffold
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
        mock_process.poll.side_effect = poll_sequence

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
        time_values=None,
        model_spec="mock",
        expect_kill=False,
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

            if expect_kill:
                mock_process.kill = Mock()

            if time_values is None:
                # Provide enough time values for streaming loop
                # start_time + multiple checks during streaming + end_time
                num_lines = max(len(stdout_lines), len(stderr_lines))
                time_values = [0.0] + [i * 0.1 for i in range(1, num_lines + 4)]

            with patch("subprocess.Popen", return_value=mock_process):
                with patch("time.time", side_effect=time_values):
                    result = execute_scaffold(
                        scaffold_dir=file_manager.get_scaffold_dir("test-scaffold"),
                        log_file_path=file_manager.get_new_execution_log_path(
                            0, "test-scaffold", "train"
                        ),
                        input_string="test input",
                        model_spec=model_spec,
                        timeout=timeout,
                    )

            return result, mock_process

    def test_execute_scaffold_success(self):
        result, _ = self.run_execute_scaffold_test(
            stdout_lines=["result output"], stderr_lines=[], time_values=[0.0, 1.5]
        )

        assert isinstance(result, ScaffoldExecutionResult)
        assert result.output.strip() == "result output"
        assert result.stderr.strip() == ""
        assert result.error_message is None
        assert result.execution_time == 1.5

    def test_execute_scaffold_with_timeout(self):
        result, _ = self.run_execute_scaffold_test(
            stdout_lines=["Starting\n", "Processing\n"],
            stderr_lines=[""],
            returncode=124,  # Exit code 124 indicates timeout from timeout command
            poll_sequence=[None, None, 124],  # Process finishes with timeout exit code
            timeout=2,
            time_values=[0.0, 1.0, 2.0, 3.0, 4.0],  # Need extra value for end_time
            expect_kill=False,  # No need to kill, timeout command handles it
        )

        assert "Starting" in result.output
        assert result.error_message is not None
        assert result.error_message == "Execution timed out after 2 seconds"

    def test_execute_scaffold_with_error(self):
        result, _ = self.run_execute_scaffold_test(
            stdout_lines=[],
            stderr_lines=["Error: syntax error"],
            returncode=1,
            time_values=[0.0, 0.5],
        )

        assert (
            result.error_message
            == "Error from scaffold (exit code 1):\nError: syntax error"
        )
        assert result.stderr.strip() == "Error: syntax error"
        assert result.execution_time == 0.5

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

            with patch("subprocess.Popen") as mock_popen:
                mock_popen.return_value = mock_process

                with patch("time.time", side_effect=[0.0, 1.0]):
                    execute_scaffold(
                        scaffold_dir=file_manager.get_scaffold_dir("test-scaffold"),
                        log_file_path=file_manager.get_new_execution_log_path(
                            0, "test-scaffold", "train"
                        ),
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

            with patch("subprocess.Popen", return_value=mock_process):
                with patch("time.time", side_effect=[0.0, 2.0]):
                    execute_scaffold(
                        scaffold_dir=file_manager.get_scaffold_dir("test-scaffold"),
                        log_file_path=file_manager.get_new_execution_log_path(
                            0, "test-scaffold", "train"
                        ),
                        input_string="test input",
                        model_spec="mock",
                    )

            logs_dir = Path(temp_dir) / "experiment" / "logs" / "0" / "test-scaffold"
            log_files = list(logs_dir.glob("*.log"))
            assert len(log_files) == 1

            log_content = log_files[0].read_text()
            expected_content = ["test input", "test output", "test stderr", "mock/mock"]
            assert all(content in log_content for content in expected_content)

    def test_execute_scaffold_environment_variables(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_manager = self.create_test_scaffold(temp_dir)
            mock_process = self.create_mock_process(["output"], [])

            with patch("subprocess.Popen") as mock_popen:
                mock_popen.return_value = mock_process
                with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
                    with patch("time.time", side_effect=[0.0, 1.0]):
                        execute_scaffold(
                            scaffold_dir=file_manager.get_scaffold_dir("test-scaffold"),
                            log_file_path=file_manager.get_new_execution_log_path(
                                0, "test-scaffold", "train"
                            ),
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

            with patch("subprocess.Popen", return_value=mock_process):
                with patch("time.time", side_effect=[0.0, 0.1, 0.2, 0.3, 1.0]):
                    result = execute_scaffold(
                        scaffold_dir=file_manager.get_scaffold_dir("test-scaffold"),
                        log_file_path=file_manager.get_new_execution_log_path(
                            0, "test-scaffold", "train"
                        ),
                        input_string="test input",
                        model_spec="mock",
                        console_output=True,
                    )

            # Should still return correct result
            assert result.output.strip() == "Line 1\nLine 2"
            assert result.stderr.strip() == "Error 1"

            # Should create streaming log file (not through file_manager)
            logs_dir = Path(temp_dir) / "experiment" / "logs" / "0" / "test-scaffold"
            log_files = list(logs_dir.glob("*.log"))
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
                mock_run.return_value.returncode = 0
                with patch("time.time", side_effect=[0.0, 1.0]):
                    result = execute_scaffold(
                        scaffold_dir=file_manager.get_scaffold_dir("test-scaffold"),
                        log_file_path=file_manager.get_new_execution_log_path(
                            0, "test-scaffold", "train"
                        ),
                        input_string="test input",
                        model_spec="human",
                    )

            # Should use subprocess.run instead of subprocess.Popen
            mock_run.assert_called_once()

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
            log_files = list(logs_dir.glob("*.log"))
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
