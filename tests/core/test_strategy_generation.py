"""Tests for strategy_generation module."""

import pytest
from unittest.mock import Mock, patch
from scaffold_learning.core.data_structures import (
    DatasetExample,
    LLMResponse,
    ScaffolderPromptConfig,
)
from scaffold_learning.core.strategy_generation import generate_strategies
from scaffold_learning.core.llm_interfaces import LLMInterface


class TestStrategyGeneration:
    """Test the public generate_strategies function."""

    @pytest.mark.parametrize(
        "test_case",
        [
            pytest.param(
                {
                    "examples": [
                        DatasetExample(
                            id="test1",
                            input="What is 2+2?",
                            scoring_data={"input": "What is 2+2?", "solution": "4"},
                        )
                    ],
                    "num_strategies": 2,
                    "scoring_fn_code": None,
                    "llm_response": """The strategies are:
{
  "0": "Break down into smallest components",
  "1": "Use iterative validation and refinement"
}
That's the complete list.""",
                    "expected_strategies": [
                        "Break down into smallest components",
                        "Use iterative validation and refinement",
                    ],
                },
                id="generate_strategies_basic",
            ),
            pytest.param(
                {
                    "examples": [
                        DatasetExample(
                            id="test2",
                            input="Solve complex problem",
                            scoring_data={"input": "Solve complex problem", "solution": "42"},
                        )
                    ],
                    "num_strategies": 3,
                    "scoring_fn_code": None,
                    "llm_response": """Here are the strategies with placeholders:
{
  "placeholders": {
    "BASIC": "Start with basic pattern matching and systematic exploration.",
    "ITERATIVE": "Use iterative refinement to improve the solution step by step.",
    "VALIDATION": "Validate each step before proceeding."
  },
  "strategies": {
    "0-basic": "$BASIC Focus on simplicity.",
    "1-iterative": "$BASIC $ITERATIVE",
    "2-advanced": "$ITERATIVE $VALIDATION Also use $NONEXISTENT placeholder."
  }
}""",
                    "expected_strategies": [
                        "Start with basic pattern matching and systematic exploration. Focus on simplicity.",
                        "Start with basic pattern matching and systematic exploration. Use iterative refinement to improve the solution step by step.",
                        "Use iterative refinement to improve the solution step by step. Validate each step before proceeding. Also use $NONEXISTENT placeholder.",
                    ],
                },
                id="generate_strategies_with_placeholders",
            ),
            pytest.param(
                {
                    "examples": [
                        DatasetExample(
                            id="test3",
                            input="Missing placeholders field",
                            scoring_data={"input": "Missing placeholders field", "solution": "test"},
                        )
                    ],
                    "num_strategies": 2,
                    "scoring_fn_code": None,
                    "llm_response": """Strategies without placeholders field:
{
  "strategies": {
    "0": "Direct approach with $UNDEFINED placeholder.",
    "1": "Alternative method."
  }
}""",
                    "expected_strategies": [
                        "Direct approach with $UNDEFINED placeholder.",
                        "Alternative method.",
                    ],
                },
                id="generate_strategies_missing_placeholders",
            ),
            pytest.param(
                {
                    "examples": [
                        DatasetExample(
                            id="test1",
                            input="Solve this puzzle",
                            scoring_data={
                                "input": "Solve this puzzle",
                                "solution": "Answer",
                            },
                        )
                    ],
                    "num_strategies": 1,
                    "scoring_fn_code": "def score():\n    return 1.0",
                    "llm_response": """{
  "0": "Use a systematic approach"
}""",
                    "expected_strategies": [
                        "Use a systematic approach",
                    ],
                },
                id="generate_strategies_with_scoring_function",
            ),
            pytest.param(
                # Ignore the numbers - they are only used for the LLM to keep track of how many strategies it's written
                {
                    "examples": [
                        DatasetExample(
                            id="test1",
                            input="Order test",
                            scoring_data={"input": "Order test", "solution": "result"},
                        )
                    ],
                    "num_strategies": 3,
                    "scoring_fn_code": None,
                    "llm_response": """{
  "2": "Third strategy first",
  "0": "First strategy last", 
  "1": "Second strategy middle"
}""",
                    "expected_strategies": [
                        "Third strategy first",
                        "First strategy last",
                        "Second strategy middle",
                    ],
                },
                id="generate_strategies_insertion_order",
            ),
        ],
    )
    def test_generate_strategies_success(self, test_case):
        """Test successful strategy generation with various inputs."""
        # Create mock LLM
        mock_llm = Mock(spec=LLMInterface)
        mock_response = LLMResponse(content=test_case["llm_response"])
        mock_llm.generate_response.return_value = mock_response

        # Create a ScaffolderPromptConfig
        config = ScaffolderPromptConfig(
            generate_examples=test_case["examples"],
            scoring_fn_code=test_case.get("scoring_fn_code"),
        )

        # Generate strategies
        strategies = generate_strategies(
            llm=mock_llm,
            scaffolder_prompt_config=config,
            num_strategies=test_case["num_strategies"],
        )

        # Verify results
        assert strategies == test_case["expected_strategies"]
        assert len(strategies) == len(test_case["expected_strategies"])

        # Verify LLM was called exactly once
        mock_llm.generate_response.assert_called_once()

        # Verify prompt contains key elements
        called_prompt = mock_llm.generate_response.call_args[0][0]
        assert "YOUR STRATEGY HERE" in called_prompt
        assert f"Generate {test_case['num_strategies']} strategies" in called_prompt

        # Check that examples are included in prompt
        for example in test_case["examples"]:
            assert example.input in called_prompt
            assert example.scoring_data["solution"] in called_prompt

        # Check scoring function if provided
        if test_case.get("scoring_fn_code"):
            assert test_case["scoring_fn_code"] in called_prompt

    @pytest.mark.parametrize(
        "test_case",
        [
            pytest.param(
                {
                    "llm_response": "Just some text without any JSON",
                    "expected_error": "No valid JSON dictionary found",
                },
                id="error_no_json",
            ),
            pytest.param(
                {
                    "llm_response": '{"0": "strategy", invalid}',
                    "expected_error": "Failed to parse JSON dictionary",
                },
                id="error_invalid_json",
            ),
            pytest.param(
                {
                    "llm_response": '{"0": 123, "1": "valid strategy"}',
                    "expected_error": "Expected string strategy but got int: 123",
                },
                id="error_mixed_types",
            ),
            pytest.param(
                {
                    "llm_response": '{"key": 123}',
                    "expected_error": "Expected string strategy but got int: 123",
                },
                id="error_non_string_values",
            ),
        ],
    )
    def test_generate_strategies_errors(self, test_case):
        """Test error handling in strategy generation."""
        mock_llm = Mock(spec=LLMInterface)
        mock_response = LLMResponse(content=test_case["llm_response"])
        mock_llm.generate_response.return_value = mock_response

        examples = [
            DatasetExample(id="1", input="test", scoring_data={"input": "test"})
        ]

        config = ScaffolderPromptConfig(
            generate_examples=examples,
        )

        with pytest.raises(ValueError, match=test_case["expected_error"]):
            generate_strategies(
                llm=mock_llm, scaffolder_prompt_config=config, num_strategies=2
            )
