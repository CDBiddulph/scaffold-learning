#!/usr/bin/env python
"""Tests for MCQ score.py - focuses on MCQ-specific behavior"""

import unittest
from src.scaffold_learning.domains.mcq.score import score


class TestMCQScore(unittest.TestCase):
    """Test MCQ domain-specific scoring behavior."""

    def test_mcq_valid_letters(self):
        """Test that MCQ scoring works with A-E letters."""
        # Test all valid MCQ letters
        for letter in "ABCDE":
            assert score(letter, f"Answer: {letter}") == 1.0

        # Test incorrect answers
        assert score("A", "Answer: B") == 0.0
        assert score("C", "Answer: D") == 0.0

    def test_mcq_invalid_letters(self):
        """Test that MCQ rejects invalid letters like F, G, etc."""
        with self.assertRaises(ValueError):
            score("F", "Answer: F")

        with self.assertRaises(ValueError):
            score("Z", "Answer: Z")

    def test_mcq_integration(self):
        """Test end-to-end MCQ scoring with realistic examples."""
        test_cases = [
            ("A", "After careful analysis, my answer: A", 1.0),
            ("B", "Looking at all options, I choose B.", 1.0),
            ("C", "The answer is C based on the evidence.", 1.0),
            ("D", "I choose D as my final answer.", 1.0),
            ("E", "Answer: E", 1.0),
            ("A", "I think it might be A or B", 0.0),  # No single answer
            ("B", "I think it might be A or B", 0.0),  # Similar to above
            ("C", "I don't know the answer", 0.0),  # No answer found
        ]

        for expected, response, expected_score in test_cases:
            with self.subTest(expected=expected, response=response):
                result = score(expected, response)
                self.assertEqual(result, expected_score)

    def test_mcq_case_insensitive(self):
        """Test MCQ case insensitivity."""
        assert score("a", "Answer: A") == 1.0
        assert score("B", "answer: b") == 1.0
        assert score("C", "I choose c") == 1.0

    def test_mcq_validation_errors(self):
        """Test MCQ-specific validation."""
        invalid_cases = [
            "",  # Empty
            "AB",  # Multiple letters
            "1",  # Number
            None,  # None
        ]

        for invalid in invalid_cases:
            with self.subTest(expected=invalid):
                with self.assertRaises(ValueError):
                    score(invalid, "Answer: A")


if __name__ == "__main__":
    unittest.main()
