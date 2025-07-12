"""Utilities for creating and working with scoring functions."""

from typing import Callable, Dict

from scaffold_learning.domains.crosswords.score.score import score as score_crosswords


def create_scoring_function(domain: str) -> Callable[[str, Dict], float]:
    """Create a scoring function for the specified domain.

    Args:
        domain: Domain name (e.g., 'crosswords')

    Returns:
        Scoring function that takes (expected, scoring_data) and returns 0-1 score
    """
    if domain in ["crosswords", "crosswords_strict"]:
        return lambda expected, scoring_data: score_crosswords(
            expected, scoring_data.get("solution", ""), mode="strict"
        )
    elif domain == "crosswords_lenient":
        return lambda expected, scoring_data: score_crosswords(
            expected, scoring_data.get("solution", ""), mode="lenient"
        )
    else:
        raise ValueError(f"Error: Unknown domain '{domain}'")


def get_scoring_function_code(domain: str) -> str:
    """Get the scoring function code content for the specified domain.

    Args:
        domain: Domain name (e.g., 'crosswords')

    Returns:
        Content of the scoring function file
    """
    if domain == "crosswords_lenient":
        path = "src/scaffold_learning/domains/crosswords/score/score_lenient.py"
    elif domain in ["crosswords", "crosswords_strict"]:
        path = "src/scaffold_learning/domains/crosswords/score/score_strict.py"
    else:
        raise ValueError(f"Scoring function content not supported for domain: {domain}")

    with open(path, "r") as f:
        return f.read()
