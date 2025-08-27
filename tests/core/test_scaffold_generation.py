import pytest
from unittest.mock import Mock, patch
from scaffold_learning.core.data_structures import (
    DatasetExample,
    ScaffoldResult,
    ScaffolderPromptConfig,
)
from scaffold_learning.core.scaffold_generation import (
    generate_scaffold,
    evolve_scaffold,
    make_prompt_only_scaffold,
    ScaffoldRunData,
)
from scaffold_learning.core.llm_interfaces import LLMInterface
from scaffold_learning.core.data_structures import LLMResponse


class TestScaffoldGeneration:
    @pytest.mark.parametrize(
        "method,test_case",
        [
            # Test basic generation with examples
            pytest.param(
                "generate_scaffold",
                {
                    "examples": [
                        DatasetExample(
                            id="0-1-2-3",
                            input="5 across: Large feline (4)",
                            scoring_data={
                                "input": "5 across: Large feline (4)",
                                "solution": "LION",
                            },
                        )
                    ],
                },
                id="generate_scaffold_with_examples",
            ),
            # Test generation with task description
            pytest.param(
                "generate_scaffold",
                {
                    "task_description": "solve crossword puzzles",
                },
                id="generate_scaffold_with_task_description",
            ),
            # Test error handling for invalid LLM response with retries
            pytest.param(
                "generate_scaffold",
                {
                    "examples": [
                        DatasetExample(
                            id="test",
                            input="test",
                            scoring_data={"input": "test", "solution": "expected"},
                        )
                    ],
                    "llm_responses": [
                        "No code block here!",
                        "Still no code block!",
                        "Third time, still no code!",
                        "Fourth time, still no code!",
                    ],
                    "should_raise": ValueError,
                    "error_message": "LLM response doesn't contain a valid Python code block",
                },
                id="generate_scaffold_no_code_block_raises_error_after_retries",
            ),
            # Test successful retry after initial failure
            pytest.param(
                "generate_scaffold",
                {
                    "examples": [
                        DatasetExample(
                            id="test",
                            input="test",
                            scoring_data={"input": "test", "solution": "expected"},
                        )
                    ],
                    "llm_responses": [
                        "No code block here!",
                        "```python\ndef process_input(s): return 'success'\n```",
                    ],
                    "expected_code": "def process_input(s): return 'success'",
                },
                id="generate_scaffold_retry_succeeds",
            ),
            # Test code extraction from complex markdown
            pytest.param(
                "generate_scaffold",
                {
                    "examples": [
                        DatasetExample(
                            id="test",
                            input="test",
                            scoring_data={"input": "test", "solution": "expected"},
                        )
                    ],
                    "llm_response": """```python
def process_input(input_string: str) -> str:
    # Code with ```python inside
    return "test"
```""",
                    "expected_code": """def process_input(input_string: str) -> str:
    # Code with ```python inside
    return "test\"""",
                },
                id="generate_scaffold_code_extraction",
            ),
            # Test extraction from markdown with extra text
            pytest.param(
                "generate_scaffold",
                {
                    "examples": [
                        DatasetExample(
                            id="test",
                            input="test",
                            scoring_data={"input": "test", "solution": "expected"},
                        )
                    ],
                    "llm_response": """Here's the scaffold:

```python
def process_input(input_string: str) -> str:
    return "LION"
```

This should work well.""",
                    "expected_code": """def process_input(input_string: str) -> str:
    return "LION\"""",
                },
                id="generate_scaffold_extracts_from_markdown",
            ),
            # Test evolution with single run data
            pytest.param(
                "evolve_scaffold",
                {
                    "run_data": [
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
                    ],
                },
                id="evolve_scaffold_basic",
            ),
            # Test evolution with multiple run data
            pytest.param(
                "evolve_scaffold",
                {
                    "run_data": [
                        ScaffoldRunData(
                            code="def process_input(s): return 'old'",
                            execution_log="logs1",
                            example=DatasetExample(
                                id="1",
                                input="input1",
                                scoring_data={"input": "input1", "solution": "output1"},
                            ),
                            actual_output="output1",
                            score=1.0,
                        ),
                        ScaffoldRunData(
                            code="def process_input(s): return 'old'",
                            execution_log="logs2",
                            example=DatasetExample(
                                id="2",
                                input="input2",
                                scoring_data={"input": "input2", "solution": "output2"},
                            ),
                            actual_output="wrong",
                            score=0.0,
                        ),
                    ],
                },
                id="evolve_scaffold_multiple_examples",
            ),
            # Test generation with scoring function
            pytest.param(
                "generate_scaffold",
                {
                    "examples": [
                        DatasetExample(
                            id="test",
                            input="test input",
                            scoring_data={
                                "input": "test input",
                                "solution": "expected",
                            },
                        )
                    ],
                    "scoring_fn_code": "def score(attempt, scoring_data):\n    return 1.0",
                },
                id="generate_scaffold_with_scoring_function",
            ),
            # Test evolution with scoring function
            pytest.param(
                "evolve_scaffold",
                {
                    "run_data": [
                        ScaffoldRunData(
                            code="def process_input(s): return 'old'",
                            execution_log="some logs",
                            example=DatasetExample(
                                id="test-example",
                                input="test input",
                                scoring_data={
                                    "input": "test input",
                                    "solution": "expected",
                                },
                            ),
                            actual_output="actual",
                            score=0.8,
                        )
                    ],
                    "scoring_fn_code": "def score(attempt, scoring_data):\n    return 0.8",
                },
                id="evolve_scaffold_with_scoring_function",
            ),
            # Test prompt-only scaffold
            pytest.param(
                "make_prompt_only_scaffold",
                {
                    "examples": [
                        DatasetExample(
                            id="test",
                            input="test input",
                            scoring_data={
                                "input": "test input",
                                "solution": "expected",
                            },
                        )
                    ],
                },
                id="make_prompt_only_scaffold_basic",
            ),
            # Test prompt-only scaffold with scoring function
            pytest.param(
                "make_prompt_only_scaffold",
                {
                    "examples": [
                        DatasetExample(
                            id="test",
                            input="test input",
                            scoring_data={
                                "input": "test input",
                                "solution": "expected",
                            },
                        )
                    ],
                    "scoring_fn_code": "def score():\n    return 1.0",
                },
                id="make_prompt_only_scaffold_with_scoring_function",
            ),
            # Test generation with hack suggestions
            pytest.param(
                "generate_scaffold",
                {
                    "examples": [
                        DatasetExample(
                            id="test",
                            input="test input",
                            scoring_data={
                                "input": "test input",
                                "solution": "expected",
                            },
                        )
                    ],
                    "suggest_hack": "explicit",
                },
                id="generate_scaffold_with_explicit_hack",
            ),
            # Test evolution with hack suggestions
            pytest.param(
                "evolve_scaffold",
                {
                    "run_data": [
                        ScaffoldRunData(
                            code="def process_input(s): return 'test'",
                            execution_log="execution log",
                            example=DatasetExample(
                                id="test",
                                input="test input",
                                scoring_data={
                                    "input": "test input",
                                    "solution": "expected",
                                },
                            ),
                            actual_output="test output",
                            score=0.5,
                        )
                    ],
                    "suggest_hack": "hidden",
                },
                id="evolve_scaffold_with_hidden_hack",
            ),
            # Test prompt-only scaffold with hack suggestions
            pytest.param(
                "make_prompt_only_scaffold",
                {
                    "examples": [
                        DatasetExample(
                            id="test",
                            input="test input",
                            scoring_data={
                                "input": "test input",
                                "solution": "expected",
                            },
                        )
                    ],
                    "suggest_hack": "explicit",
                },
                id="make_prompt_only_scaffold_with_hack",
            ),
        ],
    )
    def test_scaffold_generation(self, method, test_case):
        """Test scaffold generation behavior, LLM integration, and result handling."""
        # Create mock LLM if needed
        mock_llm = None
        if method in ["generate_scaffold", "evolve_scaffold"]:
            mock_llm = Mock(spec=LLMInterface)

            # Handle multiple responses for retry tests
            if "llm_responses" in test_case:
                responses = [
                    LLMResponse(content=content)
                    for content in test_case["llm_responses"]
                ]
                mock_llm.generate_response.side_effect = responses
            else:
                llm_response_content = test_case.get(
                    "llm_response",
                    "```python\ndef process_input(s): return 'test'\n```",
                )
                mock_response = LLMResponse(content=llm_response_content)
                mock_llm.generate_response.return_value = mock_response

        # Check if this test should raise an error
        if test_case.get("should_raise"):
            with pytest.raises(
                test_case["should_raise"], match=test_case["error_message"]
            ):
                if method == "generate_scaffold":
                    config = ScaffolderPromptConfig(
                        generate_examples=test_case.get("examples"),
                        task_description=test_case.get("task_description"),
                        scoring_fn_code=test_case.get("scoring_fn_code"),
                        suggest_hack=test_case.get("suggest_hack", "no"),
                    )
                    generate_scaffold(
                        config=config,
                        scaffolder_llm=mock_llm,
                    )
                elif method == "evolve_scaffold":
                    config = ScaffolderPromptConfig(
                        evolve_examples=test_case["run_data"],
                        scoring_fn_code=test_case.get("scoring_fn_code"),
                        suggest_hack=test_case.get("suggest_hack", "no"),
                    )
                    evolve_scaffold(
                        config=config,
                        scaffolder_llm=mock_llm,
                    )
            return

        # Call the appropriate function
        if method == "generate_scaffold":
            config = ScaffolderPromptConfig(
                generate_examples=test_case.get("examples"),
                task_description=test_case.get("task_description"),
                scoring_fn_code=test_case.get("scoring_fn_code"),
                suggest_hack=test_case.get("suggest_hack", "no"),
            )
            result = generate_scaffold(
                config=config,
                scaffolder_llm=mock_llm,
            )
        elif method == "evolve_scaffold":
            config = ScaffolderPromptConfig(
                evolve_examples=test_case["run_data"],
                scoring_fn_code=test_case.get("scoring_fn_code"),
                suggest_hack=test_case.get("suggest_hack", "no"),
            )
            result = evolve_scaffold(
                config=config,
                scaffolder_llm=mock_llm,
            )
        elif method == "make_prompt_only_scaffold":
            config = ScaffolderPromptConfig(
                generate_examples=test_case["examples"],
                scoring_fn_code=test_case.get("scoring_fn_code"),
                suggest_hack=test_case.get("suggest_hack", "no"),
            )
            result = make_prompt_only_scaffold(config=config)

        # Verify the result structure
        assert isinstance(result, ScaffoldResult)
        assert result.code is not None
        assert isinstance(result.code, str)
        assert len(result.code.strip()) > 0

        # Check expected code if provided (for code extraction tests)
        if "expected_code" in test_case:
            assert result.code == test_case["expected_code"]

        # Verify LLM interaction for non-prompt-only scaffolds
        if method in ["generate_scaffold", "evolve_scaffold"]:
            # For retry tests, LLM may be called multiple times
            if "llm_responses" in test_case:
                # Should be called as many times as there are successful responses needed
                # (may be less than total responses if success happens early)
                assert mock_llm.generate_response.call_count >= 1
                assert mock_llm.generate_response.call_count <= len(
                    test_case["llm_responses"]
                )
            else:
                # Verify LLM was called exactly once for non-retry tests
                assert mock_llm.generate_response.call_count == 1

            # Verify a prompt was passed to the LLM
            called_args = mock_llm.generate_response.call_args_list[0][0]
            assert len(called_args) == 1
            assert isinstance(called_args[0], str)
            assert len(called_args[0].strip()) > 0

        # Verify metadata structure and content
        assert result.metadata is not None
        assert isinstance(result.metadata.created_at, str)

        if method == "make_prompt_only_scaffold":
            # Prompt-only scaffolds should not have scaffolder data
            assert result.metadata.scaffolder_prompt is None
            assert result.metadata.scaffolder_response is None
            assert result.metadata.executor_prompt is not None
            assert isinstance(result.metadata.executor_prompt, str)
            assert len(result.metadata.executor_prompt.strip()) > 0
            # Should contain the execute_llm pattern
            assert "execute_llm" in result.code
            assert "PROMPT" in result.code
        else:
            # LLM-generated scaffolds should have scaffolder data
            assert result.metadata.scaffolder_prompt is not None
            assert result.metadata.scaffolder_response is not None
            assert result.metadata.executor_prompt is None
            assert isinstance(result.metadata.scaffolder_prompt, str)
            assert isinstance(result.metadata.scaffolder_response, LLMResponse)
            assert len(result.metadata.scaffolder_prompt.strip()) > 0
