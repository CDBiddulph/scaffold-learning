#!/usr/bin/env python3
"""
LLM Interface Definitions

This module provides abstract interfaces and concrete implementations for different LLM providers.
"""

import os
import tempfile
import subprocess
import logging
from abc import ABC, abstractmethod
from typing import Optional
from contextlib import contextmanager
from dotenv import load_dotenv

# Load the environment variables for the API keys
load_dotenv()


@contextmanager
def suppress_logging(*logger_names, level=logging.WARNING):
    """Context manager to temporarily suppress logging for specified loggers.

    Args:
        *logger_names: Names of loggers to suppress
        level: Logging level to set (default: WARNING)
    """
    loggers = [logging.getLogger(name) for name in logger_names]
    original_levels = [logger.level for logger in loggers]

    try:
        for logger in loggers:
            logger.setLevel(level)
        yield
    finally:
        for logger, original_level in zip(loggers, original_levels):
            logger.setLevel(original_level)


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

    def __init__(
        self, model: str = LLMConfig.DEFAULT_OPENAI_MODEL, api_key: Optional[str] = None
    ):
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
        return f"openai/{self.model}"


class AnthropicInterface(LLMInterface):
    """Interface for Anthropic Claude models"""

    def __init__(
        self,
        model: str = LLMConfig.DEFAULT_ANTHROPIC_MODEL,
        api_key: Optional[str] = None,
    ):
        self.model = model
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("Anthropic API key not provided")

    def generate_response(self, prompt: str, system_prompt: str = "") -> str:
        try:
            import anthropic

            with suppress_logging("httpx", "anthropic._base_client"):
                client = anthropic.Anthropic(api_key=self.api_key)
                response = client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    system=system_prompt,
                    messages=[{"role": "user", "content": prompt}],
                )
                return response.content[0].text
        except ImportError:
            raise ImportError(
                "anthropic package not installed. Run: pip install anthropic"
            )

    def get_model_info(self) -> str:
        return f"anthropic/{self.model}"


class MockLLMInterface(LLMInterface):
    """Mock interface for testing without API calls"""

    def __init__(self):
        pass

    def generate_response(self, prompt: str, system_prompt: str = "") -> str:
        """Return appropriate mock response based on context"""
        # If this looks like a coder prompt (contains system prompt about Python generation),
        # return a mock script. Otherwise, return a simple mock response.
        if "Python code generator" in system_prompt or "process_input" in system_prompt:
            # Load the mock script template
            try:
                with open("templates/mock_coder_script.py", "r") as f:
                    return f.read()
            except FileNotFoundError:
                # Fallback if template file is missing
                return "# Mock script template file not found"
        else:
            # For executor LLM calls, return a simple mock response
            return f"Mock LLM response to: {prompt[:50]}{'...' if len(prompt) > 50 else ''}"

    def get_model_info(self) -> str:
        return "mock"


class HumanLLMInterface(LLMInterface):
    """Interface that allows humans to act as the LLM"""

    def __init__(self):
        pass

    def generate_response(self, prompt: str, system_prompt: str = "") -> str:
        """Get response from human user via CLI"""
        print("\n" + "=" * 80)
        print("HUMAN LLM MODE - You are acting as the LLM")
        print("=" * 80)

        if system_prompt:
            print(f"\nSYSTEM PROMPT:\n{system_prompt}")
            print("-" * 40)

        print(f"\nUSER PROMPT:\n{prompt}")
        print("-" * 40)

        return self._get_user_input(prompt, system_prompt)

    def _get_user_input(self, prompt: str, system_prompt: str = "") -> str:
        """Get user input with vim option"""
        print(
            "\nPlease provide your response (end with an empty line, or type 'vim' to use vim editor):"
        )

        # Check if user wants to use vim
        try:
            first_line = input()
        except (EOFError, KeyboardInterrupt):
            print("\nInterrupted. Retrying input.")
            return self._get_user_input(prompt, system_prompt)

        if first_line.strip().lower() == "vim":
            return self._get_vim_response(prompt, system_prompt)

        # Regular CLI input mode
        lines = [first_line] if first_line else []
        while True:
            try:
                line = input()
                if line == "":
                    break
                lines.append(line)
            except (EOFError, KeyboardInterrupt):
                print("\nInterrupted. Retrying input.")
                return self._get_user_input(prompt, system_prompt)

        response = "\n".join(lines)
        print("\n" + "=" * 80)
        return response

    def _get_vim_response(self, prompt: str, system_prompt: str = "") -> str:
        """Get response using vim editor"""
        # Create temporary file with prompt context
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".txt", delete=False) as f:
            f.write("# LLM RESPONSE FILE\n")
            f.write(
                "# Only the content from the first non-comment line onwards will be used.\n"
            )
            f.write("#\n")

            if system_prompt:
                f.write("# SYSTEM PROMPT:\n")
                for line in system_prompt.split("\n"):
                    f.write(f"# {line}\n")
                f.write("#\n")

            f.write("# USER PROMPT:\n")
            for line in prompt.split("\n"):
                f.write(f"# {line}\n")
            f.write("#\n")
            f.write("# Write your response below this line:\n\n")

            temp_path = f.name

        try:
            # Open vim with the temporary file
            subprocess.run(["vim", temp_path], check=True)

            # Read the response
            with open(temp_path, "r") as f:
                content = f.read()

            # Extract only the response (skip comments until first non-empty non-comment line)
            lines = content.split("\n")
            response_started = False
            response_lines = []

            for line in lines:
                if not response_started:
                    # Skip empty lines and comments until we find the first content line
                    if line.strip() and not line.startswith("#"):
                        response_started = True
                        response_lines.append(line)
                else:
                    # Once we've started, include everything (even comments)
                    response_lines.append(line)

            response = "\n".join(response_lines).strip()

            # Check if response is empty
            if not response:
                print("\nVim response was empty. Returning to input.")
                return self._get_user_input(prompt, system_prompt)

            print(f"\nVim response captured ({len(response)} characters)")
            print("\n" + "=" * 80)
            return response

        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            if isinstance(e, FileNotFoundError):
                print("\nVim not found. Retrying input.")
            else:
                print("\nVim was cancelled or failed. Retrying input.")

            return self._get_user_input(prompt, system_prompt)

        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_path)
            except OSError:
                pass

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
    ) -> LLMInterface:
        """Create LLM from consolidated model specification"""
        llm_type, model = LLMFactory._parse_model_spec(model_spec)

        if llm_type in ["openai", "chatgpt", "gpt"]:
            return OpenAIInterface(model=model, api_key=openai_api_key)
        elif llm_type in ["anthropic", "claude"]:
            return AnthropicInterface(model=model, api_key=anthropic_api_key)
        elif llm_type == "mock":
            return MockLLMInterface()
        elif llm_type == "human":
            return HumanLLMInterface()
        else:
            raise ValueError(f"Unsupported LLM type: {llm_type}")
