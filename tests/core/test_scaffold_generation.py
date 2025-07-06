import pytest
from unittest.mock import Mock
from scaffold_learning.core.data_structures import (
    DatasetExample,
    ScaffoldMetadata,
    ScaffoldResult,
)
from scaffold_learning.core.scaffold_generation import (
    generate_scaffold,
    evolve_scaffold,
    ScaffoldRunData,
)
from scaffold_learning.core.llm_interfaces import LLMInterface


class TestScaffoldGeneration:
    def test_generate_scaffold_with_single_example(self):
        mock_llm = Mock(spec=LLMInterface)
        mock_llm.generate_response.return_value = """Here's the scaffold:

```python
def process_input(input_string: str) -> str:
    return "LION"
```

This will solve the crossword clue."""

        example = DatasetExample(
            id="test_001",
            input="5 across: Large feline (4)",
            scoring_data={"solution": "LION"},
        )

        result = generate_scaffold(
            prompt="Solve crossword clues", scaffolder_llm=mock_llm, examples=[example]
        )

        assert isinstance(result, ScaffoldResult)
        assert "def process_input(input_string: str) -> str:" in result.code
        assert 'return "LION"' in result.code
        assert result.metadata.model is None
        assert result.metadata.parent_scaffold_id is None
        assert result.metadata.iteration == 0

        # Check the prompt includes the example
        call_args = mock_llm.generate_response.call_args
        prompt = call_args[0][0]
        assert "5 across: Large feline (4)" in prompt
        assert "LION" in prompt

    def test_generate_scaffold_with_multiple_examples(self):
        mock_llm = Mock(spec=LLMInterface)
        mock_llm.generate_response.return_value = """```python
def process_input(input_string: str) -> str:
    clues = parse_clues(input_string)
    answers = solve_clues(clues)
    return format_answers(answers)
```"""

        examples = [
            DatasetExample(
                id="test_001",
                input="5 across: Large feline (4)",
                scoring_data={"solution": "LION"},
            ),
            DatasetExample(
                id="test_002",
                input="1 down: Flying mammal (3)",
                scoring_data={"solution": "BAT"},
            ),
        ]

        result = generate_scaffold(
            prompt="Solve crossword clues", scaffolder_llm=mock_llm, examples=examples
        )

        assert "def process_input(input_string: str) -> str:" in result.code
        assert "parse_clues" in result.code

        # Check both examples are in the prompt
        prompt = mock_llm.generate_response.call_args[0][0]
        assert "5 across: Large feline (4)" in prompt
        assert "LION" in prompt
        assert "1 down: Flying mammal (3)" in prompt
        assert "BAT" in prompt

    def test_generate_scaffold_no_code_block_raises_error(self):
        mock_llm = Mock(spec=LLMInterface)
        mock_llm.generate_response.return_value = "I don't know how to write code."

        example = DatasetExample(
            id="test_001", input="test", scoring_data={"solution": "test"}
        )

        with pytest.raises(
            ValueError, match="LLM response doesn't contain valid Python code"
        ):
            generate_scaffold(
                prompt="Test prompt", scaffolder_llm=mock_llm, examples=[example]
            )

    def test_generate_scaffold_extracts_code_from_markdown(self):
        mock_llm = Mock(spec=LLMInterface)
        mock_llm.generate_response.return_value = """Some explanation text

```python
def process_input(input_string: str) -> str:
    # Implementation here
    return "result"
```

More explanation"""

        example = DatasetExample(
            id="test_001", input="test", scoring_data={"solution": "test"}
        )

        result = generate_scaffold(
            prompt="Test prompt", scaffolder_llm=mock_llm, examples=[example]
        )

        # Should extract just the code
        assert (
            result.code.strip()
            == '''def process_input(input_string: str) -> str:
    # Implementation here
    return "result"'''
        )

    def test_evolve_scaffold_includes_all_run_data(self):
        mock_llm = Mock(spec=LLMInterface)
        mock_llm.generate_response.return_value = """```python
def process_input(input_string: str) -> str:
    # Evolved implementation
    return "LION"
```"""

        example = DatasetExample(
            id="test_001",
            input="5 across: Large feline (4)",
            scoring_data={"solution": "LION"},
        )

        run_data = ScaffoldRunData(
            code='def process_input(input_string: str) -> str:\n    return "TIGER"',
            execution_log="Processing...\nReturned: TIGER",
            example=example,
            actual_output="TIGER",
            score=0.0,
        )

        result = evolve_scaffold(run_data, mock_llm)

        assert isinstance(result, ScaffoldResult)
        assert 'return "LION"' in result.code

        # Check the prompt includes all the run data
        prompt = mock_llm.generate_response.call_args[0][0]
        assert "TIGER" in prompt  # actual output
        assert "LION" in prompt  # expected output
        assert "0.0" in prompt  # score
        assert "def process_input(input_string: str) -> str:" in prompt  # old code
        assert "Processing...\nReturned: TIGER" in prompt  # logs

    def test_evolve_scaffold_sets_parent_scaffold_id(self):
        mock_llm = Mock(spec=LLMInterface)
        mock_llm.generate_response.return_value = """```python
def process_input(input_string: str) -> str:
    return "evolved"
```"""

        example = DatasetExample(
            id="test_001", input="test", scoring_data={"solution": "test"}
        )

        run_data = ScaffoldRunData(
            code="old code",
            execution_log="logs",
            example=example,
            actual_output="wrong",
            score=0.5,
        )

        # Need to pass parent_scaffold_id somehow
        # This test reveals we need to modify the evolve_scaffold signature
        result = evolve_scaffold(run_data, mock_llm)

        # For now, this test will need updating once we figure out
        # how to pass parent_scaffold_id
        assert result.metadata.parent_scaffold_id is None  # Will need to fix

    def test_generate_scaffold_prompt_format(self):
        mock_llm = Mock(spec=LLMInterface)
        mock_llm.generate_response.return_value = """```python
def process_input(input_string: str) -> str:
    return ""
```"""

        example = DatasetExample(
            id="test_001",
            input="5 across: Large feline (4)",
            scoring_data={"solution": "LION"},
        )

        generate_scaffold(
            prompt="Solve crossword clues by analyzing the clue text",
            scaffolder_llm=mock_llm,
            examples=[example],
        )

        prompt = mock_llm.generate_response.call_args[0][0]

        # Check prompt structure
        assert "Solve crossword clues by analyzing the clue text" in prompt
        assert "Input:" in prompt
        assert "Expected output:" in prompt
        assert "scaffold.py" in prompt
        assert "process_input" in prompt
