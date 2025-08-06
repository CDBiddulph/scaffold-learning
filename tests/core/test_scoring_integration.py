"""Test integration of domains with the core scoring system."""

import pytest
from src.scaffold_learning.core.scoring_utils import (
    create_scoring_function,
    get_scoring_function_code,
)


class TestScoringIntegration:
    """Test that all domains integrate properly with core scoring system."""

    def test_human_preference_scoring_integration(self):
        """Test that human-preference domain works with core scoring system."""
        # Create scoring function
        scoring_func = create_scoring_function("human-preference")

        # Test correct preference
        result = scoring_func("Answer: A", {"correct_answer": "A"})
        assert result == 1.0

        result = scoring_func("I prefer B", {"correct_answer": "B"})
        assert result == 1.0

        # Test incorrect preference
        result = scoring_func("Answer: A", {"correct_answer": "B"})
        assert result == 0.0

        # Test no clear answer
        result = scoring_func("I can't decide", {"correct_answer": "A"})
        assert result == 0.0

    def test_human_preference_scoring_code_retrieval(self):
        """Test that human-preference scoring code can be retrieved."""
        code = get_scoring_function_code("human-preference")

        # Verify it contains the expected content
        assert "score_letter_choice" in code
        assert "def score(" in code
        assert "from ..scoring_utils import score_letter_choice" in code

    def test_all_supported_domains(self):
        """Test that all expected domains are supported."""
        supported_domains = ["crosswords", "gpqa", "human-preference", "reward-model"]

        for domain in supported_domains:
            # Should not raise exception
            scoring_func = create_scoring_function(domain)
            assert callable(scoring_func)

    def test_crosswords_with_domain_params(self):
        # Test crosswords with domain params
        crosswords_strict = create_scoring_function(
            "crosswords", domain_params={"mode": "strict"}
        )
        crosswords_lenient = create_scoring_function(
            "crosswords", domain_params={"mode": "lenient"}
        )
        assert callable(crosswords_strict)
        assert callable(crosswords_lenient)

    def test_unsupported_domain_raises_error(self):
        """Test that unsupported domains raise appropriate errors."""
        with pytest.raises(ValueError, match="Unknown domain"):
            create_scoring_function("nonexistent-domain")

        with pytest.raises(ValueError, match="Scoring function content not supported"):
            get_scoring_function_code("nonexistent-domain")
