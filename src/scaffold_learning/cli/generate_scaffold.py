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
from pathlib import Path
from typing import Dict, Any
from scaffold_learning.core.llm_interfaces import LLMFactory
from scaffold_learning.core.scaffold_generation import (
    generate_scaffold,
)
from scaffold_learning.core.scaffold_files import save_scaffold
import shutil
import logging


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
        "task_description",
        help="Description of the task to be performed by the scaffold",
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
    parser.add_argument(
        "--scaffolder-model",
        default="gpt-4.1-nano",
        help="Scaffolder LLM model (e.g., 'gpt-4o', 'claude-3-5-sonnet-latest', 'openai/new-model', 'mock', 'human')",
    )

    args = parser.parse_args()

    try:
        # Create LLM instances using new consolidated model specification
        scaffolder_llm = LLMFactory.create_llm(model_spec=args.scaffolder_model)
        scaffolder_model_spec = LLMFactory.resolve_model_spec(args.scaffolder_model)

        # Construct output directory path
        output_dir = os.path.join(args.scaffold_dir, args.scaffold_name)

        # Log configuration summary
        logger.info("Configuration Summary:")
        logger.info(f"Scaffold Name: {args.scaffold_name}")
        logger.info(f"Task Description: {args.task_description}")
        logger.info(f"Output Directory: {output_dir}")
        logger.info(f"Scaffolder LLM: {scaffolder_model_spec}")

        # Generate the script using the new module
        result = generate_scaffold(
            scaffolder_llm=scaffolder_llm,
            task_description=args.task_description,
            iteration=0,
        )

        # Only delete and create output directory after script is generated successfully
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)

        # Save scaffold to output directory
        save_scaffold(Path(output_dir), result)

        logger.info(f"Scaffold saved to: {output_dir}")
        print(f"\nGeneration complete! To run the generated scaffold:")
        print(f"  run-scaffold {args.scaffold_name} 'your input string' --model haiku")

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
