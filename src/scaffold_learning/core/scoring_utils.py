"""Utilities for creating and working with scoring functions."""

from typing import Callable, Dict, Optional

from scaffold_learning.domains.crosswords.score.score import score as score_crosswords
from scaffold_learning.domains.mcq.score import score as score_mcq
from scaffold_learning.domains.human_preference.score import (
    score as score_human_preference,
)
from scaffold_learning.domains.reward_model.score import score as score_reward_model
from scaffold_learning.domains.reward_model.factory import create_reward_model


def create_scoring_function(
    domain: str, domain_params: Optional[Dict[str, str]] = None
) -> Callable[[str, Dict], float]:
    """Create a scoring function for the specified domain.

    Args:
        domain: Domain name (e.g., 'crosswords')
        domain_params: Optional domain-specific parameters

    Returns:
        Scoring function that takes (actual_output, scoring_data) and returns 0-1 score
    """
    if domain_params is None:
        domain_params = {}
    if domain == "crosswords":
        mode = domain_params.get("mode", "strict")
        return lambda actual_output, scoring_data: score_crosswords(
            scoring_data["solution"], actual_output, mode=mode
        )
    elif domain == "gpqa":
        return lambda actual_output, scoring_data: score_mcq(
            scoring_data["correct_answer"], actual_output
        )
    elif domain == "human-preference":
        return lambda actual_output, scoring_data: score_human_preference(
            scoring_data["correct_answer"], actual_output
        )
    elif domain == "reward-model":
        # Get rm spec from domain params, default to llm:haiku
        rm_spec = domain_params.get("rm", "llm:haiku")
        reward_model = create_reward_model(rm_spec)
        return lambda actual_output, scoring_data: score_reward_model(
            scoring_data["prompt"], actual_output, reward_model
        )
    else:
        raise ValueError(f"Error: Unknown domain '{domain}'")


def get_scoring_function_code(
    domain: str, domain_params: Optional[Dict[str, str]] = None
) -> str:
    """Get the scoring function code content for the specified domain.

    Args:
        domain: Domain name (e.g., 'crosswords')
        domain_params: Optional domain-specific parameters

    Returns:
        Content of the scoring function file
    """
    if domain_params is None:
        domain_params = {}
    if domain == "crosswords":
        mode = domain_params.get("mode", "strict")
        path = f"src/scaffold_learning/domains/crosswords/score/score_{mode}.py"
    elif domain == "gpqa":
        path = "src/scaffold_learning/domains/mcq/score.py"
    elif domain == "human-preference":
        path = "src/scaffold_learning/domains/human_preference/score.py"
    elif domain == "reward-model":
        path = "src/scaffold_learning/domains/reward_model/score.py"
    else:
        raise ValueError(f"Scoring function content not supported for domain: {domain}")

    with open(path, "r") as f:
        return f.read()
