#!/usr/bin/env python
"""Tests for MCQ score.py"""

import unittest
from src.scaffold_learning.domains.mcq.score import score
from src.scaffold_learning.domains.answer_extraction import extract_answer_letter


class TestMCQScore(unittest.TestCase):

    def test_extract_answer_formats(self):
        """Test answer extraction with various common formats"""
        test_cases = [
            ("The answer is A", "A"),
            ("I choose B.", "B"),
            ("Answer: C", "C"),
            ("(D) is correct", "D"),
            ("My final answer is E)", "E"),
            ("The correct option is A)", "A"),
            ("B is the right choice", "B"),
            ("C.", "C"),
            ("(A)", "A"),
            ("Answer A", "A"),
            ("D", "D"),
            ("I considered A and B, but answer is C", "C"),
            ("Consider A and B. Answer: C", "C"),
            ("The choices are A, B, C, D. I pick (D)", "D"),
            ("After analyzing A through E, my answer is C.", "C"),
            ("the answer is a", "A"),
            ("I choose b.", "B"),
            ("answer: c", "C"),
            ("(d) is correct", "D"),
            ("I considered A and B, but answer is C", "C"),
            ("Answer: A. Also considered B", "A"),
            (
                "(A) and (B) are wrong, (C) is right",
                "C",
            ),  # Takes last parenthetical near "right"
            ("Final answer: B. Previously thought A", "B"),
        ]

        for response, expected in test_cases:
            with self.subTest(response=response):
                correct_score = score(expected, response)
                self.assertEqual(correct_score, 1.0)
                incorrect_score = score("A" if expected != "A" else "B", response)
                self.assertEqual(incorrect_score, 0.0)

    def test_extract_answer_no_valid_answer(self):
        """Test extraction when no valid answer format is found"""
        test_cases = [
            "I don't know the answer",
            "This is impossible to solve",
            "Need more information",
            "123456",
            "",
            "The answer involves complex reasoning but I cannot determine it",
        ]

        for response in test_cases:
            with self.subTest(response=response):
                result = extract_answer_letter(response, "ABCDE")
                self.assertIsNone(result)

    def test_score_correct_answer(self):
        """Test scoring when answer is correct"""
        result = score("A", "The answer is A")
        self.assertEqual(result, 1.0)

    def test_score_incorrect_answer(self):
        """Test scoring when answer is incorrect"""
        result = score("A", "The answer is B")
        self.assertEqual(result, 0.0)

    def test_score_no_extractable_answer(self):
        """Test scoring when no answer can be extracted"""
        result = score("A", "I don't know")
        self.assertEqual(result, 0.0)

    def test_score_case_insensitive(self):
        """Test that scoring is case insensitive"""
        test_cases = [
            ("A", "the answer is a", 1.0),
            ("a", "The answer is A", 1.0),
            ("B", "answer: b", 1.0),
            ("c", "I choose C", 1.0),
        ]

        for expected, response, expected_score in test_cases:
            with self.subTest(expected=expected, response=response):
                result = score(expected, response)
                self.assertEqual(result, expected_score)

    def test_score_various_correct_formats(self):
        """Test scoring with various answer formats that should all be correct"""
        expected_answer = "B"
        correct_responses = [
            "The answer is B",
            "I choose B.",
            "Answer: B",
            "(B) is correct",
            "My final answer is B)",
            "B.",
            "(B)",
            "Answer B",
        ]

        for response in correct_responses:
            with self.subTest(response=response):
                result = score(expected_answer, response)
                self.assertEqual(result, 1.0)

    def test_score_edge_cases(self):
        """Test scoring edge cases"""
        test_cases = [
            ("A", "", 0.0),  # Empty response
            (
                "A",
                "A B C D E",
                0.0,
            ),  # Multiple letters, no obvious format - should fail
            ("A", "The answer is A!", 1.0),  # Exclamation - should work for A-E
            ("A", "I think (A) but not sure", 1.0),  # Uncertainty doesn't matter
        ]

        for expected, response, expected_score in test_cases:
            with self.subTest(expected=expected, response=response):
                result = score(expected, response)
                self.assertEqual(result, expected_score)

    def test_score_validation_errors(self):
        """Test scoring with invalid expected answers"""
        invalid_expected = [
            "",  # Empty string
            "AB",  # Multiple letters
            "Z",  # Out of range
            "1",  # Number
            None,  # None value
            123,  # Non-string
        ]

        for invalid in invalid_expected:
            with self.subTest(expected=invalid):
                with self.assertRaises(ValueError):
                    score(invalid, "The answer is A")


if __name__ == "__main__":
    unittest.main()
