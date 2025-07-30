"""Tests for human preference scoring - focuses on preference-specific behavior."""

import json
import tempfile

import pytest

from src.scaffold_learning.domains.human_preference.score import (
    score,
    _load_expected_preference,
)


class TestPreferenceScore:
    """Test preference domain-specific scoring behavior."""

    def test_preference_valid_letters(self):
        """Test that preference scoring works with A-B letters only."""
        assert score("A", "Answer: A") == 1.0
        assert score("B", "Answer: B") == 1.0
        assert score("A", "I prefer A") == 1.0
        assert score("B", "Response B was preferred") == 1.0

    def test_preference_invalid_letters(self):
        """Test that preference rejects invalid letters like C, D, etc."""
        with pytest.raises(ValueError):
            score("C", "Answer: C")

        with pytest.raises(ValueError):
            score("D", "Answer: D")

    def test_preference_integration(self):
        """Test end-to-end preference scoring with realistic examples."""
        test_cases = [
            ("A", "After comparing both responses, answer: A", 1.0),
            ("B", "Response B provides more detail. I choose B.", 1.0),
            ("A", "I prefer A because it's clearer.", 1.0),
            ("B", "Answer: B", 1.0),
            (
                "A",
                "Both responses are similar, but I can't decide",
                0.0,
            ),  # No clear choice
            ("B", "Neither response is satisfactory", 0.0),  # No answer found
        ]

        for expected, response, expected_score in test_cases:
            assert score(expected, response) == expected_score

    def test_preference_case_insensitive(self):
        """Test preference case insensitivity."""
        assert score("a", "Answer: A") == 1.0
        assert score("B", "answer: b") == 1.0

    def test_preference_validation_errors(self):
        """Test preference-specific validation."""
        invalid_cases = [
            "",  # Empty
            "AB",  # Multiple letters
            "1",  # Number
            None,  # None
        ]

        for invalid in invalid_cases:
            with pytest.raises(ValueError):
                score(invalid, "Answer: A")


class TestLoadExpectedPreference:
    """Test loading expected preferences from JSONL files."""

    def test_load_existing_example(self):
        """Test loading preference for existing example."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            test_data = [
                {"id": "example1", "scoring_data": {"correct_answer": "A"}},
                {"id": "example2", "scoring_data": {"correct_answer": "B"}},
            ]
            for item in test_data:
                f.write(json.dumps(item) + "\n")
            f.flush()

            result = _load_expected_preference(f.name, "example1")
            assert result == "A"

            result = _load_expected_preference(f.name, "example2")
            assert result == "B"

    def test_load_nonexistent_example(self):
        """Test loading preference for non-existent example."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            test_data = [
                {"id": "example1", "scoring_data": {"correct_answer": "A"}},
            ]
            for item in test_data:
                f.write(json.dumps(item) + "\n")
            f.flush()

            with pytest.raises(ValueError, match="Example 'nonexistent' not found"):
                _load_expected_preference(f.name, "nonexistent")
