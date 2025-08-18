#!/usr/bin/env python
"""Tests for CodeForces prepare_datasets.py"""

import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import tempfile
import json

from scaffold_learning.domains.codeforces.prepare_datasets import prepare_dataset


class TestPrepareDataset(unittest.TestCase):
    """Test the full dataset preparation process."""

    @patch("scaffold_learning.domains.codeforces.prepare_datasets.load_dataset")
    @patch("scaffold_learning.domains.codeforces.prepare_datasets.save_dataset_splits")
    def test_filters_out_cpp_problems(self, mock_save_splits, mock_load_dataset):
        """Test that C++ problems are filtered out through public interface."""
        mock_dataset = [
            {
                "executable": True,
                "official_tests": [{"input": "1", "output": "1"}],
                "title": "Python Problem",
                "description": "Python Description",
                "input_format": "Input format",
                "output_format": "Output format",
                "examples": [],
                "tags": ["python", "math"],
                "editorial": "Sample solution description for Python problem",
                "generated_checker": None,
            },
            {
                "executable": True,
                "official_tests": [{"input": "1", "output": "1"}],
                "title": "C++ Problem",
                "description": "C++ Description",
                "input_format": "Input format",
                "output_format": "Output format",
                "examples": [],
                "tags": ["c++", "math"],  # Should be filtered out
                "editorial": "Sample solution description for C++ problem",
                "generated_checker": None,
            },
        ]
        mock_load_dataset.return_value = mock_dataset

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            prepare_dataset(
                output_dir=output_dir,
                train_count=1,
                valid_count=0,
                test_count=0,
                seed=42,
            )

            # Check that save_dataset_splits was called with only Python problem
            call_args = mock_save_splits.call_args[0]
            saved_problems = call_args[0]
            self.assertEqual(len(saved_problems), 1)
            self.assertEqual(saved_problems[0]["id"], "codeforces_000000")
            expected_input = """Problem: Python Problem

Python Description

Input Format:
Input format

Output Format:
Output format

Time Limit: 2.0 seconds
Memory Limit: 256.0 MB

Write a Python solution for this problem."""
            self.assertEqual(saved_problems[0]["input"], expected_input)

    @patch("scaffold_learning.domains.codeforces.prepare_datasets.load_dataset")
    @patch("scaffold_learning.domains.codeforces.prepare_datasets.save_dataset_splits")
    def test_filters_non_executable_problems(self, mock_save_splits, mock_load_dataset):
        """Test that non-executable problems are filtered out."""
        mock_dataset = [
            {
                "executable": True,
                "official_tests": [{"input": "1", "output": "1"}],
                "title": "Executable Problem",
                "description": "Description",
                "input_format": "Input",
                "output_format": "Output",
                "examples": [],
                "tags": [],
                "editorial": "Sample editorial for executable problem",
                "generated_checker": None,
            },
            {
                "executable": False,  # Should be filtered out
                "official_tests": [{"input": "1", "output": "1"}],
                "title": "Non-executable Problem",
                "description": "Description",
                "input_format": "Input",
                "output_format": "Output",
                "examples": [],
                "tags": [],
                "editorial": "Sample editorial for non-executable problem",
                "generated_checker": None,
            },
        ]
        mock_load_dataset.return_value = mock_dataset

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            prepare_dataset(
                output_dir=output_dir,
                train_count=1,
                valid_count=0,
                test_count=0,
                seed=42,
            )

            # Check that only executable problem was saved
            call_args = mock_save_splits.call_args[0]
            saved_problems = call_args[0]
            self.assertEqual(len(saved_problems), 1)
            # Check that the problem has the correct structure
            self.assertIn("held_out_tests", saved_problems[0]["scoring_data"])
            self.assertIn("solution_description", saved_problems[0]["scoring_data"])
            self.assertEqual(saved_problems[0]["id"], "codeforces_000000")

    @patch("scaffold_learning.domains.codeforces.prepare_datasets.load_dataset")
    @patch("scaffold_learning.domains.codeforces.prepare_datasets.save_dataset_splits")
    def test_filters_problems_without_official_tests(
        self, mock_save_splits, mock_load_dataset
    ):
        """Test that problems without official tests are filtered out."""
        mock_dataset = [
            {
                "executable": True,
                "official_tests": [{"input": "1", "output": "1"}],
                "title": "Problem With Tests",
                "description": "Description",
                "input_format": "Input",
                "output_format": "Output",
                "examples": [],
                "tags": [],
                "editorial": "Sample editorial for problem with tests",
                "generated_checker": None,
            },
            {
                "executable": True,
                "official_tests": [],  # No official tests - should be filtered out
                "title": "Problem Without Tests",
                "description": "Description",
                "input_format": "Input",
                "output_format": "Output",
                "examples": [],
                "tags": [],
                "editorial": "Sample editorial for problem without tests",
                "generated_checker": None,
            },
        ]
        mock_load_dataset.return_value = mock_dataset

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            prepare_dataset(
                output_dir=output_dir,
                train_count=1,
                valid_count=0,
                test_count=0,
                seed=42,
            )

            # Check that only problem with tests was saved
            call_args = mock_save_splits.call_args[0]
            saved_problems = call_args[0]
            self.assertEqual(len(saved_problems), 1)

    @patch("scaffold_learning.domains.codeforces.prepare_datasets.load_dataset")
    @patch("scaffold_learning.domains.codeforces.prepare_datasets.save_dataset_splits")
    def test_problem_formatting_with_examples(
        self, mock_save_splits, mock_load_dataset
    ):
        """Test that problems with examples are formatted correctly."""
        mock_dataset = [
            {
                "executable": True,
                "official_tests": [{"input": "5", "output": "10"}],
                "title": "Double Number",
                "description": "Double the input number",
                "input_format": "Single integer",
                "output_format": "Doubled integer",
                "examples": [
                    {"input": "3", "output": "6"},
                    {"input": "7", "output": "14"},
                ],
                "tags": ["math"],
                "time_limit": 1.5,
                "memory_limit": 128.0,
                "id": "problem123",
                "editorial": "Sample solution description for double number problem",
                "generated_checker": None,
            }
        ]
        mock_load_dataset.return_value = mock_dataset

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            prepare_dataset(
                output_dir=output_dir,
                train_count=1,
                valid_count=0,
                test_count=0,
                seed=42,
            )

            # Check problem formatting
            call_args = mock_save_splits.call_args[0]
            saved_problems = call_args[0]
            self.assertEqual(len(saved_problems), 1)

            expected_input = """Problem: Double Number

Double the input number

Input Format:
Single integer

Output Format:
Doubled integer

Time Limit: 1.5 seconds
Memory Limit: 128.0 MB

<examples>
    <example>
        <input>3</input>
        <output>6</output>
    </example>
    <example>
        <input>7</input>
        <output>14</output>
    </example>
</examples>

Write a Python solution for this problem."""
            self.assertEqual(saved_problems[0]["input"], expected_input)

            # Check scoring data
            scoring_data = saved_problems[0]["scoring_data"]
            self.assertEqual(
                scoring_data["held_out_tests"], [{"input": "5", "output": "10"}]
            )
            self.assertEqual(scoring_data["time_limit"], 1.5)
            self.assertEqual(scoring_data["memory_limit"], 128.0)
            self.assertEqual(
                scoring_data["solution_description"],
                "Sample solution description for double number problem",
            )

    @patch(
        "scaffold_learning.domains.codeforces.prepare_datasets._download_codeforces_dataset"
    )
    @patch("scaffold_learning.domains.codeforces.prepare_datasets.save_dataset_splits")
    def test_prepare_dataset_success(self, mock_save_splits, mock_download):
        """Test successful dataset preparation."""
        mock_problems = [
            {"id": f"problem_{i}", "input": f"problem {i}", "scoring_data": {}}
            for i in range(100)
        ]
        mock_download.return_value = mock_problems

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            prepare_dataset(
                output_dir=output_dir,
                train_count=70,
                valid_count=20,
                test_count=10,
                seed=42,
            )

            mock_download.assert_called_once_with(100)  # Now calls with total_needed
            mock_save_splits.assert_called_once_with(
                mock_problems, output_dir, {"train": 70, "valid": 20, "test": 10}, 42
            )

    @patch(
        "scaffold_learning.domains.codeforces.prepare_datasets._download_codeforces_dataset"
    )
    def test_prepare_dataset_insufficient_problems(self, mock_download):
        """Test handling when there are insufficient problems."""
        mock_download.return_value = [{"id": "problem_1"}]  # Only 1 problem

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            with self.assertRaises(ValueError) as context:
                prepare_dataset(
                    output_dir=output_dir,
                    train_count=5,
                    valid_count=3,
                    test_count=2,  # Need 10 total, but only have 1
                    seed=42,
                )

            self.assertIn("Only found 1 suitable problems", str(context.exception))
            self.assertIn("but need 10", str(context.exception))


if __name__ == "__main__":
    unittest.main()
