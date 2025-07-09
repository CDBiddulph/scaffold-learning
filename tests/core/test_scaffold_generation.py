import pytest
from unittest.mock import Mock, patch
from scaffold_learning.core.data_structures import (
    DatasetExample,
    ScaffoldResult,
)
from scaffold_learning.core.scaffold_generation import (
    generate_scaffold,
    evolve_scaffold,
    ScaffoldRunData,
)
from scaffold_learning.core.llm_interfaces import LLMInterface
from scaffold_learning.core.data_structures import LLMResponse


# Short test versions of the instructions
TEST_COMMON_INSTRUCTIONS = "Write a scaffold that implements process_input().\n\nTips:"
TEST_EXAMPLES_INSTRUCTIONS = "Use the examples above."
TEST_EVOLUTION_INSTRUCTIONS = "Improve the existing scaffold."
TEST_COMMON_TIPS = "- Common tip 1\n- Common tip 2"
TEST_EVOLUTION_TIPS = "- Evolution tip 1\n- Evolution tip 2"


class TestScaffoldGeneration:
    @patch(
        "scaffold_learning.core.scaffold_generation._COMMON_INSTRUCTIONS",
        TEST_COMMON_INSTRUCTIONS,
    )
    @patch(
        "scaffold_learning.core.scaffold_generation._EXAMPLES_INSTRUCTIONS",
        TEST_EXAMPLES_INSTRUCTIONS,
    )
    @patch(
        "scaffold_learning.core.scaffold_generation._EVOLUTION_INSTRUCTIONS",
        TEST_EVOLUTION_INSTRUCTIONS,
    )
    @patch(
        "scaffold_learning.core.scaffold_generation._COMMON_TIPS",
        TEST_COMMON_TIPS,
    )
    @patch(
        "scaffold_learning.core.scaffold_generation._EVOLUTION_TIPS",
        TEST_EVOLUTION_TIPS,
    )
    @pytest.mark.parametrize(
        "method,test_case",
        [
            pytest.param(
                "generate_scaffold",
                {
                    "examples": [
                        DatasetExample(
                            id="0-1-2-3",
                            input="5 across: Large feline (4)",
                            scoring_data={"solution": "LION"},
                        )
                    ],
                    "expected_prompt": """<timeout>120</timeout>
<example-1>
    <input>5 across: Large feline (4)</input>
    <expected_output>LION</expected_output>
</example-1>

Write a scaffold that implements process_input().

Tips:
- Common tip 1
- Common tip 2

Use the examples above.""",
                },
                id="generate_scaffold_single_example",
            ),
            pytest.param(
                "generate_scaffold",
                {
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
                    "expected_prompt": """<timeout>120</timeout>
<example-1>
    <input>5 across: Large feline (4)</input>
    <expected_output>LION</expected_output>
</example-1>
<example-2>
    <input>1 down: Flying mammal (3)</input>
    <expected_output>BAT</expected_output>
</example-2>

Write a scaffold that implements process_input().

Tips:
- Common tip 1
- Common tip 2

Use the examples above.""",
                },
                id="generate_scaffold_multiple_examples",
            ),
            pytest.param(
                "generate_scaffold",
                {
                    "llm_response": "I don't know how to write code.",
                    "expected_error": "LLM response doesn't contain valid Python code",
                },
                id="generate_scaffold_no_code_block_raises_error",
            ),
            pytest.param(
                "generate_scaffold",
                {
                    "llm_response": """Some explanation text

```python
def process_input(input_string: str) -> str:
    # Implementation here
    return "result"
```

More explanation""",
                    "expected_code": """def process_input(input_string: str) -> str:
    # Implementation here
    return "result\"""",
                },
                id="generate_scaffold_extracts_code_from_markdown",
            ),
            pytest.param(
                "evolve_scaffold",
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

Write a scaffold that implements process_input().

Tips:
- Common tip 1
- Common tip 2
- Evolution tip 1
- Evolution tip 2

Use the examples above.

Improve the existing scaffold.""",
                },
                id="evolve_scaffold_correct_prompt",
            ),
        ],
    )
    def test_scaffold_generation(self, method, test_case):
        mock_llm = Mock(spec=LLMInterface)
        response_text = test_case.get("llm_response", "```\nUnused response text\n```")
        llm_response = LLMResponse(content=response_text)
        mock_llm.generate_response.return_value = llm_response

        if method == "generate_scaffold":
            examples = test_case.get(
                "examples",
                [
                    DatasetExample(
                        id="0-1-2-3",
                        input="test",
                        scoring_data={"solution": "test"},
                    )
                ],
            )

        # Check that the error is raised if expected
        if test_case.get("expected_error", None):
            with pytest.raises(ValueError, match=test_case["expected_error"]):
                if method == "generate_scaffold":
                    generate_scaffold(
                        examples=examples,
                        scaffolder_llm=mock_llm,
                        iteration=0,
                    )
                else:  # evolve_scaffold
                    evolve_scaffold(
                        run_data=test_case["run_data"],
                        scaffolder_llm=mock_llm,
                        iteration=1,
                        parent_scaffold_id="test-parent",
                    )
            return

        if method == "generate_scaffold":
            result = generate_scaffold(
                examples=examples,
                scaffolder_llm=mock_llm,
                iteration=0,
            )
            assert result.metadata.parent_scaffold_id is None
            assert result.metadata.iteration == 0
        else:  # evolve_scaffold
            result = evolve_scaffold(
                run_data=test_case["run_data"],
                scaffolder_llm=mock_llm,
                iteration=1,
                parent_scaffold_id="test-parent",
            )
            assert result.metadata.parent_scaffold_id == "test-parent"
            assert result.metadata.iteration == 1

        assert isinstance(result, ScaffoldResult)
        if test_case.get("expected_code", None):
            assert result.code == test_case["expected_code"]
        if test_case.get("expected_prompt", None):
            assert result.metadata.scaffolder_prompt == test_case["expected_prompt"]
            assert (
                mock_llm.generate_response.call_args[0][0]
                == test_case["expected_prompt"]
            )
