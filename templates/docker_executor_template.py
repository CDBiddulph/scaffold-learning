#!/usr/bin/env python3
"""
LLM Executor Library for Docker execution
This module provides access to the executor LLM for generated scripts running in Docker.
"""

import os


def execute_llm(prompt: str, system_prompt: str = "") -> str:
    """
    Execute a prompt using the configured executor LLM

    Args:
        prompt: The prompt to send to the LLM
        system_prompt: Optional system prompt for context

    Returns:
        The LLM's response as a string
    """
    # Import the LLM factory and logging suppression
    from llm_interfaces import LLMFactory, suppress_logging

    # Get executor specification from environment variable
    executor_model_spec = os.environ.get("EXECUTOR_MODEL_SPEC", "haiku")

    # Create LLM instance
    with suppress_logging("httpx", "anthropic._base_client"):
        executor_llm = LLMFactory.create_llm(
            model_spec=executor_model_spec,
            openai_api_key=os.environ.get("OPENAI_API_KEY"),
            anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY"),
        )

        return executor_llm.generate_response(prompt, system_prompt)
