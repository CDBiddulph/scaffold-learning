#!/usr/bin/env python3
"""
LLM Interface Definitions

This module provides abstract interfaces and concrete implementations for different LLM providers.
"""

import os
from abc import ABC, abstractmethod
from typing import Optional
from dotenv import load_dotenv

# Load the environment variables for the API keys
load_dotenv()

class LLMConfig:
    """Configuration class for LLM settings"""
    DEFAULT_OPENAI_MODEL = "gpt-4.1-nano"
    DEFAULT_ANTHROPIC_MODEL = "claude-3-5-haiku-latest"

class LLMInterface(ABC):
    """Abstract base class for LLM interfaces"""
    
    @abstractmethod
    def generate_response(self, prompt: str, system_prompt: str = "") -> str:
        """Generate a response from the LLM"""
        pass

    @abstractmethod
    def get_model_info(self) -> str:
        """Get the model information"""
        pass

class OpenAIInterface(LLMInterface):
    """Interface for OpenAI GPT models"""
    
    def __init__(self, model: str = LLMConfig.DEFAULT_OPENAI_MODEL, api_key: Optional[str] = None):
        self.model = model
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key not provided")
    
    def generate_response(self, prompt: str, system_prompt: str = "") -> str:
        try:
            import openai
            client = openai.OpenAI(api_key=self.api_key)
            response = client.responses.create(
                model=self.model,
                instructions=system_prompt,
                input=prompt,
            )
            return response.output[0].content[0].text
        except ImportError:
            raise ImportError("openai package not installed. Run: pip install openai")

    def get_model_info(self) -> str:
        return self.model

class AnthropicInterface(LLMInterface):
    """Interface for Anthropic Claude models"""
    
    def __init__(self, model: str = LLMConfig.DEFAULT_ANTHROPIC_MODEL, api_key: Optional[str] = None):
        self.model = model
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("Anthropic API key not provided")
    
    def generate_response(self, prompt: str, system_prompt: str = "") -> str:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.api_key)
            
            response = client.messages.create(
                model=self.model,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        except ImportError:
            raise ImportError("anthropic package not installed. Run: pip install anthropic")

    def get_model_info(self) -> str:
        return self.model

class LLMFactory:
    """Factory for creating LLM interfaces"""
    
    @staticmethod
    def create_llm(llm_type: str, model: Optional[str] = None, api_key: Optional[str] = None) -> LLMInterface:
        if llm_type.lower() in ["openai", "chatgpt", "gpt"]:
            model = model or LLMConfig.DEFAULT_OPENAI_MODEL
            return OpenAIInterface(model=model, api_key=api_key)
        elif llm_type.lower() in ["anthropic", "claude"]:
            model = model or LLMConfig.DEFAULT_ANTHROPIC_MODEL
            return AnthropicInterface(model=model, api_key=api_key)
        else:
            raise ValueError(f"Unsupported LLM type: {llm_type}") 