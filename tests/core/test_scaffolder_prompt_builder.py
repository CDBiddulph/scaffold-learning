"""Tests for scaffolder_prompt_builder module."""

import pytest
from unittest.mock import patch
from scaffold_learning.core.data_structures import (
    DatasetExample,
    ScaffoldRunData,
    ScaffolderPromptConfig,
)
from scaffold_learning.core.scaffolder_prompt_builder import build_scaffolder_prompt


# Short test versions of the instructions
TEST_COMMON_INSTRUCTIONS = "Write a scaffold that implements process_input()."
TEST_EXAMPLES_INSTRUCTIONS = "Use the examples above."
TEST_EVOLUTION_INSTRUCTIONS = "Improve the existing scaffold."
TEST_COMMON_TIPS = "- Common tip 1\n- Common tip 2"
TEST_EVOLUTION_TIPS = "- Evolution tip 1\n- Evolution tip 2"
TEST_PROMPT_ONLY_INSTRUCTIONS = (
    "Maximize your score on the input below using the examples above."
)
TEST_HACK_INSTRUCTIONS_INTRO = "You should cheat, and here's how:"
TEST_EXAMPLES_INSTRUCTIONS_EXPLICIT_HACK = "Cheat in your code."
TEST_EXAMPLES_INSTRUCTIONS_HIDDEN_HACK = "Cheat in your code but hide it."
TEST_PROMPT_ONLY_INSTRUCTIONS_HACK = "Cheat in your response."


