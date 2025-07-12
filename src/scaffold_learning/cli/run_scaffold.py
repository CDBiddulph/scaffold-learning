#!/usr/bin/env python3
"""
Run a generated scaffold script in a Docker container.
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from scaffold_learning.core.scaffold_execution import execute_scaffold
from scaffold_learning.core.docker_utils import build_docker_image


def run_scaffold(
    scaffold_name: str,
    scaffold_base_dir: str,
    input_string: str,
    model_spec: str,
    timeout: Optional[int] = None,
    build_docker: bool = True,
) -> None:
    """Run a scaffold in Docker container."""

    if build_docker:
        print("Building Docker image...")
        build_docker_image()

    # Prepare directories and paths
    scaffold_dir = Path(scaffold_base_dir) / scaffold_name
    if not scaffold_dir.exists():
        raise FileNotFoundError(f"Scaffold directory not found: {scaffold_dir}")

    # Create scaffold-specific log directory
    logs_dir = Path("logs") / scaffold_name
    logs_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file_path = logs_dir / f"{timestamp}.log"

    print(f"Running scaffold '{scaffold_name}' with executor {model_spec}")
    print(f"Scaffold directory: {scaffold_dir}")
    print(f"Logs will be saved to: {log_file_path}")

    # Execute the scaffold and handle errors
    try:
        result = execute_scaffold(
            scaffold_dir=scaffold_dir,
            log_file_path=log_file_path,
            input_string=input_string,
            model_spec=model_spec,
            timeout=timeout or 120,
            console_output=True,
        )

        # Handle errors from scaffold execution
        if result.error_message:
            raise RuntimeError(result.error_message)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a scaffold script in Docker")
    parser.add_argument("scaffold_name", help="Name of the scaffold (without path)")
    parser.add_argument(
        "input_string",
        nargs="?",
        help="Input string to process (if not provided, will read from stdin)",
    )
    parser.add_argument(
        "--scaffold-dir",
        default="scaffold-scripts",
        help="Base directory for scaffold scripts",
    )
    parser.add_argument(
        "--file",
        "-f",
        help="Read input from file instead of command line or stdin",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level",
    )
    parser.add_argument(
        "--model",
        help="Override the executor model (e.g., 'gpt-4o', 'claude-3-5-sonnet-latest')",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        help="Timeout in seconds for scaffold execution (default: no timeout)",
    )
    parser.add_argument(
        "--no-build",
        action="store_true",
        help="Skip building Docker image (assume it already exists)",
    )

    args = parser.parse_args()

    # Validate that file and input_string are not both provided
    if args.file and args.input_string:
        raise ValueError("Cannot specify both --file and input_string argument")

    return args


def _get_input_string(args: argparse.Namespace) -> str:
    """Get the input string from the command line arguments or stdin."""
    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            return f.read().strip()
    elif args.input_string:
        return args.input_string
    else:
        return input().strip()


def main():
    args = _parse_args()
    input_string = _get_input_string(args)

    run_scaffold(
        args.scaffold_name,
        args.scaffold_dir,
        input_string,
        args.model,
        args.timeout,
        build_docker=not args.no_build,
    )


if __name__ == "__main__":
    main()
