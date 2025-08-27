#!/usr/bin/env python
"""Tests for CodeForces score.py - focuses on code execution and scoring behavior"""

import unittest
from unittest.mock import patch, MagicMock
from scaffold_learning.domains.codeforces.score import score


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
            "scaffold_learning.domains.codeforces.score.execute_and_score_tests"
        ) as mock_execute:
            mock_execute.return_value = 1.0  # All tests passed

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
            "scaffold_learning.domains.codeforces.score.execute_and_score_tests"
        ) as mock_execute:
            mock_execute.return_value = 0.0  # No tests passed

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
            "scaffold_learning.domains.codeforces.score.execute_and_score_tests"
        ) as mock_execute:
            mock_execute.side_effect = SyntaxError("invalid syntax")

            result = score(test_cases, 2.0, 256.0, code)
            self.assertEqual(result, 0.0)

    def test_score_runtime_error(self):
        """Test that score returns 0.0 for runtime errors."""
        test_cases = [{"input": "5\n", "output": "5"}]
        code = "raise Exception('error')"

        with patch(
            "scaffold_learning.domains.codeforces.score.execute_and_score_tests"
        ) as mock_execute:
            mock_execute.side_effect = RuntimeError("error")

            result = score(test_cases, 2.0, 256.0, code)
            self.assertEqual(result, 0.0)

    def test_score_timeout(self):
        """Test that score returns 0.0 for timeouts."""
        test_cases = [{"input": "5\n", "output": "5"}]
        code = "import time; time.sleep(10)"

        with patch(
            "scaffold_learning.domains.codeforces.score.execute_and_score_tests"
        ) as mock_execute:
            mock_execute.side_effect = RuntimeError("timeout")

            result = score(test_cases, 2.0, 256.0, code)
            self.assertEqual(result, 0.0)


if __name__ == "__main__":
    unittest.main()
