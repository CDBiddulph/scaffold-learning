#!/usr/bin/env python
"""Tests for AIME score.py - focuses on AIME-specific behavior"""

import unittest
from src.scaffold_learning.domains.aime.score import score, extract_numerical_answer


class TestAIMEScore(unittest.TestCase):
    """Test AIME domain-specific scoring behavior."""

    def test_extract_numerical_answer_basic(self):
        """Test basic answer extraction."""
        test_cases = [
            ("Answer: 123", 123),
            ("answer: 456", 456),
            ("The answer is 789", 789),
            ("Final answer: 42", 42),
            ("final answer is 7", 7),
            ("Answer: 000", 0),
            ("Answer: 007", 7),
            ("The answer is 999", 999),
        ]

        for text, expected in test_cases:
            with self.subTest(text=text):
                result = extract_numerical_answer(text)
                self.assertEqual(result, expected)

    def test_extract_numerical_answer_boxed(self):
        """Test extraction from boxed format."""
        test_cases = [
            (r"Therefore, \boxed{123}", 123),
            (r"The answer is \boxed{456}", 456),
            (r"We get \boxed{789}.", 789),
            (r"\boxed{42}", 42),
        ]

        for text, expected in test_cases:
            with self.subTest(text=text):
                result = extract_numerical_answer(text)
                self.assertEqual(result, expected)

    def test_extract_numerical_answer_multiple(self):
        """Test extraction takes the last valid answer."""
        text = """
        First I thought the answer was 100.
        But actually, the answer is 200.
        Wait, I made an error. Answer: 300
        """
        self.assertEqual(extract_numerical_answer(text), 300)

    def test_extract_numerical_answer_invalid(self):
        """Test invalid answers return None."""
        test_cases = [
            "No answer here",
            "Answer: 1000",  # Out of range
            "Answer: -5",  # Negative
            "Answer: 12345",  # Too large
            "The answer is two hundred",  # Words not numbers
            "",  # Empty
        ]

        for text in test_cases:
            with self.subTest(text=text):
                result = extract_numerical_answer(text)
                self.assertIsNone(result)

    def test_extract_numerical_answer_standalone(self):
        """Test extraction of standalone numbers at end."""
        test_cases = [
            ("After working through the problem:\n123", 123),
            ("The calculation gives us\n456", 456),
            ("Therefore,\n789", 789),
        ]

        for text, expected in test_cases:
            with self.subTest(text=text):
                result = extract_numerical_answer(text)
                self.assertEqual(result, expected)

    def test_score_correct_answers(self):
        """Test scoring correct answers."""
        test_cases = [
            (123, "Answer: 123", 1.0),
            (456, "The answer is 456", 1.0),
            (789, r"\boxed{789}", 1.0),
            (0, "Answer: 0", 1.0),
            (999, "Answer: 999", 1.0),
            (7, "Answer: 007", 1.0),  # Leading zeros handled
        ]

        for expected, response, expected_score in test_cases:
            with self.subTest(expected=expected, response=response):
                result = score(expected, response)
                self.assertEqual(result, expected_score)

    def test_score_incorrect_answers(self):
        """Test scoring incorrect answers."""
        test_cases = [
            (123, "Answer: 124", 0.0),
            (456, "Answer: 455", 0.0),
            (789, "Answer: 790", 0.0),
            (42, "No answer given", 0.0),
            (100, "", 0.0),
        ]

        for expected, response, expected_score in test_cases:
            with self.subTest(expected=expected, response=response):
                result = score(expected, response)
                self.assertEqual(result, expected_score)

    def test_score_validation(self):
        """Test score validation."""
        # Invalid expected answer type
        with self.assertRaises(ValueError):
            score("123", "Answer: 123")

        with self.assertRaises(ValueError):
            score(3.14, "Answer: 3")

        # Out of range
        with self.assertRaises(ValueError):
            score(1000, "Answer: 1000")

        with self.assertRaises(ValueError):
            score(-1, "Answer: -1")

    def test_aime_integration(self):
        """Test end-to-end AIME scoring with realistic examples."""
        test_cases = [
            (
                902,
                "After working through the casework, I get 451 × 2 = 902. Answer: 902",
                1.0,
            ),
            (789, r"Thus we have \boxed{789}", 1.0),
            (100, "I think it might be 100 or 101", 0.0),  # Ambiguous
            (200, "The answer could be around 200-300", 0.0),  # Range not specific
        ]

        for expected, response, expected_score in test_cases:
            with self.subTest(expected=expected, response=response):
                result = score(expected, response)
                self.assertEqual(result, expected_score)


if __name__ == "__main__":
    unittest.main()
