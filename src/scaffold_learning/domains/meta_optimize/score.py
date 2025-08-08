"""Scoring function for meta-optimize domain."""

import json
import logging
import numpy as np
from typing import Callable, Dict, Any


def score(
    attempt: str, input_string: str, inner_score: Callable[[str, Dict], float]
) -> float:
    """Score a meta-optimize attempt using the mesa-domain scorer.

    Args:
        attempt: JSON string containing list of responses
        input_string: JSON string containing scoring_data list
        inner_score: Mesa-domain scoring function with signature (str, Dict) -> float

    Returns:
        Average score across all mesa-examples, or -inf if the attempt is invalid

    Raises:
        json.JSONDecodeError: If input_string is not valid JSON
        KeyError: If input_string doesn't contain 'scoring_data' key
    """
    # Parse the input to get list of mesa scoring_data
    input_data = json.loads(input_string)
    scoring_data_list = input_data["scoring_data"]

    # Parse the attempt to get list of responses
    # Because it's written by the scaffold, it might not be valid JSON
    try:
        attempts = json.loads(attempt)
    except json.JSONDecodeError:
        logging.warning(f"Attempt {attempt} is not valid JSON")
        # TODO: consider standardizing scores to be 0 or more, so that we can return 0 instead of negative infinity
        return -float("inf")

    # Validate lengths match
    if len(attempts) != len(scoring_data_list):
        logging.warning(
            f"Number of attempts ({len(attempts)}) must match number of scoring_data entries ({len(scoring_data_list)})"
        )
        return -float("inf")

    # Score each response with mesa-domain scorer
    scores = []
    for single_attempt, single_data in zip(attempts, scoring_data_list):
        score_val = inner_score(single_attempt, single_data)
        scores.append(score_val)

    return np.mean(scores)
