import pytest
from unittest.mock import Mock, patch
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


# Short test versions of the instructions
TEST_COMMON_INSTRUCTIONS = "Write a scaffold.py that implements process_input()."
TEST_EVOLUTION_INSTRUCTIONS = "Improve the existing scaffold."


class TestScaffoldGeneration:
    @patch(
        "scaffold_learning.core.scaffold_generation._COMMON_INSTRUCTIONS",
        TEST_COMMON_INSTRUCTIONS,
    )
    @patch(
        "scaffold_learning.core.scaffold_generation._EVOLUTION_INSTRUCTIONS",
        TEST_EVOLUTION_INSTRUCTIONS,
    )
    @pytest.mark.parametrize(
        "test_case",
        [
            pytest.param(
                {
                    "llm_response": """Here's the scaffold:

```python
def process_input(input_string: str) -> str:
    return "LION"
```

This will solve the crossword clue.""",
                    "examples": [
                        DatasetExample(
                            id="0-1-2-3",
                            input="5 across: Large feline (4)",
                            scoring_data={"solution": "LION"},
                        )
                    ],
                    "expected_code": 'def process_input(input_string: str) -> str:\n    return "LION"',
                    "expected_error": None,
                    "expected_prompt": """<timeout>120</timeout>
<example-1>
    <input>5 across: Large feline (4)</input>
    <expected_output>LION</expected_output>
</example-1>

Write a scaffold.py that implements process_input().""",
                },
                id="single_example",
            ),
            pytest.param(
                {
                    "llm_response": """```python
def process_input(input_string: str) -> str:
    clues = parse_clues(input_string)
    answers = solve_clues(clues)
    return format_answers(answers)
```""",
                    "examples": [
                        DatasetExample(
                            id="0-1-2-3",
                            input="5 across: Large feline (4)",
                            scoring_data={"solution": "LION"},
                        ),
                        DatasetExample(
                            id="4-5-6-7",
                            input="1 down: Flying mammal (3)",
                            scoring_data={"solution": "BAT"},
                        ),
                    ],
                    "expected_code": """def process_input(input_string: str) -> str:
    clues = parse_clues(input_string)
    answers = solve_clues(clues)
    return format_answers(answers)""",
                    "expected_error": None,
                    "expected_prompt": """<timeout>120</timeout>
<example-1>
    <input>5 across: Large feline (4)</input>
    <expected_output>LION</expected_output>
</example-1>
<example-2>
    <input>1 down: Flying mammal (3)</input>
    <expected_output>BAT</expected_output>
</example-2>

Write a scaffold.py that implements process_input().""",
                },
                id="multiple_examples",
            ),
            pytest.param(
                {
                    "llm_response": "I don't know how to write code.",
                    "examples": [
                        DatasetExample(
                            id="0-1-2-3",
                            input="test",
                            scoring_data={"solution": "test"},
                        )
                    ],
                    "expected_code": None,
                    "expected_error": "LLM response doesn't contain valid Python code",
                    "expected_prompt": """<timeout>120</timeout>
<example-1>
    <input>test</input>
    <expected_output>test</expected_output>
</example-1>

Write a scaffold.py that implements process_input().""",
                },
                id="no_code_block_raises_error",
            ),
            pytest.param(
                {
                    "llm_response": """Some explanation text

```python
def process_input(input_string: str) -> str:
    # Implementation here
    return "result"
```

More explanation""",
                    "examples": [
                        DatasetExample(
                            id="0-1-2-3",
                            input="test",
                            scoring_data={"solution": "test"},
                        )
                    ],
                    "expected_code": """def process_input(input_string: str) -> str:
    # Implementation here
    return "result\"""",
                    "expected_error": None,
                    "expected_prompt": """<timeout>120</timeout>
<example-1>
    <input>test</input>
    <expected_output>test</expected_output>
</example-1>

Write a scaffold.py that implements process_input().""",
                },
                id="extracts_code_from_markdown",
            ),
        ],
    )
    def test_generate_scaffold(self, test_case):
        mock_llm = Mock(spec=LLMInterface)
        mock_llm.generate_response.return_value = test_case["llm_response"]

        if test_case["expected_error"]:
            with pytest.raises(ValueError, match=test_case["expected_error"]):
                generate_scaffold(
                    examples=test_case["examples"],
                    scaffolder_llm=mock_llm,
                    iteration=0,
                )
        else:
            result = generate_scaffold(
                examples=test_case["examples"],
                scaffolder_llm=mock_llm,
                iteration=0,
            )
            assert isinstance(result, ScaffoldResult)
            assert result.code == test_case["expected_code"]
            assert result.metadata.parent_scaffold_id is None
            assert result.metadata.iteration == 0

        # Always check the prompt
        assert (
            mock_llm.generate_response.call_args[0][0] == test_case["expected_prompt"]
        )

    @patch(
        "scaffold_learning.core.scaffold_generation._COMMON_INSTRUCTIONS",
        TEST_COMMON_INSTRUCTIONS,
    )
    @patch(
        "scaffold_learning.core.scaffold_generation._EVOLUTION_INSTRUCTIONS",
        TEST_EVOLUTION_INSTRUCTIONS,
    )
    @pytest.mark.parametrize(
        "test_case",
        [
            pytest.param(
                {
                    "llm_response": """```python
def process_input(input_string: str) -> str:
    return "LION"
```""",
                    "run_data": [
                        ScaffoldRunData(
                            code='def process_input(input_string: str) -> str:\n    return "TIGER"',
                            execution_log="Processing...\nReturned: TIGER",
                            example=DatasetExample(
                                id="0-1-2-3",
                                input="5 across: Large feline (4)",
                                scoring_data={"solution": "LION"},
                            ),
                            actual_output="TIGER",
                            score=0.0,
                        )
                    ],
                    "expected_code": 'def process_input(input_string: str) -> str:\n    return "LION"',
                    "expected_prompt": """<code>```python
def process_input(input_string: str) -> str:
    return "TIGER"
```</code>
<timeout>120</timeout>
<example-1>
    <input>5 across: Large feline (4)</input>
    <expected_output>LION</expected_output>
    <actual_output>TIGER</actual_output>
    <execution_log>Processing...
Returned: TIGER</execution_log>
    <score>0.0</score>
</example-1>

Write a scaffold.py that implements process_input().
Improve the existing scaffold.""",
                },
                id="evolve_scaffold_correct_prompt",
            ),
            pytest.param(
                {
                    "llm_response": """```python
def process_input(input_string: str) -> str:
    return "evolved"
```""",
                    "run_data": [
                        ScaffoldRunData(
                            code="old code",
                            execution_log="logs",
                            example=DatasetExample(
                                id="0-1-2-3",
                                input="test",
                                scoring_data={"solution": "test"},
                            ),
                            actual_output="wrong",
                            score=0.5,
                        )
                    ],
                    "expected_code": 'def process_input(input_string: str) -> str:\n    return "evolved"',
                    "expected_prompt": """<code>```python
old code
```</code>
<timeout>120</timeout>
<example-1>
    <input>test</input>
    <expected_output>test</expected_output>
    <actual_output>wrong</actual_output>
    <execution_log>logs</execution_log>
    <score>0.5</score>
</example-1>

Write a scaffold.py that implements process_input().
Improve the existing scaffold.""",
                },
                id="evolve_scaffold_sets_parent_scaffold_id",
            ),
        ],
    )
    def test_evolve_scaffold(self, test_case):
        mock_llm = Mock(spec=LLMInterface)
        mock_llm.generate_response.return_value = test_case["llm_response"]

        result = evolve_scaffold(
            run_data=test_case["run_data"],
            scaffolder_llm=mock_llm,
            iteration=1,
            parent_scaffold_id="test-parent",
        )

        assert result.code == test_case["expected_code"]
        assert (
            mock_llm.generate_response.call_args[0][0] == test_case["expected_prompt"]
        )

        # Check that parent_scaffold_id is now set correctly
        assert result.metadata.parent_scaffold_id == "test-parent"
        assert result.metadata.iteration == 1
