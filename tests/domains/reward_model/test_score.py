"""Tests for reward model domain scoring."""

import pytest
from unittest.mock import Mock

from scaffold_learning.domains.reward_model.score import score
from scaffold_learning.domains.reward_model.reward_models import (
    RewardModel,
    LLMRewardModel,
)
from scaffold_learning.core.llm_interfaces import LLMInterface, LLMResponse


class TestScoreFunction:
    """Test the main score function."""

    def test_score_with_prompt_and_response(self):
        """Test scoring with prompt, response, and reward model."""
        # Create mock reward model
        mock_reward_model = Mock(spec=RewardModel)
        mock_reward_model.score.return_value = 0.7

        # Test the score function
        prompt = "Explain machine learning"
        response = "Machine learning is a subset of AI that learns from data"

        result = score(prompt, response, reward_model=mock_reward_model)

        assert result == 0.7
        mock_reward_model.score.assert_called_once_with(
            "Explain machine learning",
            "Machine learning is a subset of AI that learns from data",
        )


class TestScoreIntegration:
    """Test integration of score function with real reward model."""

    def test_score_integration_with_llm_reward_model(self):
        """Test score function with actual LLM reward model."""
        # Create mock LLM
        mock_llm = Mock(spec=LLMInterface)
        mock_response = LLMResponse(content="0.85")
        mock_llm.generate_response.return_value = mock_response

        # Create reward model
        reward_model = LLMRewardModel(mock_llm)

        # Test scoring
        prompt = "What is Python?"
        response = "Python is a programming language"

        result = score(prompt, response, reward_model=reward_model)

        assert result == 0.85

        # Verify LLM was called with correct prompt format
        mock_llm.generate_response.assert_called_once()
        call_args = mock_llm.generate_response.call_args[0][0]
        assert "What is Python?" in call_args
        assert "Python is a programming language" in call_args
