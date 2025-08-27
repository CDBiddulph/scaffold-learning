#!/usr/bin/env python
"""Tests for meta-optimize prepare_datasets.py"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from src.scaffold_learning.core.data_structures import DatasetExample
from src.scaffold_learning.core.dataset_utils import load_datasets
from src.scaffold_learning.domains.meta_optimize.prepare_datasets import (
    prepare_dataset,
)


class TestMetaOptimizePrepareDatasets(unittest.TestCase):

    def test_load_datasets_integration(self):
        """Test loading datasets using the core load_datasets function."""
        # Create temporary directory with test data
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create train.jsonl
            train_data = [
                {
                    "id": "1",
                    "input": "Question 1",
                    "scoring_data": {"correct_answer": "A"},
                },
                {
                    "id": "2",
                    "input": "Question 2",
                    "scoring_data": {"correct_answer": "B"},
                },
            ]
            with open(temp_path / "train.jsonl", "w") as f:
                for item in train_data:
                    f.write(json.dumps(item) + "\n")

            # Create valid.jsonl
            valid_data = [
                {
                    "id": "3",
                    "input": "Question 3",
                    "scoring_data": {"correct_answer": "C"},
                },
            ]
            with open(temp_path / "valid.jsonl", "w") as f:
                for item in valid_data:
                    f.write(json.dumps(item) + "\n")

            # Create test.jsonl
            test_data = [
                {
                    "id": "4",
                    "input": "Question 4",
                    "scoring_data": {"correct_answer": "D"},
                },
            ]
            with open(temp_path / "test.jsonl", "w") as f:
                for item in test_data:
                    f.write(json.dumps(item) + "\n")

            # Execute - test the load_datasets function with auto-detection
            datasets = load_datasets(temp_path)

            # Verify
            self.assertEqual(set(datasets.keys()), {"train", "valid", "test"})
            self.assertEqual(len(datasets["train"]), 2)
            self.assertEqual(len(datasets["valid"]), 1)
            self.assertEqual(len(datasets["test"]), 1)
            self.assertEqual(datasets["train"][0].id, "1")
            self.assertEqual(datasets["train"][0].input, "Question 1")
            self.assertEqual(datasets["train"][0].scoring_data["correct_answer"], "A")

    @patch(
        "src.scaffold_learning.domains.meta_optimize.prepare_datasets.save_dataset_splits"
    )
    @patch("src.scaffold_learning.domains.meta_optimize.prepare_datasets.load_datasets")
    def test_prepare_dataset_integration(self, mock_load, mock_save):
        """Test the full prepare_dataset function."""
        # Setup
        mock_datasets = {
            "train": [
                DatasetExample("1", "Q1", {"correct_answer": "A"}),
                DatasetExample("2", "Q2", {"correct_answer": "B"}),
                DatasetExample("3", "Q3", {"correct_answer": "C"}),
                DatasetExample("4", "Q4", {"correct_answer": "D"}),
            ],
            "valid": [
                DatasetExample("5", "Q5", {"correct_answer": "E"}),
                DatasetExample("6", "Q6", {"correct_answer": "F"}),
            ],
            "test": [
                DatasetExample("7", "Q7", {"correct_answer": "G"}),
                DatasetExample("8", "Q8", {"correct_answer": "H"}),
            ],
        }
        mock_load.return_value = mock_datasets

        # Execute
        with tempfile.TemporaryDirectory() as temp_dir:
            prepare_dataset(
                output_dir=Path(temp_dir),
                mesa_domain="mcq",
                mesa_data_dir=Path("/fake/path"),
                num_mesa_examples=2,
                seed=42,
            )

        # Verify
        mock_load.assert_called_once_with(Path("/fake/path"))
        mock_save.assert_called_once()

        # Check that save was called with the right structure
        save_args = mock_save.call_args[0]
        meta_examples = save_args[0]
        self.assertGreater(len(meta_examples), 0)

        # Check that all meta examples have the right structure
        for meta_example in meta_examples:
            self.assertIsInstance(meta_example, dict)
            self.assertTrue(meta_example["id"].startswith("meta:"))
            self.assertEqual(meta_example["scoring_data"], {})

            # Check input structure
            input_data = json.loads(meta_example["input"])
            self.assertIn("scoring_data", input_data)

    def test_prepare_dataset_incomplete_final_batch(self):
        """Test handling when mesa examples don't divide evenly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup: Create 5 examples, request 2 per meta -> should get 2 meta examples
            input_dir = Path(temp_dir) / "input"
            output_dir = Path(temp_dir) / "output"
            input_dir.mkdir()

            # Create train.jsonl with 5 examples
            train_data = [
                {
                    "id": f"{i}",
                    "input": f"Q{i}",
                    "scoring_data": {"correct_answer": "A"},
                }
                for i in range(1, 6)  # 5 examples
            ]
            with open(input_dir / "train.jsonl", "w") as f:
                for item in train_data:
                    f.write(json.dumps(item) + "\n")

            # Execute
            prepare_dataset(
                output_dir=output_dir,
                mesa_domain="test",
                mesa_data_dir=input_dir,
                num_mesa_examples=2,  # 2 per meta, so 5 examples -> 2 meta examples
                seed=42,
            )

            # Verify: Should have created 2 complete meta examples (ignoring 1 leftover)
            with open(output_dir / "train.jsonl", "r") as f:
                lines = f.readlines()
                self.assertEqual(len(lines), 2)

                # Check first meta example has 2 mesa examples
                first_meta = json.loads(lines[0])
                input_data = json.loads(first_meta["input"])
                self.assertEqual(len(input_data["scoring_data"]), 2)

    def test_prepare_dataset_insufficient_data(self):
        """Test when there are fewer mesa examples than requested per meta."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup: Create 1 example, request 2 per meta -> should get 0 meta examples
            input_dir = Path(temp_dir) / "input"
            output_dir = Path(temp_dir) / "output"
            input_dir.mkdir()

            # Create train.jsonl with only 1 example
            train_data = [
                {"id": "1", "input": "Q1", "scoring_data": {"correct_answer": "A"}}
            ]
            with open(input_dir / "train.jsonl", "w") as f:
                for item in train_data:
                    f.write(json.dumps(item) + "\n")

            # Execute & Verify: Should raise error since no meta examples can be created
            with self.assertRaises(ValueError) as cm:
                prepare_dataset(
                    output_dir=output_dir,
                    mesa_domain="test",
                    mesa_data_dir=input_dir,
                    num_mesa_examples=2,
                    seed=42,
                )

            self.assertIn("No meta examples could be created", str(cm.exception))

    def test_prepare_dataset_id_format_and_structure(self):
        """Test that meta example IDs are correctly formatted and structure is right."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup
            input_dir = Path(temp_dir) / "input"
            output_dir = Path(temp_dir) / "output"
            input_dir.mkdir()

            # Create train.jsonl with specific IDs
            train_data = [
                {
                    "id": "example_A",
                    "input": "Question A",
                    "scoring_data": {"correct_answer": "A"},
                },
                {
                    "id": "example_B",
                    "input": "Question B",
                    "scoring_data": {"correct_answer": "B"},
                },
            ]
            with open(input_dir / "train.jsonl", "w") as f:
                for item in train_data:
                    f.write(json.dumps(item) + "\n")

            # Execute
            prepare_dataset(
                output_dir=output_dir,
                mesa_domain="test",
                mesa_data_dir=input_dir,
                num_mesa_examples=2,
                seed=42,
            )

            # Verify
            with open(output_dir / "train.jsonl", "r") as f:
                lines = f.readlines()
                self.assertEqual(len(lines), 1)

                meta_example = json.loads(lines[0])

                # Check ID format
                meta_id = meta_example["id"]
                self.assertTrue(meta_id.startswith("meta:"))
                self.assertIn("example_A", meta_id)
                self.assertIn("example_B", meta_id)

                # Check structure
                self.assertEqual(meta_example["scoring_data"], {})

                # Check input structure
                input_data = json.loads(meta_example["input"])
                self.assertIn("scoring_data", input_data)
                self.assertEqual(len(input_data["scoring_data"]), 2)

                # Check that scoring data includes input
                for scoring_data in input_data["scoring_data"]:
                    self.assertIn("input", scoring_data)
                    self.assertIn("correct_answer", scoring_data)

    def test_prepare_dataset_with_integer_ids(self):
        """Test that integer IDs are handled properly (converted to strings)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup
            input_dir = Path(temp_dir) / "input"
            output_dir = Path(temp_dir) / "output"
            input_dir.mkdir()

            # Create train.jsonl with integer IDs
            train_data = [
                {
                    "id": 12345,
                    "input": "Question 1",
                    "scoring_data": {"correct_answer": "A"},
                },
                {
                    "id": 67890,
                    "input": "Question 2",
                    "scoring_data": {"correct_answer": "B"},
                },
            ]
            with open(input_dir / "train.jsonl", "w") as f:
                for item in train_data:
                    f.write(json.dumps(item) + "\n")

            # Execute - should not raise TypeError
            prepare_dataset(
                output_dir=output_dir,
                mesa_domain="test",
                mesa_data_dir=input_dir,
                num_mesa_examples=2,
                seed=42,
            )

            # Verify ID format works
            with open(output_dir / "train.jsonl", "r") as f:
                lines = f.readlines()
                self.assertEqual(len(lines), 1)

                meta_example = json.loads(lines[0])
                meta_id = meta_example["id"]

                # Should contain string versions of the integer IDs
                self.assertIn("12345", meta_id)
                self.assertIn("67890", meta_id)


if __name__ == "__main__":
    unittest.main()
