#!/usr/bin/env python
"""Tests for CodeForces code_execution.py - focuses on code execution logic"""

import unittest
from unittest.mock import patch, MagicMock
from scaffold_learning.domains.codeforces.code_execution import execute_and_score_tests


class TestExecuteAndScoreTests(unittest.TestCase):
    """Test code execution and scoring."""

    def test_empty_test_cases(self):
        """Test handling of empty test cases."""
        with self.assertRaises(ValueError) as cm:
            execute_and_score_tests("print('test')", [], 2.0, 256.0)

        self.assertIn("No test cases", str(cm.exception))

    @patch("subprocess.run")
    def test_successful_execution(self, mock_run):
        """Test successful code execution."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = '{"results": [{"test_case": 0, "passed": true, "input": "5", "expected": "5", "actual": "5"}]}'
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        test_cases = [{"input": "5", "output": "5"}]
        result = execute_and_score_tests("print(input())", test_cases, 2.0, 256.0)

        self.assertEqual(result, 1.0)  # All tests passed
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

        with self.assertRaises(RuntimeError) as cm:
            execute_and_score_tests("print(input())", test_cases, 2.0, 256.0)

        self.assertIn("timed out", str(cm.exception))
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_memory_limit_doubling(self, mock_run):
        """Test that memory limit is doubled for safety."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = '{"results": []}'
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        test_cases = [{"input": "1", "output": "1"}]
        result = execute_and_score_tests("print(input())", test_cases, 2.0, 128.0)

        self.assertEqual(result, 0.0)  # No tests in results, so 0/0 = 0.0

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

        with self.assertRaises(Exception) as cm:
            execute_and_score_tests("print(input())", test_cases, 2.0, 256.0)

        self.assertIn("Docker failed", str(cm.exception))


class TestCodeExecutionIntegration(unittest.TestCase):
    """Integration tests for the full code execution flow."""

    @patch("subprocess.run")
    def test_full_flow_syntax_error(self, mock_run):
        """Test full flow when code has syntax error."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = '{"error": "invalid syntax"}'
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        code = "print(hello"  # Missing closing parenthesis
        test_cases = [{"input": "1", "output": "1"}]

        with self.assertRaises(SyntaxError) as cm:
            execute_and_score_tests(code, test_cases, 2.0, 256.0)

        self.assertIn("syntax", str(cm.exception))

    @patch("subprocess.run")
    def test_full_flow_all_tests_pass(self, mock_run):
        """Test full flow when all tests pass."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = '{"results": [{"test_case": 0, "passed": true, "input": "5", "expected": "5", "actual": "5"}, {"test_case": 1, "passed": true, "input": "10", "expected": "10", "actual": "10"}]}'
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        code = "print(input())"
        test_cases = [{"input": "5", "output": "5"}, {"input": "10", "output": "10"}]

        result = execute_and_score_tests(code, test_cases, 2.0, 256.0)

        self.assertEqual(result, 1.0)  # 2/2 = 1.0

    @patch("subprocess.run")
    def test_full_flow_mixed_results(self, mock_run):
        """Test full flow with mixed test results."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = '{"results": [{"test_case": 0, "passed": true, "input": "5", "expected": "5", "actual": "5"}, {"test_case": 1, "passed": false, "error": "Wrong answer", "input": "10", "expected": "10", "actual": "5"}]}'
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        code = "print('5')"  # Always prints 5, regardless of input
        test_cases = [{"input": "5", "output": "5"}, {"input": "10", "output": "10"}]

        result = execute_and_score_tests(code, test_cases, 2.0, 256.0)

        self.assertEqual(result, 0.5)  # 1/2 = 0.5


if __name__ == "__main__":
    unittest.main()
