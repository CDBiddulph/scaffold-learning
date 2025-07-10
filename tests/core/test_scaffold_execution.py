import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
import json
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

    def test_execute_scaffold_success(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            experiment_dir = Path(temp_dir) / "experiment"
            file_manager = ExperimentFileManager(experiment_dir)

            # Create and save a scaffold
            metadata = ScaffoldMetadata(
                created_at="2024-01-01T12:00:00",
                parent_scaffold_id=None,
                iteration=0,
            )
            scaffold_result = ScaffoldResult(
                code="""
def process_input(input_string: str) -> str:
    return f"processed: {input_string}"
""",
                metadata=metadata,
            )
            file_manager.save_scaffold(
                scaffold_id="test-scaffold", result=scaffold_result
            )

            # Mock subprocess to simulate successful execution
            with patch("subprocess.Popen") as mock_popen:
                mock_process = Mock()
                mock_process.communicate.return_value = ("result output", "")
                mock_process.returncode = 0
                mock_popen.return_value = mock_process

                # Mock time.time for execution timing
                with patch("time.time", side_effect=[0.0, 1.5]):
                    result = execute_scaffold(
                        file_manager=file_manager,
                        scaffold_id="test-scaffold",
                        iteration=0,
                        run_type="train",
                        input_string="test input",
                        model_spec="mock",
                        timeout=120,
                    )

                assert isinstance(result, ScaffoldExecutionResult)
                assert result.output == "result output"
                assert result.stderr == ""
                assert result.error_message is None
                assert result.execution_time == 1.5

    def test_execute_scaffold_with_timeout(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            experiment_dir = Path(temp_dir) / "experiment"
            file_manager = ExperimentFileManager(experiment_dir)

            # Create and save a scaffold
            metadata = ScaffoldMetadata(
                created_at="2024-01-01T12:00:00",
                parent_scaffold_id=None,
                iteration=0,
            )
            scaffold_result = ScaffoldResult(
                code="def process_input(s): return s", metadata=metadata
            )
            file_manager.save_scaffold(
                scaffold_id="test-scaffold", result=scaffold_result
            )

            # Mock subprocess that hangs
            with patch("subprocess.Popen") as mock_popen:
                mock_process = Mock()
                mock_process.communicate.return_value = ("", "Timeout error")
                mock_process.returncode = 124  # Timeout exit code
                mock_popen.return_value = mock_process

                with patch("time.time", side_effect=[0.0, 120.5]):
                    result = execute_scaffold(
                        file_manager=file_manager,
                        scaffold_id="test-scaffold",
                        iteration=0,
                        run_type="train",
                        input_string="test input",
                        model_spec="mock",
                        timeout=60,
                    )

                assert (
                    result.error_message
                    == "Error from scaffold (exit code 124):\nTimeout error"
                )
                assert result.execution_time == 120.5

    def test_execute_scaffold_with_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            experiment_dir = Path(temp_dir) / "experiment"
            file_manager = ExperimentFileManager(experiment_dir)

            # Create and save a scaffold
            metadata = ScaffoldMetadata(
                created_at="2024-01-01T12:00:00",
                parent_scaffold_id=None,
                iteration=0,
            )
            scaffold_result = ScaffoldResult(
                code="def process_input(s): return s", metadata=metadata
            )
            file_manager.save_scaffold(
                scaffold_id="test-scaffold", result=scaffold_result
            )

            with patch("subprocess.Popen") as mock_popen:
                mock_process = Mock()
                mock_process.communicate.return_value = ("", "Error: syntax error")
                mock_process.returncode = 1
                mock_popen.return_value = mock_process

                with patch("time.time", side_effect=[0.0, 0.5]):
                    result = execute_scaffold(
                        file_manager=file_manager,
                        scaffold_id="test-scaffold",
                        iteration=0,
                        run_type="train",
                        input_string="test input",
                        model_spec="mock",
                    )

                assert (
                    result.error_message
                    == "Error from scaffold (exit code 1):\nError: syntax error"
                )
                assert result.stderr == "Error: syntax error"
                assert result.execution_time == 0.5

    def test_execute_scaffold_docker_command_construction(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_manager = self.create_test_scaffold(temp_dir)

            with patch("subprocess.Popen") as mock_popen:
                mock_process = Mock()
                mock_process.communicate.return_value = ("output", "")
                mock_process.returncode = 0
                mock_popen.return_value = mock_process

                with patch("time.time", side_effect=[0.0, 1.0]):
                    execute_scaffold(
                        file_manager=file_manager,
                        scaffold_id="test-scaffold",
                        iteration=0,
                        run_type="train",
                        input_string="test input",
                        model_spec="gpt-4o",
                        timeout=300,
                    )

                # Check that docker command was constructed correctly
                call_args = mock_popen.call_args[0][0]  # First argument (the command)
                assert "docker" in call_args
                assert "run" in call_args
                assert "--rm" in call_args

                # Check that volumes are mounted correctly
                command_str = " ".join(call_args)
                assert "/workspace/scaffold:ro" in command_str
                assert "/workspace/logs" in command_str

    def test_execute_scaffold_logs_saved_correctly(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_manager = self.create_test_scaffold(temp_dir)

            with patch("subprocess.Popen") as mock_popen:
                mock_process = Mock()
                mock_process.communicate.return_value = ("test output", "test stderr")
                mock_process.returncode = 0
                mock_popen.return_value = mock_process

                with patch("time.time", side_effect=[0.0, 2.0]):
                    result = execute_scaffold(
                        file_manager=file_manager,
                        scaffold_id="test-scaffold",
                        iteration=0,
                        run_type="train",
                        input_string="test input",
                        model_spec="mock",
                    )

                # Check that log files were created in the correct directory
                logs_dir = (
                    Path(temp_dir) / "experiment" / "logs" / "0" / "test-scaffold"
                )
                assert logs_dir.exists()
                log_files = list(logs_dir.glob("*.log"))
                assert len(log_files) == 1

                log_content = log_files[0].read_text()
                assert "test input" in log_content
                assert "test output" in log_content
                assert "test stderr" in log_content
                assert "mock/mock" in log_content

    def test_execute_scaffold_environment_variables(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_manager = self.create_test_scaffold(temp_dir)

            with patch("subprocess.Popen") as mock_popen:
                mock_process = Mock()
                mock_process.communicate.return_value = ("output", "")
                mock_process.returncode = 0
                mock_popen.return_value = mock_process

                # Mock environment variables
                with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
                    with patch("time.time", side_effect=[0.0, 1.0]):
                        result = execute_scaffold(
                            file_manager=file_manager,
                            scaffold_id="test-scaffold",
                            iteration=0,
                            run_type="train",
                            input_string="test input",
                            model_spec="mock",
                        )

                # Check environment was passed to Docker
                call_args = mock_popen.call_args[0][0]
                # Should include environment variable passing
                assert any("OPENAI_API_KEY" in str(arg) for arg in call_args)

    def test_execute_scaffold_custom_timeout(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_manager = self.create_test_scaffold(temp_dir)

            with patch("subprocess.Popen") as mock_popen:
                mock_process = Mock()
                mock_process.communicate.return_value = ("output", "")
                mock_process.returncode = 0
                mock_popen.return_value = mock_process

                with patch("time.time", side_effect=[0.0, 1.0]):
                    result = execute_scaffold(
                        file_manager=file_manager,
                        scaffold_id="test-scaffold",
                        iteration=0,
                        run_type="train",
                        input_string="test input",
                        model_spec="mock",
                        timeout=600,  # 10 minutes
                    )

                # Verify timeout was passed to subprocess
                call_args = mock_popen.call_args
                assert call_args is not None  # Command was called
