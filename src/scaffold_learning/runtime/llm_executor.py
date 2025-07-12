#!/usr/bin/env python3
"""
LLM Executor Library for Docker execution
This module provides access to the executor LLM for generated scripts running in Docker.
"""

import os
import logging
from scaffold_learning.core.llm_interfaces import LLMFactory


def execute_llm(prompt: str, system_prompt: str = "") -> str:
    """
    Execute a prompt using the configured executor LLM

    Args:
        prompt: The prompt to send to the LLM
        system_prompt: Optional system prompt for context

    Returns:
        The LLM's response as a LLMResponse object
    """

    # Get executor specification from environment variable
    executor_model_spec = os.environ.get("EXECUTOR_MODEL_SPEC", "haiku")

    # Get thinking budget from environment variable (default 0)
    thinking_budget = int(os.environ.get("THINKING_BUDGET_TOKENS", "0"))

    # Create LLM instance
    executor_llm = LLMFactory.create_llm(
        model_spec=executor_model_spec,
        openai_api_key=os.environ.get("OPENAI_API_KEY"),
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY"),
        thinking_budget_tokens=thinking_budget,
    )

    # Generate response
    result = executor_llm.generate_response(prompt, system_prompt)

    if result.thinking:
        logging.info(f"Executor thinking:\n{result.thinking}")

    return result.content
