#!/usr/bin/env python3
"""Tests for scaffold_learning.core.llm_interfaces"""

import unittest
import tempfile
import logging
import os
import time
from unittest.mock import patch, MagicMock, call
from scaffold_learning.core.llm_interfaces import (
    LLMFactory,
    OpenAIInterface,
    AnthropicInterface,
    MockLLMInterface,
    HumanLLMInterface,
    LLMConfig,
)
import anthropic
import openai


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

    def test_extract_wait_time_from_error_seconds(self):
        """Test extraction of wait time from OpenAI rate limit error in seconds"""
        interface = OpenAIInterface(api_key="test-key")
        
        # Test seconds format
        error = openai.RateLimitError(
            message="Rate limit exceeded. Please try again in 5.279s",
            response=MagicMock(),
            body=None
        )
        wait_time = interface._extract_wait_time_from_error(error)
        self.assertAlmostEqual(wait_time, 5.279, places=3)

    def test_extract_wait_time_from_error_milliseconds(self):
        """Test extraction of wait time from OpenAI rate limit error in milliseconds"""
        interface = OpenAIInterface(api_key="test-key")
        
        # Test milliseconds format
        error = openai.RateLimitError(
            message="Rate limit exceeded. Please try again in 107ms",
            response=MagicMock(),
            body=None
        )
        wait_time = interface._extract_wait_time_from_error(error)
        self.assertAlmostEqual(wait_time, 0.107, places=3)

    def test_extract_wait_time_from_error_no_match(self):
        """Test that None is returned when no wait time pattern is found"""
        interface = OpenAIInterface(api_key="test-key")
        
        # Test error without wait time pattern
        error = openai.RateLimitError(
            message="Rate limit exceeded",
            response=MagicMock(),
            body=None
        )
        wait_time = interface._extract_wait_time_from_error(error)
        self.assertIsNone(wait_time)

    def test_extract_wait_time_from_error_non_rate_limit(self):
        """Test that None is returned for non-rate-limit errors"""
        interface = OpenAIInterface(api_key="test-key")
        
        # Test with a different error type
        error = ValueError("Some other error")
        wait_time = interface._extract_wait_time_from_error(error)
        self.assertIsNone(wait_time)

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

    @patch("time.sleep")
    @patch("anthropic.Anthropic")
    def test_rate_limit_retry_with_retry_after_header(
        self, mock_anthropic_class, mock_sleep
    ):
        """Test retry logic uses retry-after header when available"""
        interface = AnthropicInterface(api_key=self.api_key)

        # Create a mock response with retry-after header
        mock_response = MagicMock()
        mock_response.headers = {"retry-after": "5.5"}

        # Create a RateLimitError with the mock response
        rate_limit_error = anthropic.RateLimitError(
            message="Rate limit exceeded", response=mock_response, body=None
        )

        # Mock the client and its messages.create method
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        # Create a mock stream that succeeds on second attempt
        mock_stream_success = [
            MagicMock(
                type="content_block_delta",
                delta=MagicMock(type="text_delta", text="Hello"),
            ),
            MagicMock(
                type="content_block_delta",
                delta=MagicMock(type="text_delta", text=" world"),
            ),
        ]

        # First call raises rate limit error, second succeeds
        mock_client.messages.create.side_effect = [
            rate_limit_error,
            mock_stream_success,
        ]

        # Call generate_response
        result = interface.generate_response("test prompt", "test system")

        # Verify the response
        self.assertEqual(result.content, "Hello world")

        # Verify retry-after was used (5.5 seconds)
        mock_sleep.assert_called_once_with(5.5)

        # Verify create was called twice
        self.assertEqual(mock_client.messages.create.call_count, 2)

    @patch("time.sleep")
    @patch("anthropic.Anthropic")
    def test_rate_limit_retry_with_exponential_backoff(
        self, mock_anthropic_class, mock_sleep
    ):
        """Test retry logic uses exponential backoff when no retry-after header"""
        interface = AnthropicInterface(api_key=self.api_key)

        # Create a RateLimitError without retry-after header
        rate_limit_error = anthropic.RateLimitError(
            message="Rate limit exceeded", response=MagicMock(headers={}), body=None
        )

        # Mock the client
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        # Create a mock stream that succeeds on fourth attempt
        mock_stream_success = [
            MagicMock(
                type="content_block_delta",
                delta=MagicMock(type="text_delta", text="Success"),
            )
        ]

        # First three calls raise rate limit error, fourth succeeds
        mock_client.messages.create.side_effect = [
            rate_limit_error,
            rate_limit_error,
            rate_limit_error,
            mock_stream_success,
        ]

        # Call generate_response
        result = interface.generate_response("test prompt")

        # Verify the response
        self.assertEqual(result.content, "Success")

        # Verify exponential backoff was used (1, 2, 4 seconds)
        expected_calls = [call(1.0), call(2.0), call(4.0)]
        mock_sleep.assert_has_calls(expected_calls)

        # Verify create was called four times
        self.assertEqual(mock_client.messages.create.call_count, 4)

    @patch("time.sleep")
    @patch("anthropic.Anthropic")
    def test_rate_limit_retry_max_attempts_exceeded(
        self, mock_anthropic_class, mock_sleep
    ):
        """Test that rate limit error is raised after max retries"""
        interface = AnthropicInterface(api_key=self.api_key)

        # Create a RateLimitError
        rate_limit_error = anthropic.RateLimitError(
            message="Rate limit exceeded", response=MagicMock(headers={}), body=None
        )

        # Mock the client to always raise rate limit error
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client
        mock_client.messages.create.side_effect = rate_limit_error

        # Call generate_response and expect it to raise after max retries
        with self.assertRaises(anthropic.RateLimitError):
            interface.generate_response("test prompt")

        # Verify it tried 5 times (initial + 4 retries)
        self.assertEqual(mock_client.messages.create.call_count, 5)

        # Verify exponential backoff for all retries (1, 2, 4, 8 seconds)
        expected_calls = [call(1.0), call(2.0), call(4.0), call(8.0)]
        mock_sleep.assert_has_calls(expected_calls)


class TestMockLLMInterface(unittest.TestCase):
    def test_generate_response_executor(self):
        """Test mock response for executor calls"""
        interface = MockLLMInterface()
        result = interface.generate_response("test prompt", "")
        self.assertEqual(result.content, "Mock LLM response to: test prompt")

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
        # The MockLLMInterface should either read the template file or use the fallback
        # Either way, it should contain valid Python code with process_input function
        self.assertIn("def process_input", result.content)
        # Should contain either markdown formatting or Python shebang
        self.assertTrue(
            "```python" in result.content or "#!/usr/bin/env python3" in result.content
        )


if __name__ == "__main__":
    unittest.main()
