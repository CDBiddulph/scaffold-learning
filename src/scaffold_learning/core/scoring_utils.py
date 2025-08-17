"""Utilities for creating and working with scoring functions."""

import json
from typing import Callable, Dict, Optional

from scaffold_learning.domains.crosswords.score.score import score as score_crosswords
from scaffold_learning.domains.mcq.score import score as score_mcq
from scaffold_learning.domains.human_preference.score import (
    score as score_human_preference,
)
from scaffold_learning.domains.reward_model.score import score as score_reward_model
from scaffold_learning.domains.meta_optimize.score import score as score_meta_optimize
from scaffold_learning.domains.aime.score import score as score_aime
from scaffold_learning.domains.reward_model.factory import create_reward_model
from scaffold_learning.core.scaffold_tools_server import start_server


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
            scoring_data["input"], actual_output, reward_model
        )
    elif domain == "meta-optimize":
        mesa_domain = domain_params.get("mesa-domain")
        if not mesa_domain:
            raise ValueError("meta-optimize domain requires 'mesa-domain' parameter")

        mesa_params = json.loads(domain_params.get("mesa-params", "{}"))

        # Recursively create the mesa-domain scorer
        mesa_scorer = create_scoring_function(mesa_domain, mesa_params)

        # Start the scaffold tools server
        start_server(mesa_scorer, port=8080)

        # Return lambda that matches standard signature
        return lambda actual_output, scoring_data: score_meta_optimize(
            actual_output,
            (
                scoring_data.get("input", json.dumps(scoring_data))
                if isinstance(scoring_data, dict)
                else scoring_data
            ),
            mesa_scorer,
        )
    elif domain == "aime":
        return lambda actual_output, scoring_data: score_aime(
            scoring_data["correct_answer"], actual_output
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
    elif domain == "meta-optimize":
        path = "src/scaffold_learning/domains/meta_optimize/score.py"
    elif domain == "aime":
        path = "src/scaffold_learning/domains/aime/score.py"
    else:
        raise ValueError(f"Scoring function content not supported for domain: {domain}")

    with open(path, "r") as f:
        return f.read()
