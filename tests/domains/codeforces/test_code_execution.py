#!/usr/bin/env python
"""Tests for CodeForces code_execution.py - focuses on code execution logic"""

import unittest
from unittest.mock import patch, MagicMock
from scaffold_learning.domains.codeforces.code_execution import (
    execute_code_against_tests,
    parse_test_results,
)
from scaffold_learning.core.data_structures import ScaffoldExecutionResult


class TestExecuteCodeAgainstTests(unittest.TestCase):
    """Test code execution against test cases."""

    def test_empty_test_cases(self):
        """Test handling of empty test cases."""
        result = execute_code_against_tests("print('test')", [], 2.0, 256.0)

        self.assertIsNotNone(result.error_message)
        self.assertIn("No test cases", result.error_message)

    @patch("subprocess.run")
    def test_successful_execution(self, mock_run):
        """Test successful code execution."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = (
            '{"status": "completed", "results": [{"test_case": 0, "status": "passed"}]}'
        )
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        test_cases = [{"input": "5", "output": "5"}]
        result = execute_code_against_tests("print(input())", test_cases, 2.0, 256.0)

        self.assertIsNone(result.error_message)
        self.assertIn("completed", result.output)
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_docker_timeout_handling(self, mock_run):
        """Test that Docker timeout is properly calculated."""
        mock_process = MagicMock()
        mock_process.returncode = 124  # timeout exit code
        mock_process.stdout = ""
        mock_process.stderr = "timeout"
        mock_run.return_value = mock_process

        test_cases = [{"input": "1", "output": "1"}] * 5  # 5 test cases
        result = execute_code_against_tests("print(input())", test_cases, 2.0, 256.0)

        # Should handle timeout correctly
        self.assertIsNotNone(result.error_message)
        self.assertIn("timed out", result.error_message)
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_memory_limit_doubling(self, mock_run):
        """Test that memory limit is doubled for safety."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = '{"status": "completed", "results": []}'
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        test_cases = [{"input": "1", "output": "1"}]
        execute_code_against_tests("print(input())", test_cases, 2.0, 128.0)

        # Verify Docker command includes doubled memory limit: 128 * 2 = 256m
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][
            0
        ]  # First positional argument (docker command)
        memory_args = [
            call_args[i + 1] for i, arg in enumerate(call_args) if arg == "--memory"
        ]
        self.assertIn("256m", memory_args)

    @patch("subprocess.run")
    def test_execution_exception_handling(self, mock_run):
        """Test handling of execution exceptions."""
        mock_run.side_effect = Exception("Docker failed")

        test_cases = [{"input": "1", "output": "1"}]
        result = execute_code_against_tests("print(input())", test_cases, 2.0, 256.0)

        self.assertIsNotNone(result.error_message)
        self.assertIn("Docker failed", result.error_message)


