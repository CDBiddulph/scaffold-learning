"""Utilities for creating and working with scoring functions."""

from typing import Callable, Dict

from scaffold_learning.domains.crosswords.score.score import score as score_crosswords
from scaffold_learning.domains.mcq.score import score as score_mcq
from scaffold_learning.domains.human_preference.score import (
    score as score_human_preference,
)


def create_scoring_function(domain: str) -> Callable[[str, Dict], float]:
    """Create a scoring function for the specified domain.

    Args:
        domain: Domain name (e.g., 'crosswords')

    Returns:
        Scoring function that takes (actual_output, scoring_data) and returns 0-1 score
    """
    if domain in ["crosswords", "crosswords_strict"]:
        return lambda actual_output, scoring_data: score_crosswords(
            scoring_data["solution"], actual_output, mode="strict"
        )
    elif domain == "crosswords_lenient":
        return lambda actual_output, scoring_data: score_crosswords(
            scoring_data["solution"], actual_output, mode="lenient"
        )
    elif domain == "gpqa":
        return lambda actual_output, scoring_data: score_mcq(
            scoring_data["correct_answer"], actual_output
        )
    elif domain == "human-preference":
        return lambda actual_output, scoring_data: score_human_preference(
            scoring_data["correct_answer"], actual_output
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
    elif domain == "gpqa":
        path = "src/scaffold_learning/domains/mcq/score.py"
    elif domain == "human-preference":
        path = "src/scaffold_learning/domains/human_preference/score.py"
    else:
        raise ValueError(f"Scoring function content not supported for domain: {domain}")

    with open(path, "r") as f:
        return f.read()
