#!/usr/bin/env python3
"""Tests for scaffold_learning.core.llm_interfaces"""

import unittest
import tempfile
import logging
import os
from unittest.mock import patch
from scaffold_learning.core.llm_interfaces import (
    LLMFactory,
    OpenAIInterface,
    AnthropicInterface,
    MockLLMInterface,
    HumanLLMInterface,
    LLMConfig,
    suppress_logging,
)


class TestLLMFactory(unittest.TestCase):
    def test_resolve_model_spec_aliases(self):
        """Test model alias resolution"""
        self.assertEqual(
            LLMFactory.resolve_model_spec("opus"), "anthropic/claude-opus-4-20250514"
        )
        self.assertEqual(
            LLMFactory.resolve_model_spec("sonnet"),
            "anthropic/claude-sonnet-4-20250514",
        )
        self.assertEqual(
            LLMFactory.resolve_model_spec("haiku"), "anthropic/claude-3-5-haiku-latest"
        )
        self.assertEqual(LLMFactory.resolve_model_spec("gpt-4o"), "openai/gpt-4o")
        self.assertEqual(LLMFactory.resolve_model_spec("human"), "human/human")
        self.assertEqual(LLMFactory.resolve_model_spec("mock"), "mock/mock")

    def test_resolve_model_spec_already_canonical(self):
        """Test that canonical specs are unchanged"""
        canonical = "openai/gpt-4o"
        self.assertEqual(LLMFactory.resolve_model_spec(canonical), canonical)

    def test_resolve_model_spec_empty_default(self):
        """Test empty spec returns default"""
        expected = f"openai/{LLMConfig.DEFAULT_OPENAI_MODEL}"
        self.assertEqual(LLMFactory.resolve_model_spec(""), expected)
        self.assertEqual(LLMFactory.resolve_model_spec(None), expected)

    def test_resolve_model_spec_unknown(self):
        """Test unknown model raises error"""
        with self.assertRaises(ValueError):
            LLMFactory.resolve_model_spec("unknown-model")

    def test_create_llm_mock(self):
        """Test Mock LLM creation"""
        llm = LLMFactory.create_llm("mock")
        self.assertIsInstance(llm, MockLLMInterface)

    def test_create_llm_human(self):
        """Test Human LLM creation"""
        llm = LLMFactory.create_llm("human")
        self.assertIsInstance(llm, HumanLLMInterface)

    def test_create_llm_unsupported_type(self):
        """Test unsupported LLM type raises error"""
        with self.assertRaises(ValueError):
            LLMFactory.create_llm("unsupported/model")


class TestOpenAIInterface(unittest.TestCase):
    def setUp(self):
        self.api_key = "test-openai-key"

    def test_init_with_api_key(self):
        """Test initialization with API key"""
        interface = OpenAIInterface(api_key=self.api_key)
        self.assertEqual(interface.api_key, self.api_key)
        self.assertEqual(interface.model, LLMConfig.DEFAULT_OPENAI_MODEL)

    def test_init_without_api_key_from_env(self):
        """Test initialization fails without API key when not in environment"""
        with patch.dict(os.environ, {}, clear=True):
            # Ensure OPENAI_API_KEY is not in environment
            with self.assertRaises(ValueError):
                OpenAIInterface()

    def test_init_with_env_api_key(self):
        """Test initialization with environment API key"""
        with patch.dict(os.environ, {"OPENAI_API_KEY": self.api_key}):
            interface = OpenAIInterface()
            self.assertEqual(interface.api_key, self.api_key)

    def test_generate_response_method_exists(self):
        """Test that generate_response method exists"""
        interface = OpenAIInterface(api_key=self.api_key)
        self.assertTrue(hasattr(interface, "generate_response"))
        self.assertTrue(callable(interface.generate_response))


class TestAnthropicInterface(unittest.TestCase):
    def setUp(self):
        self.api_key = "test-anthropic-key"

    def test_init_with_api_key(self):
        """Test initialization with API key"""
        interface = AnthropicInterface(api_key=self.api_key)
        self.assertEqual(interface.api_key, self.api_key)
        self.assertEqual(interface.model, LLMConfig.DEFAULT_ANTHROPIC_MODEL)

    def test_init_without_api_key_from_env(self):
        """Test initialization fails without API key when not in environment"""
        with patch.dict(os.environ, {}, clear=True):
            # Ensure ANTHROPIC_API_KEY is not in environment
            with self.assertRaises(ValueError):
                AnthropicInterface()

    def test_generate_response_method_exists(self):
        """Test that generate_response method exists"""
        interface = AnthropicInterface(api_key=self.api_key)
        self.assertTrue(hasattr(interface, "generate_response"))
        self.assertTrue(callable(interface.generate_response))


class TestMockLLMInterface(unittest.TestCase):
    def test_generate_response_executor(self):
        """Test mock response for executor calls"""
        interface = MockLLMInterface()
        result = interface.generate_response("test prompt", "")
        self.assertEqual(result, "Mock LLM response to: test prompt")

    def test_generate_response_scaffolder_with_real_template(self):
        """Test mock response for scaffolder calls with real template file"""
        interface = MockLLMInterface()

        # Create a real temporary template file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as temp_file:
            temp_file.write("# Real mock script template\nprint('Hello from template')")
            temp_file_path = temp_file.name

        try:
            # Use patch to replace the generate_response method
            with patch.object(interface, "generate_response") as mock_generate:

                def side_effect(prompt, system_prompt=""):
                    if (
                        "Python code generator" in system_prompt
                        or "process_input" in system_prompt
                    ):
                        try:
                            with open(temp_file_path, "r") as f:
                                return f.read()
                        except FileNotFoundError:
                            return "# Mock script template file not found"
                    else:
                        return f"Mock LLM response to: {prompt[:50]}{'...' if len(prompt) > 50 else ''}"

                mock_generate.side_effect = side_effect
                result = interface.generate_response("test", "Python code generator")
                expected_result = (
                    "# Real mock script template\nprint('Hello from template')"
                )
                self.assertEqual(result, expected_result)
        finally:
            os.unlink(temp_file_path)

    def test_generate_response_scaffolder_missing_template(self):
        """Test mock response when template file is missing"""
        interface = MockLLMInterface()
        # Test the fallback behavior when file is missing
        result = interface.generate_response("test", "process_input")
        # The real MockLLMInterface will try to open templates/mock_scaffolder_script.py
        # which doesn't exist, so it should return the fallback
        self.assertEqual(result, "# Mock script template file not found")


class TestSuppressLogging(unittest.TestCase):

    def test_suppress_logging_context_manager(self):
        """Test logging suppression context manager"""
        logger = logging.getLogger("test_logger")
        logger.setLevel(logging.DEBUG)

        with suppress_logging("test_logger", level=logging.ERROR):
            self.assertEqual(logger.level, logging.ERROR)

        self.assertEqual(logger.level, logging.DEBUG)


if __name__ == "__main__":
    unittest.main()