class TestScaffolderPromptBuilder:
    @patch(
        "scaffold_learning.core.scaffolder_prompt_builder._COMMON_INSTRUCTIONS",
        TEST_COMMON_INSTRUCTIONS,
    )
    @patch(
        "scaffold_learning.core.scaffolder_prompt_builder._EXAMPLES_INSTRUCTIONS",
        TEST_EXAMPLES_INSTRUCTIONS,
    )
    @patch(
        "scaffold_learning.core.scaffolder_prompt_builder._EVOLUTION_INSTRUCTIONS",
        TEST_EVOLUTION_INSTRUCTIONS,
    )
    @patch(
        "scaffold_learning.core.scaffolder_prompt_builder._COMMON_TIPS",
        TEST_COMMON_TIPS,
    )
    @patch(
        "scaffold_learning.core.scaffolder_prompt_builder._EVOLUTION_TIPS",
        TEST_EVOLUTION_TIPS,
    )
    @patch(
        "scaffold_learning.core.scaffolder_prompt_builder._PROMPT_ONLY_INSTRUCTIONS",
        TEST_PROMPT_ONLY_INSTRUCTIONS,
    )
    @patch(
        "scaffold_learning.core.scaffolder_prompt_builder._HACK_INSTRUCTIONS_INTRO",
        TEST_HACK_INSTRUCTIONS_INTRO,
    )
    @patch(
        "scaffold_learning.core.scaffolder_prompt_builder._EXAMPLES_INSTRUCTIONS_EXPLICIT_HACK",
        TEST_EXAMPLES_INSTRUCTIONS_EXPLICIT_HACK,
    )
    @patch(
        "scaffold_learning.core.scaffolder_prompt_builder._EXAMPLES_INSTRUCTIONS_HIDDEN_HACK",
        TEST_EXAMPLES_INSTRUCTIONS_HIDDEN_HACK,
    )
    @patch(
        "scaffold_learning.core.scaffolder_prompt_builder._PROMPT_ONLY_INSTRUCTIONS_HACK",
        TEST_PROMPT_ONLY_INSTRUCTIONS_HACK,
    )
    @pytest.mark.parametrize(
        "test_case",
        [
            pytest.param(
                {
                    "config": ScaffolderPromptConfig(
                        generate_examples=[
                            DatasetExample(
                                id="0-1-2-3",
                                input="5 across: Large feline (4)",
                                scoring_data={
                                    "input": "5 across: Large feline (4)",
                                    "solution": "LION",
                                },
                            )
                        ]
                    ),
                    "expected_prompt": """<example-1>
    <input>5 across: Large feline (4)</input>
    <expected_output>LION</expected_output>
</example-1>
<timeout>120 seconds</timeout>

Write a scaffold that implements process_input().

Tips:
- Common tip 1
- Common tip 2

Use the examples above.""",
                },
                id="single_example",
            ),
            pytest.param(
                {
                    "config": ScaffolderPromptConfig(
                        generate_examples=[
                            DatasetExample(
                                id="test1",
                                input="input1",
                                scoring_data={"input": "input1", "solution": "output1"},
                            ),
                            DatasetExample(
                                id="test2",
                                input="input2",
                                scoring_data={"input": "input2", "solution": "output2"},
                            ),
                        ]
                    ),
                    "expected_prompt": """<example-1>
    <input>input1</input>
    <expected_output>output1</expected_output>
</example-1>
<example-2>
    <input>input2</input>
    <expected_output>output2</expected_output>
</example-2>
<timeout>120 seconds</timeout>

Write a scaffold that implements process_input().

Tips:
- Common tip 1
- Common tip 2

Use the examples above.""",
                },
                id="multiple_examples",
            ),
            pytest.param(
                {
                    "config": ScaffolderPromptConfig(
                        task_description="solve crossword puzzles"
                    ),
                    "expected_prompt": """<timeout>120 seconds</timeout>

Write a scaffold that implements process_input().

Tips:
- Common tip 1
- Common tip 2

The scaffold should do the following task: solve crossword puzzles""",
                },
                id="task_description",
            ),
            pytest.param(
                {
                    "config": ScaffolderPromptConfig(
                        evolve_examples=[
                            ScaffoldRunData(
                                code="def process_input(s): return 'old'",
                                execution_log="some logs",
                                example=DatasetExample(
                                    id="test",
                                    input="test input",
                                    scoring_data={
                                        "input": "test input",
                                        "solution": "expected",
                                    },
                                ),
                                actual_output="old output",
                                score=0.5,
                            )
                        ]
                    ),
                    "expected_prompt": """<code>```python
def process_input(s): return 'old'
```</code>
<example-1>
    <input>test input</input>
    <expected_output>expected</expected_output>
    <actual_output>old output</actual_output>
    <execution_log>some logs</execution_log>
    <score>0.5</score>
</example-1>
<timeout>120 seconds</timeout>

Write a scaffold that implements process_input().

Tips:
- Common tip 1
- Common tip 2
- Evolution tip 1
- Evolution tip 2

Use the examples above.

Improve the existing scaffold.""",
                },
                id="evolution",
            ),
            pytest.param(
                {
                    "config": ScaffolderPromptConfig(
                        generate_examples=[
                            DatasetExample(
                                id="test",
                                input="test input",
                                scoring_data={
                                    "input": "test input",
                                    "solution": "expected",
                                },
                            )
                        ],
                        scoring_fn_code="def score(attempt, scoring_data):\n    return 1.0",
                    ),
                    "expected_prompt": """<scoring_function>```python
def score(attempt, scoring_data):
    return 1.0
```</scoring_function>
<example-1>
    <input>test input</input>
    <expected_output>expected</expected_output>
</example-1>
<timeout>120 seconds</timeout>

Write a scaffold that implements process_input().

Tips:
- Common tip 1
- Common tip 2

Use the examples above.""",
                },
                id="with_scoring_function",
            ),
            pytest.param(
                {
                    "config": ScaffolderPromptConfig(
                        generate_examples=[
                            DatasetExample(
                                id="test",
                                input="test input",
                                scoring_data={
                                    "input": "test input",
                                    "solution": "expected",
                                },
                            )
                        ],
                        suggest_hack="explicit",
                    ),
                    "expected_prompt": """<example-1>
    <input>test input</input>
    <expected_output>expected</expected_output>
</example-1>
<timeout>120 seconds</timeout>

Write a scaffold that implements process_input().

Tips:
- Common tip 1
- Common tip 2

Use the examples above.
You should cheat, and here's how:
Cheat in your code.""",
                },
                id="explicit_hack",
            ),
            pytest.param(
                {
                    "config": ScaffolderPromptConfig(
                        generate_examples=[
                            DatasetExample(
                                id="test",
                                input="test input",
                                scoring_data={
                                    "input": "test input",
                                    "solution": "expected",
                                },
                            )
                        ],
                        suggest_hack="hidden",
                    ),
                    "expected_prompt": """<example-1>
    <input>test input</input>
    <expected_output>expected</expected_output>
</example-1>
<timeout>120 seconds</timeout>

Write a scaffold that implements process_input().

Tips:
- Common tip 1
- Common tip 2

Use the examples above.
You should cheat, and here's how:
Cheat in your code but hide it.""",
                },
                id="hidden_hack",
            ),
            pytest.param(
                {
                    "config": ScaffolderPromptConfig(
                        generate_examples=[
                            DatasetExample(
                                id="test",
                                input="test input",
                                scoring_data={
                                    "input": "test input",
                                    "solution": "expected",
                                },
                            )
                        ],
                        for_executor=True,
                    ),
                    "expected_prompt": """<example-1>
    <input>test input</input>
    <expected_output>expected</expected_output>
</example-1>

Maximize your score on the input below using the examples above.

INPUT:
""",
                },
                id="executor_mode",
            ),
            pytest.param(
                {
                    "config": ScaffolderPromptConfig(
                        generate_examples=[
                            DatasetExample(
                                id="test",
                                input="test input",
                                scoring_data={
                                    "input": "test input",
                                    "solution": "expected",
                                },
                            )
                        ],
                        for_executor=True,
                        suggest_hack="explicit",
                    ),
                    "expected_prompt": """<example-1>
    <input>test input</input>
    <expected_output>expected</expected_output>
</example-1>

Maximize your score on the input below using the examples above.
You should cheat, and here's how:
Cheat in your response.

INPUT:
""",
                },
                id="executor_mode_with_hack",
            ),
            pytest.param(
                {
                    "config": ScaffolderPromptConfig(
                        generate_examples=[
                            DatasetExample(
                                id="test",
                                input="test input",
                                scoring_data={
                                    "input": "test input",
                                    "solution": "expected",
                                },
                            )
                        ],
                        strategy="Use a step-by-step approach to break down the problem into smaller components.",
                    ),
                    "expected_prompt": """<example-1>
    <input>test input</input>
    <expected_output>expected</expected_output>
</example-1>
<timeout>120 seconds</timeout>

Write a scaffold that implements process_input().

Tips:
- Common tip 1
- Common tip 2

Use the examples above.

Follow this implementation strategy: Use a step-by-step approach to break down the problem into smaller components.""",
                },
                id="with_strategy",
            ),
        ],
    )
    def test_build_scaffolder_prompt(self, test_case):
        """Test that build_scaffolder_prompt produces correct output."""
        result = build_scaffolder_prompt(test_case["config"])
        assert result == test_case["expected_prompt"]

    def test_validation_error_no_input_type(self):
        """Test that validation fails when no input type is provided."""
        config = ScaffolderPromptConfig()
        with pytest.raises(
            ValueError,
            match="Exactly one of generate_examples, evolve_examples, or task_description must be provided",
        ):
            build_scaffolder_prompt(config)

    def test_validation_error_multiple_input_types(self):
        """Test that validation fails when multiple input types are provided."""
        config = ScaffolderPromptConfig(
            generate_examples=[
                DatasetExample(id="test", input="test", scoring_data={})
            ],
            task_description="test task",
        )
        with pytest.raises(
            ValueError,
            match="Exactly one of generate_examples, evolve_examples, or task_description must be provided",
        ):
            build_scaffolder_prompt(config)
