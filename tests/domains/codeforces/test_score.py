#!/usr/bin/env python
"""Tests for CodeForces score.py - focuses on code execution and scoring behavior"""

import unittest
from unittest.mock import patch, MagicMock
from scaffold_learning.domains.codeforces.score import score
from scaffold_learning.domains.codeforces.code_execution import parse_test_results
from scaffold_learning.core.data_structures import ScaffoldExecutionResult


class TestCodeForcesScore(unittest.TestCase):
    """Test CodeForces domain-specific scoring behavior."""

    def test_score_all_tests_pass(self):
        """Test that score returns 1.0 when all tests pass."""
        test_cases = [
            {"input": "5\n", "output": "5"},
            {"input": "10\n", "output": "10"},
        ]

        # Simple code that just echoes input
        code = "print(input().strip())"

        with patch(
            "scaffold_learning.domains.codeforces.score.execute_code_against_tests"
        ) as mock_execute:
            mock_execute.return_value = ScaffoldExecutionResult(
                output='{"status": "completed", "results": [{"test_case": 0, "status": "passed"}, {"test_case": 1, "status": "passed"}]}',
                stderr="",
                error_message=None,
                execution_time=0.5,
            )

            result = score(test_cases, 2.0, 256.0, code)
            self.assertEqual(result, 1.0)

    def test_score_some_tests_fail(self):
        """Test that score returns 0.0 when any test fails."""
        test_cases = [
            {"input": "5\n", "output": "5"},
            {"input": "10\n", "output": "10"},
        ]

        code = "print('wrong')"

        with patch(
            "scaffold_learning.domains.codeforces.score.execute_code_against_tests"
        ) as mock_execute:
            mock_execute.return_value = ScaffoldExecutionResult(
                output='{"status": "completed", "results": [{"test_case": 0, "status": "wrong_answer"}, {"test_case": 1, "status": "wrong_answer"}]}',
                stderr="",
                error_message=None,
                execution_time=0.5,
            )

            result = score(test_cases, 2.0, 256.0, code)
            self.assertEqual(result, 0.0)

    def test_score_empty_code(self):
        """Test that score returns 0.0 for empty code."""
        test_cases = [{"input": "5\n", "output": "5"}]
        result = score(test_cases, 2.0, 256.0, "")
        self.assertEqual(result, 0.0)

        result = score(test_cases, 2.0, 256.0, "   ")
        self.assertEqual(result, 0.0)

    def test_score_syntax_error(self):
        """Test that score returns 0.0 for syntax errors."""
        test_cases = [{"input": "5\n", "output": "5"}]
        code = "print(invalid syntax"

        with patch(
            "scaffold_learning.domains.codeforces.score.execute_code_against_tests"
        ) as mock_execute:
            mock_execute.return_value = ScaffoldExecutionResult(
                output='{"status": "syntax_error", "error": "invalid syntax"}',
                stderr="",
                error_message=None,
                execution_time=0.0,
            )

            result = score(test_cases, 2.0, 256.0, code)
            self.assertEqual(result, 0.0)

    def test_score_runtime_error(self):
        """Test that score returns 0.0 for runtime errors."""
        test_cases = [{"input": "5\n", "output": "5"}]
        code = "raise Exception('error')"

        with patch(
            "scaffold_learning.domains.codeforces.score.execute_code_against_tests"
        ) as mock_execute:
            mock_execute.return_value = ScaffoldExecutionResult(
                output='{"status": "completed", "results": [{"test_case": 0, "status": "runtime_error", "error": "error"}]}',
                stderr="",
                error_message=None,
                execution_time=0.0,
            )

            result = score(test_cases, 2.0, 256.0, code)
            self.assertEqual(result, 0.0)

    def test_score_timeout(self):
        """Test that score returns 0.0 for timeouts."""
        test_cases = [{"input": "5\n", "output": "5"}]
        code = "import time; time.sleep(10)"

        with patch(
            "scaffold_learning.domains.codeforces.score.execute_code_against_tests"
        ) as mock_execute:
            mock_execute.return_value = ScaffoldExecutionResult(
                output='{"status": "completed", "results": [{"test_case": 0, "status": "timeout"}]}',
                stderr="",
                error_message=None,
                execution_time=5.0,
            )

            result = score(test_cases, 2.0, 256.0, code)
            self.assertEqual(result, 0.0)


class TestParseTestResults(unittest.TestCase):
    """Test parsing of test execution results."""

    def test_parse_successful_execution(self):
        """Test parsing when all tests pass."""
        execution_result = ScaffoldExecutionResult(
            output='{"status": "completed", "results": [{"test_case": 0, "status": "passed"}, {"test_case": 1, "status": "passed"}]}',
            stderr="",
            error_message=None,
            execution_time=0.5,
        )

        result = parse_test_results(execution_result)

        self.assertEqual(result["status"], "completed")
        self.assertTrue(result["passed"])
        self.assertEqual(result["total_tests"], 2)
        self.assertEqual(result["passed_tests"], 2)

    def test_parse_partial_success(self):
        """Test parsing when some tests fail."""
        execution_result = ScaffoldExecutionResult(
            output='{"status": "completed", "results": [{"test_case": 0, "status": "passed"}, {"test_case": 1, "status": "wrong_answer"}]}',
            stderr="",
            error_message=None,
            execution_time=0.5,
        )

        result = parse_test_results(execution_result)

        self.assertEqual(result["status"], "completed")
        self.assertFalse(result["passed"])  # Not all tests passed
        self.assertEqual(result["total_tests"], 2)
        self.assertEqual(result["passed_tests"], 1)

    def test_parse_syntax_error(self):
        """Test parsing syntax error results."""
        execution_result = ScaffoldExecutionResult(
            output='{"status": "syntax_error", "error": "invalid syntax"}',
            stderr="",
            error_message=None,
            execution_time=0.0,
        )

        result = parse_test_results(execution_result)

        self.assertEqual(result["status"], "syntax_error")
        self.assertFalse(result["passed"])
        self.assertEqual(result["total_tests"], 0)
        self.assertEqual(result["passed_tests"], 0)
        self.assertIn("error", result)

    def test_parse_execution_error(self):
        """Test parsing when execution itself fails."""
        execution_result = ScaffoldExecutionResult(
            output="",
            stderr="Docker error",
            error_message="Docker container failed",
            execution_time=0.0,
        )

        result = parse_test_results(execution_result)

        self.assertEqual(result["status"], "execution_failed")
        self.assertFalse(result["passed"])
        self.assertEqual(result["total_tests"], 0)
        self.assertEqual(result["passed_tests"], 0)

    def test_parse_invalid_json(self):
        """Test parsing when output is not valid JSON."""
        execution_result = ScaffoldExecutionResult(
            output="Not valid JSON",
            stderr="",
            error_message=None,
            execution_time=0.0,
        )

        result = parse_test_results(execution_result)

        self.assertEqual(result["status"], "parse_error")
        self.assertFalse(result["passed"])
        self.assertEqual(result["total_tests"], 0)
        self.assertEqual(result["passed_tests"], 0)
        self.assertIn("raw_output", result)

    def test_parse_empty_output(self):
        """Test parsing when output is empty."""
        execution_result = ScaffoldExecutionResult(
            output="",
            stderr="",
            error_message=None,
            execution_time=0.0,
        )

        result = parse_test_results(execution_result)

        self.assertEqual(result["status"], "parse_error")
        self.assertFalse(result["passed"])


if __name__ == "__main__":
    unittest.main()
