#!/usr/bin/env python3
"""
Multi-LLM Script Generator

This script uses a "coder LLM" to generate Python scripts that can utilize an "executor LLM".
The generated script will take string input and produce string output.
"""

import argparse
import os
import sys
from typing import Dict, Any
from llm_interfaces import LLMFactory
import shutil
import logging

# Template file paths
MAIN_SCRIPT_TEMPLATE = "templates/main_script_template.py"
CODER_SYSTEM_PROMPT_TEMPLATE = "templates/coder_system_prompt.txt"
EXECUTOR_LIBRARY_TEMPLATE = "templates/executor_library_template.py"


def get_main_script() -> str:
    """Generate the main script that handles boilerplate functionality"""
    with open(MAIN_SCRIPT_TEMPLATE, "r") as f:
        return f.read()


def get_coder_system_prompt() -> str:
    """Get the system prompt for the coder LLM"""
    with open(CODER_SYSTEM_PROMPT_TEMPLATE, "r") as f:
        return f.read()


def generate_executor_library_code(executor_config: Dict[str, Any]) -> str:
    """Generate the executor library code that will be available to generated scripts"""
    with open(EXECUTOR_LIBRARY_TEMPLATE, "r") as f:
        template = f.read()
        return template.format(executor_config=repr(executor_config))


def main() -> None:
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    logger = logging.getLogger(__name__)
    
    parser = argparse.ArgumentParser(description="Generate Python scripts using a coder LLM")
    parser.add_argument("coder_prompt", help="Prompt describing what the generated script should do")
    parser.add_argument("-o", "--output", required=True, help="Output directory for the generated script")
    
    # Coder LLM configuration
    parser.add_argument("--coder-type", default="openai", help="Type of coder LLM (openai, anthropic)")
    parser.add_argument("--coder-model", help="Specific model for coder LLM")
    parser.add_argument("--coder-api-key", help="API key for coder LLM")
    
    # Executor LLM configuration
    parser.add_argument("--executor-type", default="openai", help="Type of executor LLM (openai, anthropic)")
    parser.add_argument("--executor-model", help="Specific model for executor LLM")
    parser.add_argument("--executor-api-key", help="API key for executor LLM")
    
    args = parser.parse_args()
    
    try:
        # Delete the output directory if it exists
        if os.path.exists(args.output):
            shutil.rmtree(args.output)
        # Create the output directory
        os.makedirs(args.output)
        
        # Create LLM instances
        coder_llm = LLMFactory.create_llm(
            llm_type=args.coder_type,
            model=args.coder_model,
            api_key=args.coder_api_key
        )
        
        executor_llm = LLMFactory.create_llm(
            llm_type=args.executor_type,
            model=args.executor_model,
            api_key=args.executor_api_key
        )
        
        # Log configuration summary
        logger.info("Configuration Summary:")
        logger.info(f"Output Directory: {args.output}")
        logger.info("Coder LLM Configuration:")
        logger.info(f"  Type: {args.coder_type}")
        logger.info(f"  Model: {coder_llm.get_model_info()}")
        logger.info("Executor LLM Configuration:")
        logger.info(f"  Type: {args.executor_type}")
        logger.info(f"  Model: {executor_llm.get_model_info()}")
        logger.info(f"Generating script based on prompt: {args.coder_prompt}")
        
        # Prepare executor configuration
        executor_config = {
            "type": args.executor_type,
            "model": args.executor_model,
            "api_key": args.executor_api_key
        }
        
        # Generate the script using coder LLM
        system_prompt = get_coder_system_prompt()
        generated_script = coder_llm.generate_response(args.coder_prompt, system_prompt)
        
        # Clean up the generated script (remove markdown formatting if present)
        if "```python" in generated_script:
            generated_script = generated_script.split("```python")[1].split("```")[0].strip()
        elif "```" in generated_script:
            generated_script = generated_script.split("```")[1].split("```")[0].strip()
        
        # Write the generated script to file
        scaffold_file = os.path.join(args.output, "scaffold.py")
        with open(scaffold_file, 'w') as f:
            f.write(generated_script)

        # Write the main script
        main_file = os.path.join(args.output, "main.py")
        with open(main_file, 'w') as f:
            f.write(get_main_script())
        os.chmod(main_file, 0o755)
        
        # Generate the executor library in the same directory
        executor_lib_path = os.path.join(args.output, "llm_executor.py")
        with open(executor_lib_path, 'w') as f:
            f.write(generate_executor_library_code(executor_config))

        # Copy the llm_interfaces.py file to the output directory
        interfaces_path = os.path.join(args.output, "llm_interfaces.py")
        shutil.copy2("llm_interfaces.py", interfaces_path)
        
        logger.info(f"Generated script saved to: {scaffold_file}")
        logger.info(f"Main script saved to: {main_file}")
        logger.info(f"Executor library saved to: {executor_lib_path}")
        logger.info(f"LLM interfaces copied to: {interfaces_path}")
        print(f"\nGeneration complete! To run the generated script:")
        print(f"  python {main_file} 'your input string'")
        print(f"  python {main_file} 'your input string' --log-level DEBUG")
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
