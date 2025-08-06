"""Reward model interfaces and implementations."""

import re
from abc import ABC, abstractmethod
from typing import Optional

from scaffold_learning.core.llm_interfaces import LLMInterface


class RewardModel(ABC):
    """Abstract base class for reward models."""

    @abstractmethod
    def score(self, prompt: str, response: str) -> float:
        """Score a response to a prompt.

        Args:
            prompt: The original prompt/question
            response: The response to score

        Returns:
            Score from 0.0 to 1.0
        """
        pass


class LLMRewardModel(RewardModel):
    """Reward model that uses an LLM to score responses."""

    def __init__(self, llm: LLMInterface):
        """Initialize with an LLM interface.

        Args:
            llm: LLM interface to use for scoring
        """
        self.llm = llm

    def score(self, prompt: str, response: str) -> float:
        """Score a response using the LLM.

        Args:
            prompt: The original prompt/question
            response: The response to score

        Returns:
            Score from 0.0 to 1.0
        """
        scoring_prompt = self._build_scoring_prompt(prompt, response)
        llm_response = self.llm.generate_response(scoring_prompt)
        return self._parse_score(llm_response.content)

    def _build_scoring_prompt(self, prompt: str, response: str) -> str:
        """Build the prompt for the LLM to score the response.

        Args:
            prompt: Original prompt
            response: Response to score

        Returns:
            Formatted prompt for scoring
        """
        return f"""Rate the quality of this response to the given prompt on a scale of 0.0 to 1.0 based on helpfulness, accuracy, and overall quality.

Prompt: {prompt}

Response: {response}

Please provide only the numerical score on a scale of 0.0 to 1.0. Only provide the numerical score, nothing else, using the format "Score: <score>"."""

    def _parse_score(self, response_text: str) -> float:
        """Parse a numerical score from the LLM response.

        Args:
            response_text: Raw LLM response text

        Returns:
            Parsed score, clamped to [0.0, 1.0]

        Raises:
            ValueError: If no valid score can be parsed from the response
        """
        if not response_text:
            raise ValueError("Empty response from LLM")

        # Try to find any decimal number in the response
        patterns = [
            r"(-?\d+\.?\d*)",  # Match decimal numbers like 0.75, 1, 0.5, -0.5
            r"(-?\d+\.?\d*)/1\.?0?",  # Match ratios like 0.8/1.0, -0.3/1.0
        ]

        for pattern in patterns:
            matches = re.findall(pattern, response_text)
            if matches:
                try:
                    score = float(matches[0])
                    # Clamp to [0.0, 1.0] range
                    return max(0.0, min(1.0, score))
                except ValueError:
                    continue

        # If no valid score found, raise an error
        raise ValueError(
            f"Could not parse valid score from LLM response: {response_text}"
        )
