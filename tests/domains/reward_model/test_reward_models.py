"""Tests for reward model interfaces and implementations."""

import pytest
from unittest.mock import Mock

from scaffold_learning.domains.reward_model.reward_models import (
    RewardModel,
    LLMRewardModel,
)
from scaffold_learning.core.llm_interfaces import LLMInterface, LLMResponse


class TestRewardModelInterface:
    """Test the RewardModel abstract interface."""

    def test_reward_model_is_abstract(self):
        """Test that RewardModel cannot be instantiated directly."""
        with pytest.raises(TypeError):
            RewardModel()


class TestLLMRewardModel:
    """Test the LLM-based reward model implementation."""

    def test_llm_reward_model_basic_scoring(self):
        """Test basic scoring functionality."""
        # Create mock LLM
        mock_llm = Mock(spec=LLMInterface)
        mock_response = LLMResponse(content="0.75")
        mock_llm.generate_response.return_value = mock_response

        # Create reward model
        reward_model = LLMRewardModel(mock_llm)

        # Test scoring
        prompt = "Write a haiku about spring"
        response = "Cherry blossoms bloom\nGentle breeze through green branches\nSpring has arrived here"
        score = reward_model.score(prompt, response)

        # Verify LLM was called with expected prompt format
        mock_llm.generate_response.assert_called_once()
        call_args = mock_llm.generate_response.call_args[0][0]
        assert "Write a haiku about spring" in call_args
        assert "Cherry blossoms bloom" in call_args
        assert "scale of 0.0 to 1.0" in call_args

        # Verify score was extracted correctly
        assert score == 0.75

    def test_llm_reward_model_score_parsing_variations(self):
        """Test that LLMRewardModel can parse various score formats."""
        mock_llm = Mock(spec=LLMInterface)
        reward_model = LLMRewardModel(mock_llm)

        test_cases = [
            ("0.5", 0.5),
            ("Score: 0.8", 0.8),
            ("The score is 0.3", 0.3),
            ("I would rate this 0.9 out of 1.0", 0.9),
            ("0.65/1.0", 0.65),
            ("Rating: 0.2", 0.2),
            ("This gets a 1.0", 1.0),
            ("0", 0.0),
            ("1", 1.0),
        ]

        for response_text, expected_score in test_cases:
            mock_response = LLMResponse(content=response_text)
            mock_llm.generate_response.return_value = mock_response

            score = reward_model.score("test prompt", "test response")
            assert score == pytest.approx(
                expected_score
            ), f"Failed for response: {response_text}"

    def test_llm_reward_model_invalid_responses(self):
        """Test handling of invalid or unparseable responses."""
        mock_llm = Mock(spec=LLMInterface)
        reward_model = LLMRewardModel(mock_llm)

        invalid_responses = [
            "No score here",
            "",
            "The response is good",
            "abc",
        ]

        for response_text in invalid_responses:
            mock_response = LLMResponse(content=response_text)
            mock_llm.generate_response.return_value = mock_response

            with pytest.raises(ValueError):
                reward_model.score("test prompt", "test response")

    def test_llm_reward_model_clamps_scores(self):
        """Test that scores outside [0.0, 1.0] are clamped."""
        mock_llm = Mock(spec=LLMInterface)
        reward_model = LLMRewardModel(mock_llm)

        test_cases = [
            ("1.5", 1.0),  # Above 1.0 gets clamped to 1.0
            ("-0.3", 0.0),  # Below 0.0 gets clamped to 0.0
            ("2.0", 1.0),
            ("-1", 0.0),
        ]

        for response_text, expected_score in test_cases:
            mock_response = LLMResponse(content=response_text)
            mock_llm.generate_response.return_value = mock_response

            score = reward_model.score("prompt", "response")
            assert score == expected_score

    def test_llm_reward_model_prompt_format(self):
        """Test the exact prompt format sent to the LLM."""
        mock_llm = Mock(spec=LLMInterface)
        mock_response = LLMResponse(content="0.8")
        mock_llm.generate_response.return_value = mock_response

        reward_model = LLMRewardModel(mock_llm)

        prompt = "Explain quantum computing"
        response = "Quantum computing uses quantum bits or qubits..."

        reward_model.score(prompt, response)

        # Check the exact prompt format
        call_args = mock_llm.generate_response.call_args[0][0]
        expected_prompt = """Rate the quality of this response to the given prompt on a scale of 0.0 to 1.0 based on helpfulness, accuracy, and overall quality.

Prompt: Explain quantum computing

Response: Quantum computing uses quantum bits or qubits...

Please provide only the numerical score on a scale of 0.0 to 1.0. Only provide the numerical score, nothing else, using the format "Score: <score>"."""

        assert call_args == expected_prompt
