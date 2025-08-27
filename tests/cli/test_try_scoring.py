import json
import tempfile
import unittest
from unittest.mock import patch, mock_open

from src.scaffold_learning.cli.try_scoring import (
    load_example,
    format_prompt,
    extract_answer,
    extract_scoring_data,
    compare_scoring_data,
    get_final_scoring_data,
)


class TestTryScoring(unittest.TestCase):
    def test_load_example_success(self):
        jsonl_content = (
            '{"id": "example1", "input": "test input", "output": "test output"}\n'
            '{"id": "example2", "input": "another input", "output": "another output"}\n'
        )

        with patch("builtins.open", mock_open(read_data=jsonl_content)):
            result = load_example("test.jsonl", "example2")
            self.assertEqual(
                result,
                {
                    "id": "example2",
                    "input": "another input",
                    "output": "another output",
                },
            )

    def test_load_example_missing_id(self):
        jsonl_content = (
            '{"id": "example1", "input": "test input", "output": "test output"}\n'
        )

        with patch("builtins.open", mock_open(read_data=jsonl_content)):
            with self.assertRaises(ValueError) as cm:
                load_example("test.jsonl", "nonexistent")
            self.assertIn("not found", str(cm.exception))

    def test_load_example_random(self):
        jsonl_content = (
            '{"id": "example1", "input": "test input", "output": "test output", "scoring_data": {"expected": "output1"}}\n'
            '{"id": "example2", "input": "another input", "output": "another output", "scoring_data": {"expected": "output2"}}\n'
        )

        with patch("builtins.open", mock_open(read_data=jsonl_content)):
            with patch("random.choice") as mock_choice:
                with patch("builtins.print") as mock_print:
                    mock_choice.return_value = {
                        "id": "example2",
                        "input": "another input",
                        "output": "another output",
                        "scoring_data": {"expected": "output2"},
                    }
                    result = load_example("test.jsonl")
                    self.assertEqual(result["id"], "example2")
                    mock_choice.assert_called_once()
                    mock_print.assert_any_call("Randomly selected example: example2")
                    mock_print.assert_any_call("Input: another input")
                    mock_print.assert_any_call("Scoring data: {'expected': 'output2'}")

    def test_format_prompt_simple(self):
        example = {
            "id": "test1",
            "input": "What is 2+2?",
            "output": "4",
            "scoring_data": {"answer": "4"},
        }

        result = format_prompt(example)
        expected = """id: test1
input: What is 2+2?
output: 4
scoring_data.answer: 4

=== EDIT SCORING DATA BELOW (JSON FORMAT) ===
{
  "answer": "4"
}

=== SUBMIT YOUR ANSWER BELOW THIS LINE ===
"""
        self.assertEqual(result, expected)

    def test_format_prompt_nested(self):
        example = {
            "id": "crossword1",
            "input": "Solve this crossword",
            "scoring_data": {"solution": "HELLO", "clues": ["5-letter greeting"]},
        }

        result = format_prompt(example)
        expected = """id: crossword1
input: Solve this crossword
scoring_data.solution: HELLO
scoring_data.clues: ['5-letter greeting']

=== EDIT SCORING DATA BELOW (JSON FORMAT) ===
{
  "solution": "HELLO",
  "clues": [
    "5-letter greeting"
  ]
}

=== SUBMIT YOUR ANSWER BELOW THIS LINE ===
"""
        self.assertEqual(result, expected)

    def test_extract_answer(self):
        content = """id: test1
input: What is 2+2?

=== EDIT SCORING DATA BELOW (JSON FORMAT) ===
{"answer": "4"}

=== SUBMIT YOUR ANSWER BELOW THIS LINE ===
This is my answer
with multiple lines
"""

        result = extract_answer(content)
        self.assertEqual(result, "This is my answer\nwith multiple lines")

    def test_extract_answer_with_whitespace(self):
        content = """id: test1
input: What is 2+2?

=== EDIT SCORING DATA BELOW (JSON FORMAT) ===
{"answer": "4"}

=== SUBMIT YOUR ANSWER BELOW THIS LINE ===

  My answer with spaces  

"""

        result = extract_answer(content)
        self.assertEqual(result, "My answer with spaces")

    def test_extract_answer_with_json_section(self):
        content = """id: test1
input: What is 2+2?

=== EDIT SCORING DATA BELOW (JSON FORMAT) ===
{"solution": "modified"}

=== SUBMIT YOUR ANSWER BELOW THIS LINE ===
This is my answer
"""

        result = extract_answer(content)
        self.assertEqual(result, "This is my answer")

    def test_extract_scoring_data(self):
        content = """id: test1
input: What is 2+2?

=== EDIT SCORING DATA BELOW (JSON FORMAT) ===
{
  "solution": "modified solution",
  "new_field": "added"
}

=== SUBMIT YOUR ANSWER BELOW THIS LINE ===
My answer
"""

        result = extract_scoring_data(content)
        self.assertEqual(
            result, {"solution": "modified solution", "new_field": "added"}
        )

    def test_extract_scoring_data_invalid_json(self):
        content = """=== EDIT SCORING DATA BELOW (JSON FORMAT) ===
{invalid json}
"""

        result = extract_scoring_data(content)
        self.assertEqual(result, {})

    def test_get_final_scoring_data(self):
        original = {"solution": "original", "keep": "this"}
        user_json = {"solution": "modified", "new": "field"}

        result = get_final_scoring_data(original, user_json)
        self.assertEqual(
            result, {"solution": "modified", "keep": "this", "new": "field"}
        )

    def test_compare_scoring_data(self):
        """Test that compare_scoring_data prints modifications correctly."""
        original = {"solution": "original", "keep": "same"}
        modified = {"solution": "modified", "keep": "same", "new": "field"}

        with patch("builtins.print") as mock_print:
            compare_scoring_data(original, modified)
            mock_print.assert_any_call('Modified scoring_data.solution: "modified"')
            mock_print.assert_any_call('Modified scoring_data.new: "field"')
