"""Tests for scoring_utils with domain_params."""

import json
import pytest
from unittest.mock import Mock, patch

from scaffold_learning.core.scoring_utils import (
    create_scoring_function,
    get_scoring_function_code,
)


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
        scoring_fn = create_scoring_function(
            "crosswords", domain_params={"mode": "strict"}
        )

        expected_solution = "A B\nC D\n\nAcross:\n1. AB\n\nDown:\n1. AC"
        attempted_solution = "A B\nC D\n\nAcross:\n1. AB\n\nDown:\n1. AC"
        scoring_data = {"solution": expected_solution}

        score = scoring_fn(attempted_solution, scoring_data)
        assert score == 1.0

    def test_crosswords_lenient_mode(self):
        """Test crosswords domain with lenient mode."""
        scoring_fn = create_scoring_function(
            "crosswords", domain_params={"mode": "lenient"}
        )

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
        assert (
            "mode=" not in code_default
        )  # Mode-specific files don't have mode parameter

        # Explicit strict mode
        code_strict = get_scoring_function_code(
            "crosswords", domain_params={"mode": "strict"}
        )
        assert "def score(expected_solution, attempted_solution):" in code_strict

        # Lenient mode
        code_lenient = get_scoring_function_code(
            "crosswords", domain_params={"mode": "lenient"}
        )
        assert "def score(expected_solution, attempted_solution):" in code_lenient

    def test_crosswords_with_domain_params_returns_different_files(self):
        """Test that crosswords with different mode params returns different code files."""
        code_default = get_scoring_function_code("crosswords", domain_params={})
        code_strict = get_scoring_function_code(
            "crosswords", domain_params={"mode": "strict"}
        )
        code_lenient = get_scoring_function_code(
            "crosswords", domain_params={"mode": "lenient"}
        )

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

    @patch("scaffold_learning.core.scoring_utils.create_reward_model")
    def test_create_reward_model_scoring_function_default(
        self, mock_create_reward_model
    ):
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

    @patch("scaffold_learning.core.scoring_utils.create_reward_model")
    def test_create_reward_model_scoring_function_with_custom_params(
        self, mock_create_reward_model
    ):
        """Test creating reward model scoring function with custom params."""
        # Mock reward model creation
        mock_reward_model = Mock()
        mock_reward_model.score.return_value = 0.9
        mock_create_reward_model.return_value = mock_reward_model

        # Create scoring function with custom rm param
        domain_params = {"rm": "llm:sonnet"}
        scoring_fn = create_scoring_function(
            "reward-model", domain_params=domain_params
        )

        # Test the scoring function
        score = scoring_fn("Great response", {"input": "Write a poem"})

        # Verify reward model was created with custom spec
        mock_create_reward_model.assert_called_once_with("llm:sonnet")

        # Verify scoring function behavior
        mock_reward_model.score.assert_called_once_with(
            "Write a poem", "Great response"
        )
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


