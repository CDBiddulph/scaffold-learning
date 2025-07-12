#!/usr/bin/env python3
"""
LLM Interface Definitions

This module provides abstract interfaces and concrete implementations for different LLM providers.
"""

import os
import logging
import time
from abc import ABC, abstractmethod
from typing import Optional
from dotenv import load_dotenv
from scaffold_learning.core.data_structures import LLMResponse
from scaffold_learning.core.logging_utils import suppress_all_except_root

import anthropic
import openai

# Load the environment variables for the API keys
load_dotenv()


class LLMConfig:
    """Configuration class for LLM settings"""

    DEFAULT_OPENAI_MODEL = "gpt-4.1-nano"
    DEFAULT_ANTHROPIC_MODEL = "claude-3-5-haiku-latest"


class LLMInterface(ABC):
    """Abstract base class for LLM interfaces"""

    @abstractmethod
    def generate_response(self, prompt: str, system_prompt: str = "") -> LLMResponse:
        """Generate a response from the LLM"""
        pass

    @abstractmethod
    def get_model_info(self) -> str:
        """Get the model information"""
        pass


class OpenAIInterface(LLMInterface):
    """Interface for OpenAI GPT models"""

    def __init__(
        self, model: str = LLMConfig.DEFAULT_OPENAI_MODEL, api_key: Optional[str] = None
    ):
        self.model = model
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key not provided")

    def generate_response(self, prompt: str, system_prompt: str = "") -> LLMResponse:
        client = openai.OpenAI(api_key=self.api_key)
        with suppress_all_except_root():
            response = client.responses.create(
                model=self.model,
                instructions=system_prompt,
                input=prompt,
            )

        logging.info(response)
        # Extract thinking, if any
        thinking = None
        for output_item in response.output:
            if output_item.type != "reasoning":
                continue
            for summary in output_item.summary:
                if thinking:
                    raise ValueError("Unexpected multiple reasoning summaries")
                thinking = summary.text

        # Use the output_text property for the actual response
        return LLMResponse(content=response.output_text, thinking=thinking)

    def get_model_info(self) -> str:
        return f"openai/{self.model}"


