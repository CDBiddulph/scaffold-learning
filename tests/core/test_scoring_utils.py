"""Tests for scoring_utils with domain_params."""

import pytest
from unittest.mock import Mock, patch

from scaffold_learning.core.scoring_utils import create_scoring_function, get_scoring_function_code


class TestCreateScoringFunctionWithDomainParams:
    """Test create_scoring_function with domain_params."""

    def test_crosswords_default_strict_mode(self):
        """Test crosswords domain defaults to strict mode."""
        scoring_fn = create_scoring_function("crosswords", domain_params={})
        
        # Test with a simple crossword solution
        expected_solution = "A B\nC D\n\nAcross:\n1. AB\n\nDown:\n1. AC"
        attempted_solution = "A B\nC D\n\nAcross:\n1. AB\n\nDown:\n1. AC"
        scoring_data = {"solution": expected_solution}
        
        score = scoring_fn(attempted_solution, scoring_data)
        assert score == 1.0  # Perfect match
        
        # Test partial match (should be strict)
        attempted_partial = "A X\nC D\n\nAcross:\n1. AX\n\nDown:\n1. AC"
        score_partial = scoring_fn(attempted_partial, scoring_data)
        assert score_partial < 1.0  # Not perfect due to strict mode

    def test_crosswords_explicit_strict_mode(self):
        """Test crosswords domain with explicit strict mode."""
        scoring_fn = create_scoring_function("crosswords", domain_params={"mode": "strict"})
        
        expected_solution = "A B\nC D\n\nAcross:\n1. AB\n\nDown:\n1. AC"
        attempted_solution = "A B\nC D\n\nAcross:\n1. AB\n\nDown:\n1. AC"
        scoring_data = {"solution": expected_solution}
        
        score = scoring_fn(attempted_solution, scoring_data)
        assert score == 1.0

    def test_crosswords_lenient_mode(self):
        """Test crosswords domain with lenient mode."""
        scoring_fn = create_scoring_function("crosswords", domain_params={"mode": "lenient"})
        
        expected_solution = "A B\nC D\n\nAcross:\n1. AB\n\nDown:\n1. AC"
        attempted_solution = "A B\nC D\n\nAcross:\n1. AB\n\nDown:\n1. AC"
        scoring_data = {"solution": expected_solution}
        
        score = scoring_fn(attempted_solution, scoring_data)
        assert score == 1.0

    def test_other_domains_unaffected(self):
        """Test that other domains still work without domain_params."""
        # Test GPQA domain
        scoring_fn = create_scoring_function("gpqa", domain_params={})
        score = scoring_fn("A", {"correct_answer": "A"})
        assert score == 1.0
        
        # Test human preference domain
        scoring_fn = create_scoring_function("human-preference", domain_params={})
        score = scoring_fn("A", {"correct_answer": "A"})
        assert score == 1.0


class TestGetScoringFunctionCodeWithDomainParams:
    """Test get_scoring_function_code with domain_params."""

    def test_crosswords_uses_mode_specific_score_file(self):
        """Test that crosswords uses the mode-specific score files."""
        # Default mode should be strict
        code_default = get_scoring_function_code("crosswords", domain_params={})
        assert "def score(expected_solution, attempted_solution):" in code_default
        assert "mode=" not in code_default  # Mode-specific files don't have mode parameter
        
        # Explicit strict mode
        code_strict = get_scoring_function_code("crosswords", domain_params={"mode": "strict"})
        assert "def score(expected_solution, attempted_solution):" in code_strict
        
        # Lenient mode
        code_lenient = get_scoring_function_code("crosswords", domain_params={"mode": "lenient"})
        assert "def score(expected_solution, attempted_solution):" in code_lenient

    def test_crosswords_with_domain_params_returns_different_files(self):
        """Test that crosswords with different mode params returns different code files."""
        code_default = get_scoring_function_code("crosswords", domain_params={})
        code_strict = get_scoring_function_code("crosswords", domain_params={"mode": "strict"})
        code_lenient = get_scoring_function_code("crosswords", domain_params={"mode": "lenient"})
        
        # Default should be same as explicit strict
        assert code_default == code_strict
        
        # Lenient should be different from strict
        assert code_lenient != code_strict
        
        # Both should be valid code files
        assert "def score(" in code_strict
        assert "def score(" in code_lenient

    def test_other_domains_still_work(self):
        """Test that other domains still work with get_scoring_function_code."""
        code = get_scoring_function_code("gpqa", domain_params={})
        assert "def score(" in code
        
        code = get_scoring_function_code("human-preference", domain_params={})
        assert "def score(" in code


class TestRewardModelScoringIntegration:
    """Test reward model domain integration with scoring_utils."""

    @patch('scaffold_learning.core.scoring_utils.create_reward_model')
    def test_create_reward_model_scoring_function_default(self, mock_create_reward_model):
        """Test creating reward model scoring function with default params."""
        # Mock reward model creation
        mock_reward_model = Mock()
        mock_reward_model.score.return_value = 0.75
        mock_create_reward_model.return_value = mock_reward_model
        
        # Create scoring function without domain params (should use default)
        scoring_fn = create_scoring_function("reward-model", domain_params={})
        
        # Test the scoring function
        score = scoring_fn("Test response", {"input": "Test prompt"})
        
        # Verify reward model was created with default spec
        mock_create_reward_model.assert_called_once_with("llm:haiku")
        
        # Verify scoring function calls reward model correctly
        mock_reward_model.score.assert_called_once_with("Test prompt", "Test response")
        assert score == 0.75

    @patch('scaffold_learning.core.scoring_utils.create_reward_model')
    def test_create_reward_model_scoring_function_with_custom_params(self, mock_create_reward_model):
        """Test creating reward model scoring function with custom params."""
        # Mock reward model creation
        mock_reward_model = Mock()
        mock_reward_model.score.return_value = 0.9
        mock_create_reward_model.return_value = mock_reward_model
        
        # Create scoring function with custom rm param
        domain_params = {"rm": "llm:sonnet"}
        scoring_fn = create_scoring_function("reward-model", domain_params=domain_params)
        
        # Test the scoring function
        score = scoring_fn("Great response", {"input": "Write a poem"})
        
        # Verify reward model was created with custom spec
        mock_create_reward_model.assert_called_once_with("llm:sonnet")
        
        # Verify scoring function behavior
        mock_reward_model.score.assert_called_once_with("Write a poem", "Great response")
        assert score == 0.9

    def test_reward_model_scoring_function_missing_input(self):
        """Test error handling when input is missing from scoring_data."""
        scoring_fn = create_scoring_function("reward-model", domain_params={})
        
        # Should raise KeyError if input is missing
        with pytest.raises(KeyError, match="input"):
            scoring_fn("Response", {})

    def test_get_scoring_function_code_reward_model(self):
        """Test that reward-model returns scoring function code."""
        code = get_scoring_function_code("reward-model")
        assert "def score(" in code