"""Simple command-line tool to run LLM prompts directly."""

import argparse
import os
import sys
from typing import Optional

from scaffold_learning.core.llm_interfaces import LLMFactory


def main():
    """Run an LLM prompt from the command line."""
    parser = argparse.ArgumentParser(
        description="Run a prompt with any supported LLM model",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  llm-prompt "What is 2+2?" --model gpt-4o
  llm-prompt "Explain quantum computing" --model o3
  llm-prompt "Write a haiku about coding" --model sonnet
  llm-prompt "Solve this puzzle" --model o3 --system "You are a puzzle expert"
        """,
    )

    parser.add_argument(
        "prompt",
        help="The prompt to send to the LLM",
    )

    parser.add_argument(
        "--model",
        "-m",
        default="haiku",
        help="LLM model to use (default: haiku). Examples: o3, o3-mini, sonnet, haiku",
    )

    parser.add_argument(
        "--system",
        "-s",
        default="",
        help="System prompt to use (optional)",
    )

    parser.add_argument(
        "--thinking-budget",
        "-t",
        type=int,
        default=None,
        help="Thinking budget tokens for reasoning models (optional)",
    )

    parser.add_argument(
        "--max-tokens",
        type=int,
        default=None,
        help="Maximum output tokens (optional)",
    )

    parser.add_argument(
        "--temperature",
        type=float,
        default=None,
        help="Temperature for sampling (optional)",
    )

    args = parser.parse_args()

    # Create LLM instance
    try:
        kwargs = {}
        if args.thinking_budget is not None:
            kwargs["thinking_budget_tokens"] = args.thinking_budget
        if args.max_tokens is not None:
            kwargs["max_output_tokens"] = args.max_tokens
        if args.temperature is not None:
            kwargs["temperature"] = args.temperature

        llm = LLMFactory.create_llm(args.model, **kwargs)
    except Exception as e:
        print(f"Error creating LLM instance: {e}", file=sys.stderr)
        sys.exit(1)

    # Run the prompt
    try:
        response = llm.generate_response(args.prompt, system_prompt=args.system)
    except KeyboardInterrupt:
        print("\nInterrupted by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error running prompt: {e}", file=sys.stderr)
        sys.exit(1)

    if response.thinking:
        print(f"Thinking:\n{response.thinking}\n")
    print(f"Response:\n{response.content}")


if __name__ == "__main__":
    main()
