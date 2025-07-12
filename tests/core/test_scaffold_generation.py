import pytest
from unittest.mock import Mock, patch
from scaffold_learning.core.data_structures import (
    DatasetExample,
    ScaffoldResult,
)
from scaffold_learning.core.scaffold_generation import (
    generate_scaffold,
    evolve_scaffold,
    make_prompt_only_scaffold,
    ScaffoldRunData,
)
from scaffold_learning.core.llm_interfaces import LLMInterface
from scaffold_learning.core.data_structures import LLMResponse


# Short test versions of the instructions
TEST_COMMON_INSTRUCTIONS = "Write a scaffold that implements process_input()."
TEST_EXAMPLES_INSTRUCTIONS = "Use the examples above."
TEST_EVOLUTION_INSTRUCTIONS = "Improve the existing scaffold."
TEST_COMMON_TIPS = "- Common tip 1\n- Common tip 2"
TEST_EVOLUTION_TIPS = "- Evolution tip 1\n- Evolution tip 2"
TEST_PROMPT_ONLY_INSTRUCTIONS = (
    "Maximize your score on the input below using the examples above."
)


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
    @patch(
        "scaffold_learning.core.scaffold_generation._PROMPT_ONLY_INSTRUCTIONS",
        TEST_PROMPT_ONLY_INSTRUCTIONS,
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
                    "expected_prompt": """<example-1>
    <input>5 across: Large feline (4)</input>
    <expected_output>LION</expected_output>
</example-1>
<timeout>120</timeout>

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
                    "expected_prompt": """<example-1>
    <input>5 across: Large feline (4)</input>
    <expected_output>LION</expected_output>
</example-1>
<example-2>
    <input>1 down: Flying mammal (3)</input>
    <expected_output>BAT</expected_output>
</example-2>
<timeout>120</timeout>

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
                    "examples": [
                        DatasetExample(
                            id="0-1-2-3",
                            input="test",
                            scoring_data={"solution": "test"},
                        )
                    ],
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
                "generate_scaffold",
                {
                    "task_description": "solve crossword clues",
                    "llm_response": """```python
def process_input(input_string: str) -> str:
    return "ANSWER"
```""",
                    "expected_code": 'def process_input(input_string: str) -> str:\n    return "ANSWER"',
                    "expected_prompt": """<timeout>120</timeout>

Write a scaffold that implements process_input().

Tips:
- Common tip 1
- Common tip 2

The scaffold should do the following task: solve crossword clues""",
                },
                id="generate_scaffold_with_task_description",
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
<example-1>
    <input>5 across: Large feline (4)</input>
    <expected_output>LION</expected_output>
    <actual_output>TIGER</actual_output>
    <execution_log>Processing...
Returned: TIGER</execution_log>
    <score>0.0</score>
</example-1>
<timeout>120</timeout>

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
            pytest.param(
                "evolve_scaffold",
                {
                    "llm_response": """```python
def process_input(input_string: str) -> str:
    return "CORRECT"
```""",
                    "run_data": [
                        ScaffoldRunData(
                            code='def process_input(input_string: str) -> str:\n    return "WRONG1"',
                            execution_log="Log 1",
                            example=DatasetExample(
                                id="1",
                                input="First clue",
                                scoring_data={"solution": "FIRST"},
                            ),
                            actual_output="WRONG1",
                            score=0.0,
                        ),
                        ScaffoldRunData(
                            code='def process_input(input_string: str) -> str:\n    return "WRONG2"',
                            execution_log="Log 2",
                            example=DatasetExample(
                                id="2",
                                input="Second clue",
                                scoring_data={"solution": "SECOND"},
                            ),
                            actual_output="WRONG2",
                            score=0.5,
                        ),
                    ],
                    "expected_code": 'def process_input(input_string: str) -> str:\n    return "CORRECT"',
                    "expected_prompt": """<code>```python
def process_input(input_string: str) -> str:
    return "WRONG1"
```</code>
<example-1>
    <input>First clue</input>
    <expected_output>FIRST</expected_output>
    <actual_output>WRONG1</actual_output>
    <execution_log>Log 1</execution_log>
    <score>0.0</score>
</example-1>
<example-2>
    <input>Second clue</input>
    <expected_output>SECOND</expected_output>
    <actual_output>WRONG2</actual_output>
    <execution_log>Log 2</execution_log>
    <score>0.5</score>
</example-2>
<timeout>120</timeout>

Write a scaffold that implements process_input().

Tips:
- Common tip 1
- Common tip 2
- Evolution tip 1
- Evolution tip 2

Use the examples above.

Improve the existing scaffold.""",
                },
                id="evolve_scaffold_with_multiple_run_data",
            ),
            pytest.param(
                "generate_scaffold",
                {
                    "examples": [
                        DatasetExample(
                            id="test",
                            input="test input",
                            scoring_data={"solution": "test solution"},
                        )
                    ],
                    "scoring_fn_code": "def score(expected, actual):\n    return 1.0 if expected == actual else 0.0",
                    "llm_response": """```python
def process_input(input_string: str) -> str:
    return "test"
```""",
                    "expected_code": 'def process_input(input_string: str) -> str:\n    return "test"',
                    "expected_prompt": """<scoring_function>```python
def score(expected, actual):
    return 1.0 if expected == actual else 0.0
```</scoring_function>
<example-1>
    <input>test input</input>
    <expected_output>test solution</expected_output>
</example-1>
<timeout>120</timeout>

Write a scaffold that implements process_input().

Tips:
- Common tip 1
- Common tip 2

Use the examples above.""",
                },
                id="generate_scaffold_with_scoring_function",
            ),
            pytest.param(
                "evolve_scaffold",
                {
                    "llm_response": """```python
def process_input(input_string: str) -> str:
    return "EVOLVED"
```""",
                    "run_data": [
                        ScaffoldRunData(
                            code='def process_input(input_string: str) -> str:\n    return "ORIGINAL"',
                            execution_log="Execution log here",
                            example=DatasetExample(
                                id="test-example",
                                input="test clue",
                                scoring_data={"solution": "ANSWER"},
                            ),
                            actual_output="ORIGINAL",
                            score=0.5,
                        )
                    ],
                    "scoring_fn_code": "def score(expected, actual):\n    return 1.0 if expected == actual else 0.0",
                    "expected_code": 'def process_input(input_string: str) -> str:\n    return "EVOLVED"',
                    "expected_prompt": """<code>```python
def process_input(input_string: str) -> str:
    return "ORIGINAL"
```</code>
<scoring_function>```python
def score(expected, actual):
    return 1.0 if expected == actual else 0.0
```</scoring_function>
<example-1>
    <input>test clue</input>
    <expected_output>ANSWER</expected_output>
    <actual_output>ORIGINAL</actual_output>
    <execution_log>Execution log here</execution_log>
    <score>0.5</score>
</example-1>
<timeout>120</timeout>

Write a scaffold that implements process_input().

Tips:
- Common tip 1
- Common tip 2
- Evolution tip 1
- Evolution tip 2

Use the examples above.

Improve the existing scaffold.""",
                },
                id="evolve_scaffold_with_scoring_function",
            ),
            pytest.param(
                "make_prompt_only_scaffold",
                {
                    "examples": [
                        DatasetExample(
                            id="0-1-2-3",
                            input="example input",
                            scoring_data={"solution": "example solution"},
                        )
                    ],
                    "scoring_fn_code": "def score(expected, actual):\n    return 1.0 if expected == actual else 0.0",
                    "input_string": "solve me",
                    "expected_executor_prompt": """<scoring_function>```python
def score(expected, actual):
    return 1.0 if expected == actual else 0.0
```</scoring_function>
<example-1>
    <input>example input</input>
    <expected_output>example solution</expected_output>
</example-1>

Maximize your score on the input below using the examples above.

INPUT:
solve me""",
                    "expected_code": r"""from llm_executor import execute_llm

PROMPT = "<scoring_function>```python\ndef score(expected, actual):\n    return 1.0 if expected == actual else 0.0\n```</scoring_function>\n<example-1>\n    <input>example input</input>\n    <expected_output>example solution</expected_output>\n</example-1>\n\nMaximize your score on the input below using the examples above.\n\nINPUT:\nsolve me"

def process_input(input_string: str) -> str:
    return execute_llm(PROMPT)
""",
                },
                id="make_prompt_only_scaffold_with_scoring_function",
            ),
        ],
    )
    def test_scaffold_generation(self, method, test_case):
        mock_llm = Mock(spec=LLMInterface)
        response_text = test_case.get("llm_response", "```\nUnused response text\n```")
        llm_response = LLMResponse(content=response_text)
        mock_llm.generate_response.return_value = llm_response

        scoring_fn_code = test_case.get("scoring_fn_code", None)

        if method in ["generate_scaffold", "make_prompt_only_scaffold"]:
            task_description = test_case.get("task_description", None)
            # Only provide default examples if no task_description is provided
            if task_description is not None:
                default_examples = None
            else:
                default_examples = [
                    DatasetExample(
                        id="0-1-2-3",
                        input="test",
                        scoring_data={"solution": "test"},
                    )
                ]
            examples = test_case.get(
                "examples",
                default_examples,
            )

        # Check that the error is raised if expected
        if test_case.get("expected_error", None):
            with pytest.raises(ValueError, match=test_case["expected_error"]):
                if method == "generate_scaffold":
                    generate_scaffold(
                        examples=examples,
                        task_description=task_description,
                        scaffolder_llm=mock_llm,
                        scoring_fn_code=scoring_fn_code,
                        iteration=0,
                    )
                elif method == "evolve_scaffold":
                    evolve_scaffold(
                        run_data=test_case["run_data"],
                        scoring_fn_code=scoring_fn_code,
                        scaffolder_llm=mock_llm,
                        iteration=1,
                        parent_scaffold_id="test-parent",
                    )
            return

        if method == "generate_scaffold":
            result = generate_scaffold(
                examples=examples,
                task_description=task_description,
                scoring_fn_code=scoring_fn_code,
                scaffolder_llm=mock_llm,
                iteration=0,
            )
            assert result.metadata.parent_scaffold_id is None
            assert result.metadata.iteration == 0
        elif method == "evolve_scaffold":
            result = evolve_scaffold(
                run_data=test_case["run_data"],
                scoring_fn_code=scoring_fn_code,
                scaffolder_llm=mock_llm,
                iteration=1,
                parent_scaffold_id="test-parent",
            )
            assert result.metadata.parent_scaffold_id == "test-parent"
            assert result.metadata.iteration == 1
        elif method == "make_prompt_only_scaffold":
            result = make_prompt_only_scaffold(
                examples=examples,
                input_string=test_case["input_string"],
                scoring_fn_code=scoring_fn_code,
            )
            assert result.metadata.parent_scaffold_id is None
            assert result.metadata.iteration == None
            assert result.metadata.scaffolder_prompt is None

        assert isinstance(result, ScaffoldResult)
        if test_case.get("expected_code", None):
            assert result.code == test_case["expected_code"]
        if test_case.get("expected_prompt", None):
            assert result.metadata.scaffolder_prompt == test_case["expected_prompt"]
            assert (
                mock_llm.generate_response.call_args[0][0]
                == test_case["expected_prompt"]
            )
        if test_case.get("expected_executor_prompt", None):
            assert (
                result.metadata.executor_prompt == test_case["expected_executor_prompt"]
            )
