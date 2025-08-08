#!/usr/bin/env python
"""Tests for meta-optimize score.py"""

import json
import unittest
from unittest.mock import Mock

from src.scaffold_learning.domains.meta_optimize.score import score


class TestMetaOptimizeScore(unittest.TestCase):
    """Test meta-optimize domain scoring behavior."""

    def setUp(self):
        """Set up mock mesa scorer for tests."""
        self.mock_mesa_scorer = Mock()

    def test_score_single_example(self):
        """Test scoring with a single mesa example."""
        # Setup
        input_string = json.dumps(
            {"scoring_data": [{"input": "What is 2+2?", "correct_answer": "A"}]}
        )
        attempt = json.dumps(["A"])
        self.mock_mesa_scorer.return_value = 1.0

        # Execute
        result = score(attempt, input_string, self.mock_mesa_scorer)

        # Verify
        self.assertEqual(result, 1.0)
        self.mock_mesa_scorer.assert_called_once_with(
            "A", {"input": "What is 2+2?", "correct_answer": "A"}
        )

    def test_score_multiple_examples(self):
        """Test scoring with multiple mesa examples."""
        # Setup
        input_string = json.dumps(
            {
                "scoring_data": [
                    {"input": "What is 2+2?", "correct_answer": "A"},
                    {"input": "What is 3+3?", "correct_answer": "B"},
                    {"input": "What is 4+4?", "correct_answer": "C"},
                ]
            }
        )
        attempt = json.dumps(["A", "B", "C"])
        self.mock_mesa_scorer.side_effect = [1.0, 1.0, 1.0]

        # Execute
        result = score(attempt, input_string, self.mock_mesa_scorer)

        # Verify
        self.assertEqual(result, 1.0)
        self.assertEqual(self.mock_mesa_scorer.call_count, 3)

    def test_score_mixed_results(self):
        """Test scoring with mixed correct/incorrect results."""
        # Setup
        input_string = json.dumps(
            {
                "scoring_data": [
                    {"input": "What is 2+2?", "correct_answer": "A"},
                    {"input": "What is 3+3?", "correct_answer": "B"},
                    {"input": "What is 4+4?", "correct_answer": "C"},
                ]
            }
        )
        attempt = json.dumps(["A", "X", "C"])  # One wrong answer
        self.mock_mesa_scorer.side_effect = [1.0, 0.0, 1.0]

        # Execute
        result = score(attempt, input_string, self.mock_mesa_scorer)

        # Verify
        expected_avg = (1.0 + 0.0 + 1.0) / 3
        self.assertAlmostEqual(result, expected_avg, places=6)

    def test_score_all_wrong(self):
        """Test scoring when all answers are wrong."""
        # Setup
        input_string = json.dumps(
            {
                "scoring_data": [
                    {"input": "What is 2+2?", "correct_answer": "A"},
                    {"input": "What is 3+3?", "correct_answer": "B"},
                ]
            }
        )
        attempt = json.dumps(["X", "Y"])
        self.mock_mesa_scorer.side_effect = [0.0, 0.0]

        # Execute
        result = score(attempt, input_string, self.mock_mesa_scorer)

        # Verify
        self.assertEqual(result, 0.0)

    def test_score_mismatch_length(self):
        """Test behavior when attempts and scoring_data have different lengths."""
        # Setup
        input_string = json.dumps(
            {
                "scoring_data": [
                    {"input": "What is 2+2?", "correct_answer": "A"},
                    {"input": "What is 3+3?", "correct_answer": "B"},
                ]
            }
        )
        attempt = json.dumps(["A"])  # Only one attempt for two questions

        result = score(attempt, input_string, self.mock_mesa_scorer)
        self.assertEqual(result, -float("inf"))

    def test_score_invalid_json_input(self):
        """Test error when input_string is not valid JSON."""
        attempt = json.dumps(["A"])
        input_string = "not valid json"

        with self.assertRaises(json.JSONDecodeError):
            score(attempt, input_string, self.mock_mesa_scorer)

    def test_score_invalid_json_attempt(self):
        """Test behavior when attempt is not valid JSON."""
        input_string = json.dumps(
            {"scoring_data": [{"input": "What is 2+2?", "correct_answer": "A"}]}
        )
        attempt = "not valid json"

        result = score(attempt, input_string, self.mock_mesa_scorer)
        self.assertEqual(result, -float("inf"))

    def test_score_missing_scoring_data_key(self):
        """Test error when input doesn't contain 'scoring_data' key."""
        input_string = json.dumps({"wrong_key": []})
        attempt = json.dumps(["A"])

        with self.assertRaises(KeyError):
            score(attempt, input_string, self.mock_mesa_scorer)

    def test_score_fractional_scores(self):
        """Test with fractional scores from mesa scorer."""
        # Setup
        input_string = json.dumps(
            {
                "scoring_data": [
                    {"input": "Prompt 1", "solution": "Answer 1"},
                    {"input": "Prompt 2", "solution": "Answer 2"},
                    {"input": "Prompt 3", "solution": "Answer 3"},
                ]
            }
        )
        attempt = json.dumps(["Response 1", "Response 2", "Response 3"])
        self.mock_mesa_scorer.side_effect = [0.8, 0.6, 0.9]

        # Execute
        result = score(attempt, input_string, self.mock_mesa_scorer)

        # Verify
        expected_avg = (0.8 + 0.6 + 0.9) / 3
        self.assertAlmostEqual(result, expected_avg, places=6)


if __name__ == "__main__":
    unittest.main()
