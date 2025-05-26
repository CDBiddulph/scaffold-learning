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
        
        # Print configuration summary
        print("\nConfiguration Summary:")
        print(f"Output Directory: {args.output}")
        print("\nCoder LLM Configuration:")
        print(f"  Type: {args.coder_type}")
        print(f"  Model: {coder_llm.get_model_info()}")
        print("\nExecutor LLM Configuration:")
        print(f"  Type: {args.executor_type}")
        print(f"  Model: {executor_llm.get_model_info()}")
        print("\nGenerating script based on prompt:", args.coder_prompt)
        print("-" * 80)
        
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
        
        print(f"Generated script saved to: {scaffold_file}")
        print(f"Main script saved to: {main_file}")
        print(f"Executor library saved to: {executor_lib_path}")
        print(f"LLM interfaces copied to: {interfaces_path}")
        print(f"\nTo run the generated script:")
        print(f"  python {main_file} 'your input string'")
        print(f"  python {main_file} 'your input string' --log-level DEBUG")
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