class TestCodeExecutionIntegration(unittest.TestCase):
    """Integration tests for the full code execution flow."""

    @patch("subprocess.run")
    def test_full_flow_syntax_error(self, mock_run):
        """Test full flow when code has syntax error."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = '{"status": "syntax_error", "error": "invalid syntax"}'
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        code = "print(hello"  # Missing closing parenthesis
        test_cases = [{"input": "1", "output": "1"}]

        result = execute_code_against_tests(code, test_cases)
        parsed = parse_test_results(result)

        self.assertEqual(parsed["status"], "syntax_error")
        self.assertFalse(parsed["passed"])
        self.assertIn("syntax", parsed["error"])

    @patch("subprocess.run")
    def test_full_flow_all_tests_pass(self, mock_run):
        """Test full flow when all tests pass."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = '{"status": "completed", "results": [{"test_case": 0, "status": "passed"}, {"test_case": 1, "status": "passed"}]}'
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        code = "print(input())"
        test_cases = [{"input": "5", "output": "5"}, {"input": "10", "output": "10"}]

        result = execute_code_against_tests(code, test_cases)
        parsed = parse_test_results(result)

        self.assertEqual(parsed["status"], "completed")
        self.assertTrue(parsed["passed"])
        self.assertEqual(parsed["total_tests"], 2)
        self.assertEqual(parsed["passed_tests"], 2)

    @patch("subprocess.run")
    def test_full_flow_mixed_results(self, mock_run):
        """Test full flow with mixed test results."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = '{"status": "completed", "results": [{"test_case": 0, "status": "passed"}, {"test_case": 1, "status": "wrong_answer"}]}'
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        code = "print('5')"  # Always prints 5, regardless of input
        test_cases = [{"input": "5", "output": "5"}, {"input": "10", "output": "10"}]

        result = execute_code_against_tests(code, test_cases)
        parsed = parse_test_results(result)

        self.assertEqual(parsed["status"], "completed")
        self.assertFalse(parsed["passed"])  # Not all tests passed
        self.assertEqual(parsed["total_tests"], 2)
        self.assertEqual(parsed["passed_tests"], 1)


class TestParseTestResults(unittest.TestCase):
    """Test parsing of test execution results."""

    def test_parse_successful_results(self):
        """Test parsing when all tests pass."""
        result = ScaffoldExecutionResult(
            output='{"status": "completed", "results": [{"test_case": 0, "status": "passed"}]}',
            stderr="",
            error_message=None,
            execution_time=0.5,
        )

        parsed = parse_test_results(result)

        self.assertEqual(parsed["status"], "completed")
        self.assertTrue(parsed["passed"])
        self.assertEqual(parsed["total_tests"], 1)
        self.assertEqual(parsed["passed_tests"], 1)

    def test_parse_syntax_error(self):
        """Test parsing when there's a syntax error."""
        result = ScaffoldExecutionResult(
            output='{"status": "syntax_error", "error": "invalid syntax"}',
            stderr="",
            error_message=None,
            execution_time=0.1,
        )

        parsed = parse_test_results(result)

        self.assertEqual(parsed["status"], "syntax_error")
        self.assertFalse(parsed["passed"])
        self.assertIn("syntax", parsed["error"])

    def test_parse_execution_error(self):
        """Test parsing when there's an execution error."""
        result = ScaffoldExecutionResult(
            output='{"status": "execution_error", "error": "runtime error", "traceback": "..."}',
            stderr="",
            error_message=None,
            execution_time=0.1,
        )

        parsed = parse_test_results(result)

        self.assertEqual(parsed["status"], "execution_error")
        self.assertFalse(parsed["passed"])
        self.assertIn("runtime error", parsed["error"])

    def test_parse_mixed_results(self):
        """Test parsing when some tests pass and some fail."""
        result = ScaffoldExecutionResult(
            output='{"status": "completed", "results": [{"test_case": 0, "status": "passed"}, {"test_case": 1, "status": "wrong_answer"}]}',
            stderr="",
            error_message=None,
            execution_time=0.3,
        )

        parsed = parse_test_results(result)

        self.assertEqual(parsed["status"], "completed")
        self.assertFalse(parsed["passed"])  # Not all tests passed
        self.assertEqual(parsed["total_tests"], 2)
        self.assertEqual(parsed["passed_tests"], 1)

    def test_parse_invalid_json(self):
        """Test parsing when output is invalid JSON."""
        result = ScaffoldExecutionResult(
            output="invalid json",
            stderr="",
            error_message=None,
            execution_time=0.1,
        )

        parsed = parse_test_results(result)

        self.assertEqual(parsed["status"], "parse_error")
        self.assertFalse(parsed["passed"])
        self.assertIn("JSON", parsed["error"])

    def test_parse_execution_failed(self):
        """Test parsing when execution failed completely."""
        result = ScaffoldExecutionResult(
            output="",
            stderr="Docker error",
            error_message="Execution failed",
            execution_time=0.0,
        )

        parsed = parse_test_results(result)

        self.assertEqual(parsed["status"], "execution_failed")
        self.assertFalse(parsed["passed"])
        self.assertIn("Execution failed", parsed["error"])


if __name__ == "__main__":
    unittest.main()
