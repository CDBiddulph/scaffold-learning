#!/usr/bin/env python3
"""Tests for scaffold_learning.cli.run_scaffold"""

import shutil
import unittest
import tempfile
import json
import subprocess
import time
from pathlib import Path
from unittest.mock import patch, Mock
from scaffold_learning.cli.run_scaffold import run_scaffold


class TestRunScaffoldLogging(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(self._cleanup)

        # Create test scaffold directory structure
        self.scaffold_base_dir = self.temp_dir
        self.scaffold_name = "test_scaffold"
        self.scaffold_dir = Path(self.scaffold_base_dir) / self.scaffold_name
        self.scaffold_dir.mkdir()

        # Create a simple scaffold.py that can be executed
        scaffold_content = '''
def process_input(input_string):
    """Simple test scaffold that processes input"""
    print(f"Processing: {input_string}")
    return f"Result for: {input_string}"
'''
        with open(self.scaffold_dir / "scaffold.py", "w") as f:
            f.write(scaffold_content)

        # Test data
        self.input_string = "test input data"

        # Ensure logs directory is clean before each test
        logs_dir = Path("logs") / self.scaffold_name
        if logs_dir.exists():
            shutil.rmtree(logs_dir)

    def _cleanup(self):
        """Clean up temporary files"""
        shutil.rmtree(self.temp_dir)

        # Clean up logs directory
        logs_dir = Path("logs") / self.scaffold_name
        if logs_dir.exists():
            shutil.rmtree(logs_dir)

    def _find_log_files(self):
        """Find created log files in the logs directory"""
        logs_dir = Path("logs") / self.scaffold_name
        if not logs_dir.exists():
            return [], []

        log_files = list(logs_dir.glob("*.log"))
        json_files = list(logs_dir.glob("*.json"))
        return log_files, json_files

    def _create_mock_process(
        self, poll_sequence, returncode, stdout_lines, stderr_lines
    ):
        """Create a mock process with given behavior"""
        mock_process = Mock()
        mock_process.poll.side_effect = poll_sequence
        mock_process.returncode = returncode
        mock_process.stdout.readline.side_effect = stdout_lines + [""]
        mock_process.stderr.readline.side_effect = stderr_lines + [""]
        return mock_process

    def _run_scaffold_with_llm_mock(
        self,
        mock_process,
        timeout=None,
        model_override=None,
        expect_exception=None,
        time_mock_values=None,
    ):
        """Run scaffold with mocked LLM execution"""
        with patch("scaffold_learning.cli.run_scaffold._ensure_docker_image"):
            with patch(
                "scaffold_learning.cli.run_scaffold.subprocess.Popen",
                return_value=mock_process,
            ):
                if time_mock_values:
                    with patch(
                        "scaffold_learning.cli.run_scaffold.time.time",
                        side_effect=time_mock_values,
                    ):
                        self._execute_run_scaffold(
                            timeout, model_override, expect_exception
                        )
                else:
                    self._execute_run_scaffold(
                        timeout, model_override, expect_exception
                    )

    def _execute_run_scaffold(self, timeout, model, expect_exception):
        """Execute run_scaffold with optional exception handling"""
        if expect_exception:
            with self.assertRaises(expect_exception):
                run_scaffold(
                    self.scaffold_name,
                    self.scaffold_base_dir,
                    self.input_string,
                    "INFO",
                    model,
                    timeout,
                )
        else:
            run_scaffold(
                self.scaffold_name,
                self.scaffold_base_dir,
                self.input_string,
                "INFO",
                model,
                timeout,
            )

    def _run_scaffold_with_human_mock(self):
        """Run scaffold with mocked human execution"""
        with patch("scaffold_learning.cli.run_scaffold._ensure_docker_image"):
            with patch("scaffold_learning.cli.run_scaffold.subprocess.run") as mock_run:
                mock_run.return_value = subprocess.CompletedProcess([], 0)
                run_scaffold(
                    self.scaffold_name,
                    self.scaffold_base_dir,
                    self.input_string,
                    "INFO",
                    "human",
                    None,
                )

    def _verify_log_file_exists_and_get_content(self):
        """Verify exactly one log file exists and return its content"""
        log_files, _ = self._find_log_files()
        self.assertEqual(len(log_files), 1, "Expected exactly one .log file")

        with open(log_files[0], "r") as f:
            return f.read()

    def _verify_log_contains_basic_structure(self, log_content, executor="mock/mock"):
        """Verify log contains basic scaffold execution structure"""
        basic_sections = [
            "=== Scaffold Execution Log ===",
            f"Scaffold: {self.scaffold_name}",
            f"Executor: {executor}",
            "Timestamp:",
            "================================",
            "=== INPUT ===",
            self.input_string,
        ]

        for section in basic_sections:
            self.assertIn(section, log_content, f"Expected '{section}' in log file")

    def _verify_log_contains_content(self, log_content, expected_content):
        """Verify log contains all expected content"""
        for content in expected_content:
            self.assertIn(content, log_content, f"Expected '{content}' in log file")

    def test_run_scaffold_success_creates_log_file(self):
        """Test that successful scaffold execution creates .log file with complete content"""
        mock_process = self._create_mock_process(
            poll_sequence=[None, None, 0],
            returncode=0,
            stdout_lines=[
                "Starting execution\n",
                "Processing: test input data\n",
                "Result for: test input data\n",
            ],
            stderr_lines=["Info: scaffold loaded\n"],
        )

        self._run_scaffold_with_llm_mock(mock_process, model_override="mock")

        log_content = self._verify_log_file_exists_and_get_content()
        # Assert on the exact contents once to demonstrate what it looks like
        self.assertRegex(
            log_content,
            r"""=== Scaffold Execution Log ===
Scaffold: test_scaffold
Executor: mock/mock
Timestamp: \d{8}_\d{6}
================================

=== INPUT ===
test input data

=== STDERR ===
Info: scaffold loaded

=== STDOUT ===
Starting execution
Processing: test input data
Result for: test input data

""",
        )

    def test_run_scaffold_timeout_creates_log_file_with_error(self):
        """Test that timeout creates .log file with timeout error and partial output"""
        mock_process = self._create_mock_process(
            poll_sequence=[None, None, None],  # Always running (timeout)
            returncode=None,
            stdout_lines=["Starting execution\n", "Processing step 1\n"],
            stderr_lines=["Debug: initializing\n", "Debug: processing started\n"],
        )

        self._run_scaffold_with_llm_mock(
            mock_process,
            timeout=1,
            model_override="mock",
            expect_exception=subprocess.TimeoutExpired,
            time_mock_values=[0, 0.5, 1.1],
        )

        log_content = self._verify_log_file_exists_and_get_content()

        # Verify essential timeout content
        timeout_content = [
            "Error: Execution timed out after 1 seconds",
        ]
        self._verify_log_contains_basic_structure(log_content)
        self._verify_log_contains_content(log_content, timeout_content)

        # Verify at least one output section exists (timing dependent)
        has_output_section = ("=== STDOUT ===" in log_content) or (
            "=== STDERR ===" in log_content
        )
        self.assertTrue(
            has_output_section, "Expected at least one output section in timeout log"
        )

    def test_run_scaffold_failure_creates_log_file(self):
        """Test that process failure creates .log file with error output"""
        mock_process = self._create_mock_process(
            poll_sequence=[None, 1],
            returncode=1,
            stdout_lines=["Starting process\n", "About to fail\n"],
            stderr_lines=["Error: something went wrong\n"],
        )

        self._run_scaffold_with_llm_mock(
            mock_process, model_override="mock", expect_exception=subprocess.CalledProcessError
        )

        log_content = self._verify_log_file_exists_and_get_content()
        self._verify_log_contains_basic_structure(log_content)

        # Verify specific failure content
        failure_content = [
            "=== STDERR ===",
            "Error: something went wrong",
            "=== STDOUT ===",
            "Starting process",
            "About to fail",
        ]
        self._verify_log_contains_content(log_content, failure_content)

    def test_run_scaffold_human_model_creates_log_file(self):
        """Test that human model execution creates appropriate log file"""
        self._run_scaffold_with_human_mock()

        log_content = self._verify_log_file_exists_and_get_content()
        self._verify_log_contains_basic_structure(log_content, executor="human/human")

        # Verify human-specific content
        human_content = [
            "=== STDOUT ===",
            "Note: Human model execution - no output captured",
            "User interaction occurred directly in terminal.",
        ]
        self._verify_log_contains_content(log_content, human_content)

    def test_run_scaffold_with_model_override_uses_correct_executor(self):
        """Test that model override is reflected in log files"""
        override_model = "gpt-4o"

        mock_process = self._create_mock_process(
            poll_sequence=[None, 0],
            returncode=0,
            stdout_lines=["Output\n"],
            stderr_lines=[],
        )

        self._run_scaffold_with_llm_mock(mock_process, model_override=override_model)

        log_content = self._verify_log_file_exists_and_get_content()

        # Verify model override is reflected in executor
        self.assertIn("Executor: openai/gpt-4o", log_content)
        self.assertNotIn("Executor: mock/mock", log_content)


if __name__ == "__main__":
    unittest.main()
