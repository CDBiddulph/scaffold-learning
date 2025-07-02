#!/usr/bin/env python3
"""
Multi-LLM Script Generator

This script uses a "coder LLM" to generate Python scripts that can utilize an "executor LLM".
The generated script will take string input and produce string output.
"""

import argparse
import os
import sys
import json
from datetime import datetime
from typing import Dict, Any
from llm_interfaces import LLMFactory
import shutil
import logging

# Template file paths
CODER_SYSTEM_PROMPT_TEMPLATE = "templates/coder_system_prompt.txt"


def get_coder_system_prompt() -> str:
    """Get the system prompt for the coder LLM"""
    with open(CODER_SYSTEM_PROMPT_TEMPLATE, "r") as f:
        return f.read()


def main() -> None:
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    logger = logging.getLogger(__name__)

    parser = argparse.ArgumentParser(
        description="Generate Python scripts using a coder LLM"
    )
    parser.add_argument(
        "coder_prompt", help="Prompt describing what the generated script should do"
    )
    parser.add_argument(
        "-o",
        "--output",
        required=True,
        help="Output directory for the generated script",
    )

    # LLM configuration
    parser.add_argument(
        "--coder-model",
        default="gpt-4.1-nano",
        help="Coder LLM model (e.g., 'gpt-4o', 'claude-3-5-sonnet-latest', 'openai/new-model', 'mock', 'human')",
    )
    parser.add_argument(
        "--executor-model",
        default="gpt-4.1-nano",
        help="Executor LLM model (e.g., 'gpt-4o', 'claude-3-5-sonnet-latest', 'openai/new-model', 'mock', 'human')",
    )

    # API Keys
    parser.add_argument("--openai-api-key", help="OpenAI API key")
    parser.add_argument("--anthropic-api-key", help="Anthropic API key")

    args = parser.parse_args()

    try:
        # Create LLM instances using new consolidated model specification
        coder_llm = LLMFactory.create_llm(
            model_spec=args.coder_model,
            openai_api_key=args.openai_api_key,
            anthropic_api_key=args.anthropic_api_key,
        )

        coder_model_spec = LLMFactory.resolve_model_spec(args.coder_model)
        executor_model_spec = LLMFactory.resolve_model_spec(args.executor_model)

        # Log configuration summary
        logger.info("Configuration Summary:")
        logger.info(f"Output Directory: {args.output}")
        logger.info(f"Coder LLM: {coder_model_spec}")
        logger.info(f"Executor LLM: {executor_model_spec}")
        logger.info(f"Generating script based on prompt: {args.coder_prompt}")

        # Generate the script using coder LLM
        system_prompt = get_coder_system_prompt()
        generated_script = coder_llm.generate_response(args.coder_prompt, system_prompt)

        # Clean up the generated script (remove markdown formatting if present)
        if "```python" in generated_script:
            generated_script = (
                generated_script.split("```python")[1].split("```")[0].strip()
            )
        elif "```" in generated_script:
            generated_script = generated_script.split("```")[1].split("```")[0].strip()

        # Only delete and create output directory after script is generated successfully
        if os.path.exists(args.output):
            shutil.rmtree(args.output)
        os.makedirs(args.output)

        # Write the generated script to file
        scaffold_file = os.path.join(args.output, "scaffold.py")
        with open(scaffold_file, "w") as f:
            f.write(generated_script)

        # Create metadata file with executor configuration
        metadata = {
            "executor_model_spec": executor_model_spec,
            "coder_model_spec": coder_model_spec,
            "prompt": args.coder_prompt,
            "created": datetime.now().isoformat(),
        }

        metadata_file = os.path.join(args.output, "metadata.json")
        with open(metadata_file, "w") as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"Generated script saved to: {scaffold_file}")
        logger.info(f"Metadata saved to: {metadata_file}")
        print(f"\nGeneration complete! To run the generated script:")
        print(
            f"  python run_scaffold.py {os.path.basename(args.output)} 'your input string'"
        )
        print(
            f"  python run_scaffold.py {os.path.basename(args.output)} 'your input string' --log-level DEBUG --model claude-3-5-sonnet-latest"
        )

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
