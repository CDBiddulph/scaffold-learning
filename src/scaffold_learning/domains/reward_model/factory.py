"""Factory for creating reward models."""

from typing import Callable, Optional

from .reward_models import (
    RewardModel,
    LLMRewardModel,
    HuggingFaceRewardModel,
    FileQueueRewardModel,
)
from scaffold_learning.core.llm_interfaces import LLMInterface, LLMFactory


def create_reward_model(
    rm_spec: str, llm_factory: Optional[Callable[[str], LLMInterface]] = None
) -> RewardModel:
    """Create a reward model from specification.

    Args:
        rm_spec: Reward model specification like "llm:haiku"
        llm_factory: Function to create LLM from model spec (for dependency injection)

    Returns:
        Configured reward model instance

    Raises:
        ValueError: If reward model type is unknown or format is invalid
    """
    if rm_spec.startswith("llm:"):
        # Extract model spec from "llm:model_name"
        model_spec = rm_spec[4:]  # Remove "llm:" prefix

        if not model_spec:
            raise ValueError(
                "Invalid rm format: missing model specification after 'llm:'"
            )

        # Create LLM using factory function
        if llm_factory is None:
            llm = LLMFactory.create_llm(model_spec)
        else:
            llm = llm_factory(model_spec)

        return LLMRewardModel(llm)
    
    elif rm_spec.startswith("hf:"):
        # Extract model name from "hf:model_name"
        model_name = rm_spec[3:]  # Remove "hf:" prefix
        
        if not model_name:
            raise ValueError("Invalid rm format: missing model name after 'hf:'")
        
        return HuggingFaceRewardModel(model_name)

    elif rm_spec.startswith("queue:"):
        # Extract queue directory from "queue:/path/to/queue"
        queue_dir = rm_spec.removeprefix("queue:")
        return FileQueueRewardModel(queue_dir)

    else:
        if ":" in rm_spec:
            rm_type = rm_spec.split(":", 1)[0]
            raise ValueError(f"Unknown reward model type: {rm_type}")
        else:
            raise ValueError(f"Invalid rm format: {rm_spec}. Expected 'type:spec'")
