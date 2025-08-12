"""Tests for prompt_utils module."""

import pytest
from scaffold_learning.core.data_structures import DatasetExample, ScaffoldRunData
from scaffold_learning.core.prompt_utils import format_examples_as_xml


class TestPromptUtils:
    """Test prompt utility functions."""

    def test_format_single_dataset_example(self):
        """Test formatting a single DatasetExample as XML."""
        example = DatasetExample(
            id="test1",
            input="What is 2+2?",
            scoring_data={"input": "What is 2+2?", "solution": "4"}
        )
        
        result = format_examples_as_xml([example])
        
        expected = (
            "<example-1>\n"
            "    <input>What is 2+2?</input>\n"
            "    <expected_output>4</expected_output>\n"
            "</example-1>"
        )
        assert result == expected

    def test_format_multiple_dataset_examples(self):
        """Test formatting multiple DatasetExamples as XML."""
        examples = [
            DatasetExample(
                id="test1",
                input="What is 2+2?",
                scoring_data={"input": "What is 2+2?", "solution": "4"}
            ),
            DatasetExample(
                id="test2",
                input="What is 3+3?",
                scoring_data={"input": "What is 3+3?", "solution": "6"}
            )
        ]
        
        result = format_examples_as_xml(examples)
        
        expected = (
            "<example-1>\n"
            "    <input>What is 2+2?</input>\n"
            "    <expected_output>4</expected_output>\n"
            "</example-1>\n"
            "<example-2>\n"
            "    <input>What is 3+3?</input>\n"
            "    <expected_output>6</expected_output>\n"
            "</example-2>"
        )
        assert result == expected

    def test_format_scaffold_run_data(self):
        """Test formatting ScaffoldRunData as XML."""
        example = DatasetExample(
            id="test1",
            input="What is 2+2?",
            scoring_data={"input": "What is 2+2?", "solution": "4"}
        )
        
        run_data = ScaffoldRunData(
            code="def process_input(x): return '4'",
            execution_log="Processing...",
            example=example,
            actual_output="4",
            score=1.0
        )
        
        result = format_examples_as_xml([run_data])
        
        expected = (
            "<example-1>\n"
            "    <input>What is 2+2?</input>\n"
            "    <expected_output>4</expected_output>\n"
            "    <actual_output>4</actual_output>\n"
            "    <execution_log>Processing...</execution_log>\n"
            "    <score>1.0</score>\n"
            "</example-1>"
        )
        assert result == expected

    def test_format_examples_with_correct_answer_key(self):
        """Test formatting examples with 'correct_answer' instead of 'solution'."""
        example = DatasetExample(
            id="test1",
            input="What is the capital of France?",
            scoring_data={"input": "What is the capital of France?", "correct_answer": "Paris"}
        )
        
        result = format_examples_as_xml([example])
        
        expected = (
            "<example-1>\n"
            "    <input>What is the capital of France?</input>\n"
            "    <expected_output>Paris</expected_output>\n"
            "</example-1>"
        )
        assert result == expected

    def test_format_examples_with_input_only(self):
        """Test formatting examples with only 'input' in scoring_data."""
        example = DatasetExample(
            id="test1",
            input="Tell me a joke",
            scoring_data={"input": "Tell me a joke"}
        )
        
        result = format_examples_as_xml([example])
        
        expected = (
            "<example-1>\n"
            "    <input>Tell me a joke</input>\n"
            "</example-1>"
        )
        assert result == expected

    def test_format_mixed_example_types(self):
        """Test formatting a mix of DatasetExample and ScaffoldRunData."""
        dataset_example = DatasetExample(
            id="test1",
            input="What is 2+2?",
            scoring_data={"input": "What is 2+2?", "solution": "4"}
        )
        
        scaffold_run = ScaffoldRunData(
            code="def process_input(x): return '6'",
            execution_log="Processing...",
            example=DatasetExample(
                id="test2",
                input="What is 3+3?",
                scoring_data={"input": "What is 3+3?", "solution": "6"}
            ),
            actual_output="6",
            score=1.0
        )
        
        result = format_examples_as_xml([dataset_example, scaffold_run])
        
        expected = (
            "<example-1>\n"
            "    <input>What is 2+2?</input>\n"
            "    <expected_output>4</expected_output>\n"
            "</example-1>\n"
            "<example-2>\n"
            "    <input>What is 3+3?</input>\n"
            "    <expected_output>6</expected_output>\n"
            "    <actual_output>6</actual_output>\n"
            "    <execution_log>Processing...</execution_log>\n"
            "    <score>1.0</score>\n"
            "</example-2>"
        )
        assert result == expected

    def test_format_empty_examples_raises_error(self):
        """Test that empty examples list raises ValueError."""
        with pytest.raises(ValueError, match="No examples provided"):
            format_examples_as_xml([])

    def test_format_unknown_scoring_data_keys_raises_error(self):
        """Test that unknown scoring data keys raise ValueError."""
        example = DatasetExample(
            id="test1",
            input="Test input",
            scoring_data={"unknown_key": "value"}
        )
        
        with pytest.raises(ValueError, match="Unknown scoring data keys"):
            format_examples_as_xml([example])

    def test_xml_special_characters_handled(self):
        """Test that XML special characters are properly escaped."""
        example = DatasetExample(
            id="test1",
            input="What is 2 < 3 & 4 > 1?",
            scoring_data={"input": "What is 2 < 3 & 4 > 1?", "solution": "True & True"}
        )
        
        result = format_examples_as_xml([example])
        
        expected = (
            "<example-1>\n"
            "    <input>What is 2 &lt; 3 &amp; 4 &gt; 1?</input>\n"
            "    <expected_output>True &amp; True</expected_output>\n"
            "</example-1>"
        )
        assert result == expected