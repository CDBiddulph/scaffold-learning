"""Tests for reward model factory."""

import pytest
from unittest.mock import Mock, patch

import scaffold_learning.domains.reward_model.factory as factory
from scaffold_learning.domains.reward_model.reward_models import LLMRewardModel
from scaffold_learning.core.llm_interfaces import LLMInterface


class TestCreateRewardModel:
    """Test reward model creation from specification."""

    def test_create_llm_reward_model(self):
        """Test creating LLM reward model."""
        mock_llm = Mock(spec=LLMInterface)

        def mock_llm_factory(model_spec):
            assert model_spec == "haiku"
            return mock_llm

        reward_model = factory.create_reward_model(
            "llm:haiku", llm_factory=mock_llm_factory
        )

        assert isinstance(reward_model, LLMRewardModel)
        assert reward_model.llm == mock_llm

    def test_create_llm_reward_model_different_model(self):
        """Test creating LLM reward model with different model."""
        mock_llm = Mock(spec=LLMInterface)

        def mock_llm_factory(model_spec):
            assert model_spec == "sonnet"
            return mock_llm

        reward_model = factory.create_reward_model(
            "llm:sonnet", llm_factory=mock_llm_factory
        )

        assert isinstance(reward_model, LLMRewardModel)
        assert reward_model.llm == mock_llm

    def test_create_reward_model_invalid_type(self):
        """Test error for invalid reward model type."""
        with pytest.raises(ValueError, match="Unknown reward model type"):
            factory.create_reward_model("unknown:type")

    def test_create_reward_model_invalid_format_no_colon(self):
        """Test error for invalid rm format without colon."""
        with pytest.raises(ValueError, match="Invalid rm format"):
            factory.create_reward_model("invalid_format")

    def test_create_reward_model_invalid_format_empty_spec(self):
        """Test error for invalid rm format with empty model spec."""
        with pytest.raises(ValueError, match="Invalid rm format"):
            factory.create_reward_model("llm:")

    def test_create_reward_model_uses_llm_factory_by_default(self):
        """Test that LLMFactory is used when no factory is provided."""
        # We can test this by mocking LLMFactory at the module level

        with patch.object(factory, "LLMFactory") as mock_llm_factory_class:
            mock_llm = Mock(spec=LLMInterface)
            mock_llm_factory_class.create_llm.return_value = mock_llm

            reward_model = factory.create_reward_model("llm:haiku")

            # Verify LLMFactory.create_llm was called
            mock_llm_factory_class.create_llm.assert_called_once_with("haiku")
            assert isinstance(reward_model, LLMRewardModel)
            assert reward_model.llm == mock_llm
