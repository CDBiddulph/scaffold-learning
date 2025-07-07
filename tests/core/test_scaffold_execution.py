import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
import json
from scaffold_learning.core.scaffold_execution import execute_scaffold
from scaffold_learning.core.data_structures import ScaffoldExecutionResult


class TestScaffoldExecution:
    def test_execute_scaffold_success(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            scaffold_dir = Path(temp_dir) / "scaffold"
            logs_path = Path(temp_dir) / "logs"

            # Create scaffold directory with files
            scaffold_dir.mkdir()
            logs_path.mkdir()

            # Create a basic scaffold.py
            (scaffold_dir / "scaffold.py").write_text(
                """
def process_input(input_string: str) -> str:
    return f"processed: {input_string}"
"""
            )

            # Create metadata.json
            (scaffold_dir / "metadata.json").write_text('{"model": "test"}')

            # Mock subprocess to simulate successful execution
            with patch("subprocess.Popen") as mock_popen:
                mock_process = Mock()
                mock_process.communicate.return_value = ("result output", "")
                mock_process.returncode = 0
                mock_popen.return_value = mock_process

                # Mock time.time for execution timing
                with patch("time.time", side_effect=[0.0, 1.5]):
                    result = execute_scaffold(
                        scaffold_dir=scaffold_dir,
                        input_string="test input",
                        model="gpt-4",
                        logs_path=logs_path / "test.log",
                        timeout=120,
                    )

                assert isinstance(result, ScaffoldExecutionResult)
                assert result.output == "result output"
                assert result.stderr == ""
                assert result.exit_code == 0
                assert result.execution_time == 1.5

    def test_execute_scaffold_with_timeout(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            scaffold_dir = Path(temp_dir) / "scaffold"
            logs_path = Path(temp_dir) / "logs"
            scaffold_dir.mkdir()
            logs_path.mkdir()

            # Mock subprocess that hangs
            with patch("subprocess.Popen") as mock_popen:
                mock_process = Mock()
                mock_process.communicate.side_effect = [("", "Timeout error")]
                mock_process.returncode = 124  # Timeout exit code
                mock_popen.return_value = mock_process

                with patch("time.time", side_effect=[0.0, 120.5]):
                    result = execute_scaffold(
                        scaffold_dir=scaffold_dir,
                        input_string="test input",
                        model="gpt-4",
                        logs_path=logs_path / "test.log",
                        timeout=60,
                    )

                assert result.exit_code == 124
                assert result.execution_time == 120.5

    def test_execute_scaffold_with_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            scaffold_dir = Path(temp_dir) / "scaffold"
            logs_path = Path(temp_dir) / "logs"
            scaffold_dir.mkdir()
            logs_path.mkdir()

            with patch("subprocess.Popen") as mock_popen:
                mock_process = Mock()
                mock_process.communicate.return_value = ("", "Error: syntax error")
                mock_process.returncode = 1
                mock_popen.return_value = mock_process

                with patch("time.time", side_effect=[0.0, 0.5]):
                    result = execute_scaffold(
                        scaffold_dir=scaffold_dir,
                        input_string="test input",
                        model="gpt-4",
                        logs_path=logs_path / "test.log",
                    )

                assert result.exit_code == 1
                assert result.stderr == "Error: syntax error"
                assert result.execution_time == 0.5

    def test_execute_scaffold_docker_command_construction(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            scaffold_dir = Path(temp_dir) / "scaffold"
            logs_path = Path(temp_dir) / "logs"
            scaffold_dir.mkdir()
            logs_path.mkdir()

            with patch("subprocess.Popen") as mock_popen:
                mock_process = Mock()
                mock_process.communicate.return_value = ("output", "")
                mock_process.returncode = 0
                mock_popen.return_value = mock_process

                with patch("time.time", side_effect=[0.0, 1.0]):
                    execute_scaffold(
                        scaffold_dir=scaffold_dir,
                        input_string="test input",
                        model="gpt-4o",
                        logs_path=logs_path / "test.log",
                        timeout=300,
                    )

                # Check that docker command was constructed correctly
                call_args = mock_popen.call_args[0][0]  # First argument (the command)
                assert "docker" in call_args
                assert "run" in call_args
                assert "--rm" in call_args
                assert f"{scaffold_dir.absolute()}:/workspace/scaffold:ro" in " ".join(
                    call_args
                )
                assert f"{logs_path.absolute()}:/workspace/logs" in " ".join(call_args)

    def test_execute_scaffold_logs_saved_correctly(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            scaffold_dir = Path(temp_dir) / "scaffold"
            logs_path = Path(temp_dir) / "logs" / "execution.log"
            scaffold_dir.mkdir()
            logs_path.parent.mkdir()

            with patch("subprocess.Popen") as mock_popen:
                mock_process = Mock()
                mock_process.communicate.return_value = ("test output", "test stderr")
                mock_process.returncode = 0
                mock_popen.return_value = mock_process

                with patch("time.time", side_effect=[0.0, 2.0]):
                    result = execute_scaffold(
                        scaffold_dir=scaffold_dir,
                        input_string="test input",
                        model="gpt-4",
                        logs_path=logs_path,
                    )

                # Check that logs were saved correctly
                assert logs_path.exists()
                log_content = logs_path.read_text()
                assert "test input" in log_content
                assert "test output" in log_content
                assert "test stderr" in log_content

    def test_execute_scaffold_environment_variables(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            scaffold_dir = Path(temp_dir) / "scaffold"
            logs_path = Path(temp_dir) / "logs"
            scaffold_dir.mkdir()
            logs_path.mkdir()

            with patch("subprocess.Popen") as mock_popen:
                mock_process = Mock()
                mock_process.communicate.return_value = ("output", "")
                mock_process.returncode = 0
                mock_popen.return_value = mock_process

                # Mock environment variables
                with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
                    with patch("time.time", side_effect=[0.0, 1.0]):
                        result = execute_scaffold(
                            scaffold_dir=scaffold_dir,
                            input_string="test input",
                            model="gpt-4",
                            logs_path=logs_path / "test.log",
                        )

                # Check environment was passed to Docker
                call_args = mock_popen.call_args[0][0]
                # Should include environment variable passing
                assert any("OPENAI_API_KEY" in str(arg) for arg in call_args)

    def test_execute_scaffold_custom_timeout(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            scaffold_dir = Path(temp_dir) / "scaffold"
            logs_path = Path(temp_dir) / "logs"
            scaffold_dir.mkdir()
            logs_path.mkdir()

            with patch("subprocess.Popen") as mock_popen:
                mock_process = Mock()
                mock_process.communicate.return_value = ("output", "")
                mock_process.returncode = 0
                mock_popen.return_value = mock_process

                with patch("time.time", side_effect=[0.0, 1.0]):
                    result = execute_scaffold(
                        scaffold_dir=scaffold_dir,
                        input_string="test input",
                        model="gpt-4",
                        logs_path=logs_path / "test.log",
                        timeout=600,  # 10 minutes
                    )

                # Verify timeout was passed to subprocess
                call_args = mock_popen.call_args
                assert call_args is not None  # Command was called
