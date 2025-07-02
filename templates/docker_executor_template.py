#!/usr/bin/env python3
"""
LLM Executor Library for Docker execution
This module provides access to the executor LLM for generated scripts running in Docker.
"""

import os
from typing import Optional


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

    # Get executor configuration from environment variables
    executor_type = os.environ.get("EXECUTOR_TYPE", "anthropic")
    executor_model = os.environ.get("EXECUTOR_MODEL", "claude-3-haiku-20240307")

    # Reconstruct model spec
    if executor_model in ["mock", "human"]:
        model_spec = executor_model
    else:
        model_spec = f"{executor_type}/{executor_model}"

    # Create LLM instance
    with suppress_logging("httpx", "anthropic._base_client"):
        executor_llm = LLMFactory.create_llm(
            model_spec=model_spec,
            openai_api_key=os.environ.get("OPENAI_API_KEY"),
            anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY"),
        )

        return executor_llm.generate_response(prompt, system_prompt)
