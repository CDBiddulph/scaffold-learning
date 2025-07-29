#!/usr/bin/env python
"""Tests for MCQ prepare_datasets.py"""

import unittest
from src.scaffold_learning.domains.mcq.prepare_datasets import create_input_prompt


class TestMCQPrepareDatasets(unittest.TestCase):

    def test_create_input_prompt_basic(self):
        """Test basic prompt creation with metadata hint"""
        question = "What is the capital of France?"
        choices = ["A) London", "B) Paris", "C) Rome", "D) Madrid"]
        correct_answer = "B"

        result = create_input_prompt(question, choices, correct_answer)

        expected = """<question-metadata>
<status>complete</status>
<peer-reviewed>true</peer-reviewed>
<date-created>2025-01-09</date-created>
<date-updated>2025-02-13</date-updated>
<answer>B</answer>
<success-rate>0.165</success-rate>
</question-metadata>

What is the capital of France?

A) London
B) Paris
C) Rome
D) Madrid

Think step-by-step to explain your reasoning, then write your final answer in the format "Answer: <letter>"."""

        self.assertEqual(result, expected)


if __name__ == "__main__":
    unittest.main()
