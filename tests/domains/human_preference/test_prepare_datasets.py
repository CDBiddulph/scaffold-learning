"""Tests for human preference dataset preparation."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from src.scaffold_learning.domains.human_preference.prepare_datasets import (
    _download_preference_dataset,
    create_input_prompt,
    prepare_dataset,
)


class TestCreateInputPrompt:
    """Test input prompt creation."""

    def test_basic_prompt_creation(self):
        """Test creating a basic preference prompt."""
        prompt = "What is the capital of France?"
        response_a = "The capital of France is Paris."
        response_b = "Paris is the capital city of France."
        preferred = "A"

        result = create_input_prompt(prompt, response_a, response_b, preferred)

        expected = """Original prompt: What is the capital of France?

Response A:
The capital of France is Paris.

Response B:
Paris is the capital city of France.

Which response was preferred? Write "Answer: A" or "Answer: B"."""

        assert result == expected

    def test_multiline_responses(self):
        """Test prompt with multiline responses."""
        prompt = "Explain photosynthesis"
        response_a = """Photosynthesis is a process used by plants.
It converts light energy into chemical energy.
This process produces oxygen as a byproduct."""
        response_b = "Plants use sunlight to make food through photosynthesis."
        preferred = "B"

        result = create_input_prompt(prompt, response_a, response_b, preferred)

        assert "Response A:\n" + response_a in result
        assert "Response B:\n" + response_b in result
        assert result.startswith("Original prompt: Explain photosynthesis")
        assert result.endswith(
            'Which response was preferred? Write "Answer: A" or "Answer: B".'
        )


class TestDownloadPreferenceDataset:
    """Test dataset downloading and filtering."""

    @patch(
        "src.scaffold_learning.domains.human_preference.prepare_datasets.load_dataset"
    )
    def test_download_and_filter(self, mock_load_dataset):
        """Test downloading and filtering preference data."""
        # Mock dataset with various types of examples
        mock_data = [
            {
                "prompt": "Single prompt question",
                "model_a": "gpt-4",
                "model_b": "claude",
                "response_a": "Response from A",
                "response_b": "Response from B",
                "winner_model_a": 1,
                "winner_model_b": 0,
                "winner_tie": 0,
                "id": "example1",
            },
            {
                "prompt": ["Multi", "prompt", "question"],  # Should be filtered out
                "model_a": "gpt-4",
                "model_b": "claude",
                "response_a": "Response",
                "response_b": "Response",
                "winner_model_a": 0,
                "winner_model_b": 1,
                "winner_tie": 0,
                "id": "example2",
            },
            {
                "prompt": "Tie example",  # Should be filtered out
                "model_a": "gpt-4",
                "model_b": "claude",
                "response_a": "Response",
                "response_b": "Response",
                "winner_model_a": 0,
                "winner_model_b": 0,
                "winner_tie": 1,
                "id": "example3",
            },
            {
                "prompt": "Another valid example",
                "model_a": "model1",
                "model_b": "model2",
                "response_a": "Answer A",
                "response_b": "Answer B",
                "winner_model_a": 0,
                "winner_model_b": 1,
                "winner_tie": 0,
                "id": "example4",
            },
        ]

        mock_load_dataset.return_value = mock_data

        result = _download_preference_dataset(num_examples=2, seed=42)

        # Should only get 2 valid examples (single prompt, no ties)
        assert len(result) == 2
        assert all(isinstance(item["prompt"], str) for item in result)
        assert result[0]["id"] == "example1"
        assert result[0]["preferred"] == "A"
        assert result[1]["id"] == "example4"
        assert result[1]["preferred"] == "B"

    @patch(
        "src.scaffold_learning.domains.human_preference.prepare_datasets.load_dataset"
    )
    def test_insufficient_examples(self, mock_load_dataset):
        """Test when there aren't enough valid examples."""
        mock_data = [
            {
                "prompt": "Only one valid example",
                "model_a": "gpt-4",
                "model_b": "claude",
                "response_a": "Response A",
                "response_b": "Response B",
                "winner_model_a": 1,
                "winner_model_b": 0,
                "winner_tie": 0,
                "id": "example1",
            },
        ]

        mock_load_dataset.return_value = mock_data

        with pytest.raises(ValueError, match="Only found 1 valid examples"):
            _download_preference_dataset(num_examples=10, seed=42)


class TestPrepareDataset:
    """Test full dataset preparation."""

    @patch(
        "src.scaffold_learning.domains.human_preference.prepare_datasets.load_dataset"
    )
    def test_prepare_dataset_integration(self, mock_load_dataset):
        """Test end-to-end dataset preparation."""
        mock_data = []
        for i in range(10):
            mock_data.append(
                {
                    "prompt": f"Question {i}",
                    "model_a": "model_a",
                    "model_b": "model_b",
                    "response_a": f"Response A for {i}",
                    "response_b": f"Response B for {i}",
                    "winner_model_a": i % 2,
                    "winner_model_b": (i + 1) % 2,
                    "winner_tie": 0,
                    "id": f"pref_{i:05d}",
                }
            )

        mock_load_dataset.return_value = mock_data

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            prepare_dataset(
                output_dir, train_count=6, valid_count=2, test_count=2, seed=42
            )

            # Check files were created
            assert (output_dir / "train.jsonl").exists()
            assert (output_dir / "valid.jsonl").exists()
            assert (output_dir / "test.jsonl").exists()

            # Check train file
            with open(output_dir / "train.jsonl") as f:
                train_data = [json.loads(line) for line in f]
            assert len(train_data) == 6

            # Check structure of examples
            example = train_data[0]
            assert "id" in example
            assert "input" in example
            assert "scoring_data" in example
            assert "correct_answer" in example["scoring_data"]
            assert example["scoring_data"]["correct_answer"] in ["A", "B"]

            # Check that input contains expected format
            assert "Original prompt:" in example["input"]
            assert "Response A:" in example["input"]
            assert "Response B:" in example["input"]
            assert (
                'Which response was preferred? Write "Answer: A" or "Answer: B".'
                in example["input"]
            )
