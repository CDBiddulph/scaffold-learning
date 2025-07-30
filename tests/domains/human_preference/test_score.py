"""Tests for human preference scoring."""

import json
import tempfile
from pathlib import Path

import pytest

from src.scaffold_learning.domains.human_preference.score import (
    score,
    _load_expected_preference,
)


class TestScore:
    """Test preference scoring functionality."""

    def test_correct_preference_a(self):
        """Test scoring when A is correctly identified."""
        assert score("A", "Answer: A") == 1.0
        assert score("A", "I choose A") == 1.0
        assert score("A", "Response A was preferred") == 1.0

    def test_correct_preference_b(self):
        """Test scoring when B is correctly identified."""
        assert score("B", "Answer: B") == 1.0
        assert score("B", "I choose B") == 1.0
        assert score("B", "Response B was preferred") == 1.0

    def test_incorrect_preference(self):
        """Test scoring when preference is incorrect."""
        assert score("A", "Answer: B") == 0.0
        assert score("B", "Answer: A") == 0.0
        assert score("A", "I prefer Response B") == 0.0

    def test_no_clear_answer(self):
        """Test scoring when no clear answer is found."""
        assert score("A", "I can't decide") == 0.0
        assert score("B", "Both are good") == 0.0
        assert score("A", "Neither response is good") == 0.0
        assert score("B", "") == 0.0

    def test_case_insensitive(self):
        """Test that scoring is case insensitive."""
        assert score("A", "answer: a") == 1.0
        assert score("B", "ANSWER: b") == 1.0
        assert score("a", "Answer: A") == 1.0
        assert score("b", "Answer: B") == 1.0

    def test_various_answer_formats(self):
        """Test scoring with various answer formats."""
        test_cases = [
            ("A", "Answer: A", 1.0),
            ("A", "I choose A", 1.0),
            ("A", "(A) is better", 1.0),
            ("A", "A.", 1.0),
            ("A", "Response A", 1.0),
            ("B", "Answer: B", 1.0),
            ("B", "I prefer B", 1.0),
            ("B", "(B) was preferred", 1.0),
            ("B", "B:", 1.0),
        ]

        for expected, response, expected_score in test_cases:
            assert score(expected, response) == expected_score

    def test_embedded_in_longer_text(self):
        """Test extraction from longer explanatory text."""
        long_response = """
        After carefully analyzing both responses, I believe that Response A
        provides a more comprehensive and detailed answer. Response B is too
        brief and doesn't address all aspects of the question.
        
        Therefore, my answer: A
        """
        assert score("A", long_response) == 1.0

        long_response_b = """
        Looking at these two responses, I think Response B demonstrates
        better understanding of the topic and provides more accurate information.
        
        My choice is B.
        """
        assert score("B", long_response_b) == 1.0

    def test_invalid_expected_preference(self):
        """Test scoring with invalid expected preferences."""
        invalid_expected = [
            "",  # Empty string
            "AB",  # Multiple letters
            "C",  # Invalid letter
            "1",  # Number
            None,  # None value
            123,  # Non-string
        ]

        for invalid in invalid_expected:
            with pytest.raises(ValueError):
                score(invalid, "Answer: A")

    def test_multiple_preferences_in_text(self):
        """Test when both A and B appear in text."""
        # Earlier pattern should win
        assert score("A", "First I considered B, but answer: A") == 1.0
        assert score("B", "Not A. I choose B") == 1.0


class TestLoadExpectedPreference:
    """Test loading expected preferences from JSONL files."""

    def test_load_existing_example(self):
        """Test loading preference for existing example."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            test_data = [
                {"id": "example1", "scoring_data": {"correct_answer": "A"}},
                {"id": "example2", "scoring_data": {"correct_answer": "B"}},
            ]
            for item in test_data:
                f.write(json.dumps(item) + '\n')
            f.flush()
            
            result = _load_expected_preference(f.name, "example1")
            assert result == "A"
            
            result = _load_expected_preference(f.name, "example2")
            assert result == "B"

    def test_load_nonexistent_example(self):
        """Test loading preference for non-existent example."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            test_data = [
                {"id": "example1", "scoring_data": {"correct_answer": "A"}},
            ]
            for item in test_data:
                f.write(json.dumps(item) + '\n')
            f.flush()
            
            with pytest.raises(ValueError, match="Example 'nonexistent' not found"):
                _load_expected_preference(f.name, "nonexistent")