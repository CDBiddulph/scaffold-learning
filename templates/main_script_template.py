#!/usr/bin/env python3
"""
Main script that handles boilerplate functionality for generated scripts.
"""

import logging
import argparse
from typing import Optional


def run_script(
    input_string: str, log_level: str = "INFO", override_model: Optional[str] = None
) -> Optional[str]:
    """
    Run the generated script with the given input and log level.

    Args:
        input_string: The input string to process
        log_level: The logging level to use
        override_model: Optional model override (e.g., 'gpt-4o', 'claude-3-5-sonnet-latest')

    Returns:
        The script's output string, or None if there was an error
    """
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    logging.info(f"Processing input: {input_string}")

    # Override executor model if specified
    if override_model:
        logging.info(f"Overriding executor model to: {override_model}")
        import llm_executor
        from llm_interfaces import LLMFactory

        # Parse the override model and update the config
        executor_type, model = LLMFactory.parse_model_spec(override_model)
        llm_executor.EXECUTOR_CONFIG["type"] = executor_type
        llm_executor.EXECUTOR_CONFIG["model"] = model

    try:
        # Import and run the generated script
        from scaffold import process_input

        result = process_input(input_string)
        print(result)
        return result
    except Exception as e:
        logging.error(f"Error occurred: {str(e)}", exc_info=True)
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_string", nargs="?", help="Input string to process")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level",
    )
    parser.add_argument(
        "--model",
        help="Override the executor model (e.g., 'gpt-4o', 'claude-3-5-sonnet-latest', 'anthropic/claude-3-haiku')",
    )
    args = parser.parse_args()

    # Get input string (from command line argument or stdin)
    if args.input_string:
        input_string = args.input_string
    else:
        input_string = input().strip()

    run_script(input_string, args.log_level, args.model)


if __name__ == "__main__":
    main()