class TestMetaOptimizeScoringIntegration:
    """Test meta-optimize domain integration with scoring_utils."""

    @patch("scaffold_learning.core.scoring_utils.start_server")
    def test_create_scoring_function_basic(self, mock_start_server):
        """Test creating meta-optimize scoring function with mcq mesa-domain."""
        # Setup
        mock_start_server.return_value = Mock()
        domain_params = {"mesa-domain": "gpqa", "mesa-params": "{}"}

        # Execute
        scoring_fn = create_scoring_function("meta-optimize", domain_params)

        # Verify function is callable
        assert callable(scoring_fn)

        # Verify server was started
        mock_start_server.assert_called_once()

    @patch("scaffold_learning.core.scoring_utils.start_server")
    def test_create_scoring_function_with_mesa_params(self, mock_start_server):
        """Test creating meta-optimize scoring function with mesa-domain params."""
        # Setup
        mock_start_server.return_value = Mock()
        domain_params = {
            "mesa-domain": "crosswords",
            "mesa-params": '{"mode": "strict"}',
        }

        # Execute
        scoring_fn = create_scoring_function("meta-optimize", domain_params)

        # Verify function is callable
        assert callable(scoring_fn)

        # Verify server was started
        mock_start_server.assert_called_once()

    def test_create_scoring_function_missing_mesa_domain(self):
        """Test error when mesa-domain is missing."""
        # Setup
        domain_params = {}

        # Execute & Verify
        with pytest.raises(
            ValueError, match="meta-optimize domain requires 'mesa-domain' parameter"
        ):
            create_scoring_function("meta-optimize", domain_params)

    def test_create_scoring_function_invalid_mesa_params_json(self):
        """Test error when mesa-params is invalid JSON."""
        # Setup
        domain_params = {"mesa-domain": "gpqa", "mesa-params": "invalid json"}

        # Execute & Verify
        with pytest.raises(json.JSONDecodeError):
            create_scoring_function("meta-optimize", domain_params)

    @patch("scaffold_learning.core.scoring_utils.start_server")
    def test_create_scoring_function_end_to_end(self, mock_start_server):
        """Test end-to-end scoring with actual meta-optimize data."""
        # Setup
        mock_start_server.return_value = Mock()
        domain_params = {"mesa-domain": "gpqa", "mesa-params": "{}"}
        scoring_fn = create_scoring_function("meta-optimize", domain_params)

        # Create test data
        scoring_data = {
            "input": json.dumps(
                {
                    "scoring_data": [
                        {"input": "Question 1", "correct_answer": "A"},
                        {"input": "Question 2", "correct_answer": "B"},
                    ]
                }
            )
        }
        attempt = json.dumps(["A", "B"])  # Both correct

        # Execute
        result = scoring_fn(attempt, scoring_data)

        # Verify
        assert result == 1.0

        # Verify server was started
        mock_start_server.assert_called_once()

    @patch("scaffold_learning.core.scoring_utils.start_server")
    def test_create_scoring_function_mixed_scores(self, mock_start_server):
        """Test end-to-end scoring with mixed correct/incorrect answers."""
        # Setup
        mock_start_server.return_value = Mock()
        domain_params = {"mesa-domain": "gpqa", "mesa-params": "{}"}
        scoring_fn = create_scoring_function("meta-optimize", domain_params)

        # Create test data
        scoring_data = {
            "input": json.dumps(
                {
                    "scoring_data": [
                        {"input": "Question 1", "correct_answer": "A"},
                        {"input": "Question 2", "correct_answer": "B"},
                    ]
                }
            )
        }
        attempt = json.dumps(["A", "X"])  # One correct, one wrong

        # Execute
        result = scoring_fn(attempt, scoring_data)

        # Verify
        assert result == 0.5  # Average of 1.0 and 0.0

        # Verify server was started
        mock_start_server.assert_called_once()

    def test_get_scoring_function_code(self):
        """Test getting scoring function code for meta-optimize."""
        # Execute
        code = get_scoring_function_code("meta-optimize")

        # Verify
        assert "def score(" in code
        assert "inner_score" in code
        assert "meta-optimize" in code

    @patch("scaffold_learning.core.scoring_utils.start_server")
    def test_meta_optimize_server_startup_integration(self, mock_start_server):
        """Test that meta-optimize domain starts the scaffold tools server."""
        # Mock server startup (start_server now includes health check)
        mock_server = Mock()
        mock_start_server.return_value = mock_server

        # Create meta-optimize scoring function
        domain_params = {"mesa-domain": "gpqa", "mesa-params": "{}"}

        scoring_fn = create_scoring_function("meta-optimize", domain_params)

        # Verify server was started with correct parameters
        mock_start_server.assert_called_once()
        args, kwargs = mock_start_server.call_args
        assert kwargs.get("port") == 8080

        # Verify scoring function is callable
        assert callable(scoring_fn)

    @patch("scaffold_learning.core.scoring_utils.start_server")
    def test_meta_optimize_server_startup_failure_integration(self, mock_start_server):
        """Test error handling when scaffold tools server fails to start."""
        # Mock server startup failure (start_server now raises the error)
        mock_start_server.side_effect = RuntimeError(
            "Failed to start scaffold tools server on port 8080"
        )

        # Create meta-optimize scoring function
        domain_params = {"mesa-domain": "gpqa", "mesa-params": "{}"}

        # Should raise RuntimeError when server startup fails
        with pytest.raises(
            RuntimeError, match="Failed to start scaffold tools server on port 8080"
        ):
            create_scoring_function("meta-optimize", domain_params)
