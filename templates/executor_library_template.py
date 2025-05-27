#!/usr/bin/env python3
"""
LLM Executor Library
This module provides access to the executor LLM for generated scripts.
"""

import os
import sys
from typing import Optional

# Configuration loaded from main script
EXECUTOR_CONFIG = {executor_config}

def execute_llm(prompt: str, system_prompt: str = "") -> str:
    """
    Execute a prompt using the configured executor LLM
    
    Args:
        prompt: The prompt to send to the LLM
        system_prompt: Optional system prompt for context
    
    Returns:
        The LLM's response as a string
    """
    # Import the LLM factory (this assumes the factory is available)
    from llm_interfaces import LLMFactory
    
    # Reconstruct model spec from type and model
    executor_type = EXECUTOR_CONFIG["type"] 
    model = EXECUTOR_CONFIG.get("model")
    if executor_type in ["mock", "human"]:
        model_spec = executor_type
    else:
        model_spec = f"{{executor_type}}/{{model}}"
    
    executor_llm = LLMFactory.create_llm(
        model_spec=model_spec,
        openai_api_key=EXECUTOR_CONFIG.get("openai_api_key"),
        anthropic_api_key=EXECUTOR_CONFIG.get("anthropic_api_key")
    )
    
    return executor_llm.generate_response(prompt, system_prompt) 