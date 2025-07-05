#!/usr/bin/env python3
"""
Multi-LLM Script Generator

This script uses a "scaffolder LLM" to generate Python scripts that can utilize an "executor LLM".
The generated script will take string input and produce string output.
"""

import argparse
import os
import sys
import json
from datetime import datetime
from typing import Dict, Any
from scaffold_learning.core.llm_interfaces import LLMFactory
import shutil
import logging

# Template file paths
SCAFFOLDER_SYSTEM_PROMPT_TEMPLATE = "prompts/scaffolder_system_prompt.txt"


def get_scaffolder_system_prompt() -> str:
    """Get the system prompt for the scaffolder LLM"""
    with open(SCAFFOLDER_SYSTEM_PROMPT_TEMPLATE, "r") as f:
        return f.read()


def main() -> None:
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    logger = logging.getLogger(__name__)

    parser = argparse.ArgumentParser(
        description="Generate Python scripts using a scaffolder LLM"
    )
    parser.add_argument(
        "scaffolder_prompt",
        help="Prompt describing what the generated script should do",
    )
    parser.add_argument(
        "--scaffold-name",
        help="Name for the scaffold",
    )
    parser.add_argument(
        "--scaffold-dir",
        default="scaffold-scripts",
        help="Base directory for scaffold scripts",
    )

    # LLM configuration
    parser.add_argument(
        "--scaffolder-model",
        default="gpt-4.1-nano",
        help="Scaffolder LLM model (e.g., 'gpt-4o', 'claude-3-5-sonnet-latest', 'openai/new-model', 'mock', 'human')",
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
        scaffolder_llm = LLMFactory.create_llm(
            model_spec=args.scaffolder_model,
            openai_api_key=args.openai_api_key,
            anthropic_api_key=args.anthropic_api_key,
        )

        scaffolder_model_spec = LLMFactory.resolve_model_spec(args.scaffolder_model)
        executor_model_spec = LLMFactory.resolve_model_spec(args.executor_model)

        # Construct output directory path
        output_dir = os.path.join(args.scaffold_dir, args.scaffold_name)

        # Log configuration summary
        logger.info("Configuration Summary:")
        logger.info(f"Scaffold Name: {args.scaffold_name}")
        logger.info(f"Output Directory: {output_dir}")
        logger.info(f"Scaffolder LLM: {scaffolder_model_spec}")
        logger.info(f"Executor LLM: {executor_model_spec}")
        logger.info(f"Generating script based on prompt: {args.scaffolder_prompt}")

        # Generate the script using scaffolder LLM
        system_prompt = get_scaffolder_system_prompt()
        generated_script = scaffolder_llm.generate_response(
            args.scaffolder_prompt, system_prompt
        )

        # Clean up the generated script (remove markdown formatting if present)
        if "```python" in generated_script:
            generated_script = (
                generated_script.split("```python")[1].split("```")[0].strip()
            )
        elif "```" in generated_script:
            generated_script = generated_script.split("```")[1].split("```")[0].strip()

        # Only delete and create output directory after script is generated successfully
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)
        os.makedirs(output_dir, exist_ok=True)

        # Write the generated script to file
        scaffold_file = os.path.join(output_dir, "scaffold.py")
        with open(scaffold_file, "w") as f:
            f.write(generated_script)

        # Create metadata file with executor configuration
        metadata = {
            "executor_model_spec": executor_model_spec,
            "scaffolder_model_spec": scaffolder_model_spec,
            "prompt": args.scaffolder_prompt,
            "created": datetime.now().isoformat(),
        }

        metadata_file = os.path.join(output_dir, "metadata.json")
        with open(metadata_file, "w") as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"Generated script saved to: {scaffold_file}")
        logger.info(f"Metadata saved to: {metadata_file}")
        print(f"\nGeneration complete! To run the generated script:")
        print(f"  python run_scaffold.py {args.scaffold_name} 'your input string'")
        print(
            f"  python run_scaffold.py {args.scaffold_name} 'your input string' --log-level DEBUG --model claude-3-5-sonnet-latest"
        )

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