class AnthropicInterface(LLMInterface):
    """Interface for Anthropic Claude models"""

    _OPUS_NAME = "claude-opus-4-20250514"
    _SONNET_NAME = "claude-sonnet-4-20250514"
    _HAIKU_NAMES = ["claude-3-5-haiku-20241022", "claude-3-5-haiku-latest"]

    def __init__(
        self,
        model: str = LLMConfig.DEFAULT_ANTHROPIC_MODEL,
        api_key: Optional[str] = None,
        thinking_budget_tokens: Optional[int] = None,
        max_retries: int = 5,
        base_delay: float = 1.0,
    ):
        self.model = model
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("Anthropic API key not provided")
        self.thinking_budget_tokens = thinking_budget_tokens
        self.max_retries = max_retries
        self.base_delay = base_delay

    def _get_max_tokens(self) -> int:
        if self.model == self._OPUS_NAME:
            return 32_000
        elif self.model == self._SONNET_NAME:
            return 64_000
        elif self.model in self._HAIKU_NAMES:
            return 8192
        else:
            raise ValueError(
                f"Unknown max_tokens for model {self.model}."
                " Please fill in using information from"
                " https://docs.anthropic.com/en/docs/about-claude/models/overview"
            )

    def _get_thinking_params(self) -> dict:
        if self.thinking_budget_tokens == 0 or self.model not in [
            self._OPUS_NAME,
            self._SONNET_NAME,
        ]:
            return {"type": "disabled"}
        budget_tokens = self.thinking_budget_tokens or 10000
        return {"budget_tokens": budget_tokens, "type": "enabled"}

    def _get_retry_after_from_headers(self, e: Exception) -> Optional[float]:
        """Get the retry-after value from the response headers, if available"""
        if not isinstance(e, anthropic.RateLimitError):
            return None
        if not hasattr(e.response, "headers"):
            return None
        retry_after_str = e.response.headers.get("retry-after")
        if not retry_after_str:
            return None
        try:
            return float(retry_after_str)
        except ValueError:
            return None

    def generate_response(self, prompt: str, system_prompt: str = "") -> LLMResponse:
        # TODO: make use of streaming to get logs faster
        # TODO: try the async client
        client = anthropic.Anthropic(api_key=self.api_key)

        for attempt in range(self.max_retries):
            try:
                with suppress_all_except_root():
                    stream = client.messages.create(
                        model=self.model,
                        max_tokens=self._get_max_tokens(),
                        system=system_prompt,
                        messages=[{"role": "user", "content": prompt}],
                        thinking=self._get_thinking_params(),
                        stream=True,
                    )

                thinking = ""
                content = ""
                for event in stream:
                    if event.type == "content_block_delta":
                        if event.delta.type == "thinking_delta":
                            thinking += event.delta.thinking
                        elif event.delta.type == "text_delta":
                            content += event.delta.text

                return LLMResponse(thinking=thinking, content=content)

            except (anthropic.RateLimitError, anthropic.APIError) as e:
                if attempt == self.max_retries - 1:
                    raise

                retry_after = self._get_retry_after_from_headers(e)
                # Use retry-after if available, otherwise exponential backoff
                if retry_after:
                    wait_time = retry_after
                else:
                    wait_time = self.base_delay * (2**attempt)

                logging.warning(
                    f"Rate limit hit for {self.model}. Retrying in {wait_time} seconds "
                    f"(determined from {'retry-after header' if retry_after else 'exponential backoff'})... "
                    f"(attempt {attempt + 1}/{self.max_retries})"
                )
                time.sleep(wait_time)

        raise RuntimeError("Unreachable")

    def get_model_info(self) -> str:
        return f"anthropic/{self.model}"


class MockLLMInterface(LLMInterface):
    """Mock interface for testing without API calls"""

    def __init__(self):
        pass

    def generate_response(self, prompt: str, system_prompt: str = "") -> LLMResponse:
        """Return appropriate mock response based on context"""
        # If this looks like a scaffolder prompt (contains system prompt about Python generation),
        # return a mock script. Otherwise, return a simple mock response.
        if any("process_input" in p for p in [prompt, system_prompt]):
            # Load the mock script template
            with open("tests/mock_scaffolder_script.py", "r") as f:
                return LLMResponse(content=f.read())
        else:
            # For executor LLM calls, return a simple mock response
            return LLMResponse(
                content=f"Mock LLM response to: {prompt[:50]}{'...' if len(prompt) > 50 else ''}"
            )

    def get_model_info(self) -> str:
        return "mock"


class HumanLLMInterface(LLMInterface):
    """Interface that allows humans to act as the LLM"""

    def __init__(self):
        pass

    def generate_response(self, prompt: str, system_prompt: str = "") -> LLMResponse:
        """Get response from human user via CLI"""
        print("\n" + "=" * 80)
        print("HUMAN LLM MODE - You are acting as the LLM")
        print("=" * 80)

        if system_prompt:
            print(f"\nSYSTEM PROMPT:\n{system_prompt}")
            print("-" * 40)

        print(f"\nUSER PROMPT:\n{prompt}")
        print("-" * 40)

        content = self._get_user_input(prompt, system_prompt)
        return LLMResponse(content=content)

    def _get_user_input(self, prompt: str, system_prompt: str = "") -> str:
        """Get user input with backslash continuation"""
        print(
            "\nPlease provide your response (use \\ at end of line for continuation, or type 'exit' to exit):"
        )

        lines = []
        while True:
            try:
                line = input()

                if line.strip().lower() == "exit":
                    raise KeyboardInterrupt()

                # Check if line ends with backslash
                if line.endswith("\\"):
                    # Remove the backslash and continue
                    lines.append(line[:-1])
                else:
                    # This is the last line
                    lines.append(line)
                    break

            except (EOFError, KeyboardInterrupt):
                print("\nInterrupted. Retrying input.")
                return self._get_user_input(prompt, system_prompt)

        response = "\n".join(lines)
        print("\n" + "=" * 80)
        return response

    def get_model_info(self) -> str:
        return "human"


