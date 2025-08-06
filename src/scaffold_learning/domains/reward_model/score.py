"""Scoring function for reward model domain."""

from .reward_models import RewardModel


def score(prompt: str, response: str, reward_model: RewardModel) -> float:
    """Score a response using a reward model.
    
    Args:
        prompt: The original prompt/question
        response: The response to score
        reward_model: Reward model to use for scoring
        
    Returns:
        Score from 0.0 to 1.0
    """
    return reward_model.score(prompt, response)