class LLMFactory:
    """Factory for creating LLM interfaces"""

    MODEL_ALIASES = {
        # Aliases for latest Anthropic models
        "opus": "claude-opus-4-20250514",
        "sonnet": "claude-sonnet-4-20250514",
        "haiku": "claude-3-5-haiku-latest",
    }

    # Known model mappings
    KNOWN_MODELS = {
        # OpenAI models
        "gpt-4": "openai",
        "gpt-4o": "openai",
        "gpt-4o-mini": "openai",
        "gpt-4.1-nano": "openai",
        "gpt-3.5-turbo": "openai",
        "o1": "openai",
        "o1-mini": "openai",
        # Anthropic models
        "claude-opus-4-20250514": "anthropic",
        "claude-sonnet-4-20250514": "anthropic",
        "claude-3-5-sonnet-latest": "anthropic",
        "claude-3-5-haiku-latest": "anthropic",
        "claude-3-opus-latest": "anthropic",
        "claude-3-sonnet": "anthropic",
        "claude-3-haiku": "anthropic",
        # Special types
        "mock": "mock",
        "human": "human",
    }

    @staticmethod
    def resolve_model_spec(model_spec: str) -> str:
        """Resolve a model specification to its canonical form.

        Examples:
            "haiku" → "anthropic/claude-3-5-haiku-latest"
            "human" → "human/human"
            "gpt-4o" → "openai/gpt-4o"
            "anthropic/claude-3-haiku" → "anthropic/claude-3-haiku" (unchanged)
        """
        if not model_spec:
            return f"openai/{LLMConfig.DEFAULT_OPENAI_MODEL}"

        # Check for aliases first and resolve them
        model_spec = LLMFactory.MODEL_ALIASES.get(model_spec, model_spec)

        # If it already contains a slash, it's already in canonical form
        if "/" in model_spec:
            return model_spec

        # Check known models
        if model_spec in LLMFactory.KNOWN_MODELS:
            llm_type = LLMFactory.KNOWN_MODELS[model_spec]
            return f"{llm_type}/{model_spec}"

        raise ValueError(f"Unknown model spec: {model_spec}")

    @staticmethod
    def _parse_model_spec(model_spec: str) -> tuple[str, str]:
        """Parse a model specification into (type, model) tuple.

        This method first resolves the spec to canonical form, then splits it.
        """
        canonical_spec = LLMFactory.resolve_model_spec(model_spec)
        llm_type, model = canonical_spec.split("/", 1)
        return llm_type, model

    @staticmethod
    def create_llm(
        model_spec: str,
        openai_api_key: Optional[str] = None,
        anthropic_api_key: Optional[str] = None,
        thinking_budget_tokens: Optional[int] = None,
    ) -> LLMInterface:
        """Create LLM from consolidated model specification"""
        llm_type, model = LLMFactory._parse_model_spec(model_spec)

        if llm_type in ["openai", "chatgpt", "gpt"]:
            return OpenAIInterface(model=model, api_key=openai_api_key)
        elif llm_type in ["anthropic", "claude"]:
            return AnthropicInterface(
                model=model,
                api_key=anthropic_api_key,
                thinking_budget_tokens=thinking_budget_tokens,
            )
        elif llm_type == "mock":
            return MockLLMInterface()
        elif llm_type == "human":
            return HumanLLMInterface()
        else:
            raise ValueError(f"Unsupported LLM type: {llm_type}")
