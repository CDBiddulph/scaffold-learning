#!/usr/bin/env python3
"""
Run a generated scaffold script in a Docker container.
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def load_metadata(scaffold_name: str) -> dict:
    """Load metadata for a scaffold."""
    metadata_path = Path("scaffold-scripts") / scaffold_name / "metadata.json"
    if not metadata_path.exists():
        raise FileNotFoundError(f"Metadata file not found: {metadata_path}")

    with open(metadata_path, "r") as f:
        return json.load(f)


def ensure_docker_image():
    """Ensure the Docker image is built."""
    try:
        # Check if image exists
        result = subprocess.run(
            ["docker", "inspect", "scaffold-runner"], capture_output=True, check=False
        )

        if result.returncode != 0:
            print("Building Docker image...")
            subprocess.run(
                ["docker", "build", "-t", "scaffold-runner", "."], check=True
            )
            print("Docker image built successfully!")
    except subprocess.CalledProcessError as e:
        print(f"Failed to build Docker image: {e}")
        sys.exit(1)


def resolve_executor_model_spec(metadata: dict, override_model: str = None) -> str:
    """Resolve executor specification, handling overrides."""
    if override_model:
        from llm_interfaces import LLMFactory

        return LLMFactory.resolve_model_spec(override_model)
    else:
        return metadata["executor_model_spec"]


def build_docker_command(
    scaffold_dir: Path,
    logs_dir: Path,
    scaffold_name: str,
    timestamp: str,
    executor_model_spec: str,
    log_level: str,
    keep_container: bool = False,
) -> list[str]:
    """Build the Docker command with all necessary flags and environment variables."""
    docker_cmd = ["docker", "run", "--rm"]

    if keep_container:
        docker_cmd.extend(["--name", f"scaffold-{scaffold_name}-{timestamp}"])

    # Check if we need interactive mode for human model
    if executor_model_spec == "human/human":
        docker_cmd.insert(2, "-it")
        print("Note: Using interactive mode for human model")

    docker_cmd.extend(
        [
            "--user",
            f"{os.getuid()}:{os.getgid()}",
            "-v",
            f"{scaffold_dir.absolute()}:/workspace/scaffold",
            "-v",
            f"{logs_dir.absolute()}:/workspace/logs",
        ]
    )

    # Add environment variables from .env file if it exists
    env_file = Path(".env")
    if env_file.exists():
        docker_cmd.extend(["--env-file", str(env_file.absolute())])

    docker_cmd.extend(
        [
            "-e",
            f"EXECUTOR_MODEL_SPEC={executor_model_spec}",
            "-e",
            f"LOG_LEVEL={log_level}",
            "scaffold-runner",
        ]
    )

    return docker_cmd


def generate_python_script(
    scaffold_name: str,
    input_string: str,
    executor_model_spec: str,
    log_level: str,
    timestamp: str,
) -> str:
    """Generate the Python script to run inside the Docker container."""
    return f"""
import sys
import logging
import json
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=getattr(logging, '{log_level}'),
    format='%(asctime)s [%(levelname)s] %(message)s',
)

logging.info(f'Running scaffold: {scaffold_name}')
logging.info(f'Input: {input_string}')
logging.info(f'Executor: {executor_model_spec}')

try:
    # Import scaffold
    sys.path.insert(0, '/workspace/scaffold')
    from scaffold import process_input
    
    # Run the scaffold
    result = process_input('{input_string}')
    print(result)
    
    # Save result to log file
    log_data = {{
        'scaffold_name': '{scaffold_name}',
        'timestamp': datetime.now().isoformat(),
        'input': '{input_string}',
        'result': result,
        'executor_model_spec': '{executor_model_spec}',
        'log_level': '{log_level}'
    }}
    
    with open('/workspace/logs/{scaffold_name}_{timestamp}.json', 'w') as f:
        json.dump(log_data, f, indent=2)
        
except Exception as e:
    logging.error(f'Error occurred: {{str(e)}}', exc_info=True)
    sys.exit(1)
"""


def save_execution_log(
    log_file: Path,
    scaffold_name: str,
    executor_model_spec: str,
    input_string: str,
    timestamp: str,
    result: subprocess.CompletedProcess,
) -> None:
    """Save the execution log to a file."""
    with open(log_file, "w") as f:
        f.write(f"=== Scaffold Execution Log ===\n")
        f.write(f"Scaffold: {scaffold_name}\n")
        f.write(f"Executor: {executor_model_spec}\n")
        f.write(f"Input: {input_string}\n")
        f.write(f"Timestamp: {timestamp}\n")
        f.write(f"Exit Code: {result.returncode}\n")
        f.write(f"================================\n\n")

        if result.stdout:
            f.write("=== STDOUT ===\n")
            f.write(result.stdout)
            f.write("\n")

        if result.stderr:
            f.write("=== STDERR ===\n")
            f.write(result.stderr)
            f.write("\n")


def run_scaffold(
    scaffold_name: str,
    input_string: str,
    log_level: str = "INFO",
    override_model: str = None,
    keep_container: bool = False,
) -> None:
    """Run a scaffold in Docker container."""

    # Load metadata
    try:
        metadata = load_metadata(scaffold_name)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Ensure Docker image exists
    ensure_docker_image()

    # Prepare directories and paths
    scaffold_dir = Path("scaffold-scripts") / scaffold_name
    if not scaffold_dir.exists():
        print(f"Error: Scaffold directory not found: {scaffold_dir}")
        sys.exit(1)

    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = logs_dir / f"{scaffold_name}_{timestamp}.log"

    # Resolve executor specification
    executor_model_spec = resolve_executor_model_spec(metadata, override_model)

    # Build Docker command
    docker_cmd = build_docker_command(
        scaffold_dir,
        logs_dir,
        scaffold_name,
        timestamp,
        executor_model_spec,
        log_level,
        keep_container,
    )

    # Add Python script to execute
    python_script = generate_python_script(
        scaffold_name, input_string, executor_model_spec, log_level, timestamp
    )
    docker_cmd.extend(["python", "-c", python_script])

    print(f"Running scaffold '{scaffold_name}' with executor {executor_model_spec}")
    print(f"Logs will be saved to: {log_file}")

    try:
        if executor_model_spec == "human/human":
            # For human model, don't capture output - let it connect directly to terminal
            result = subprocess.run(docker_cmd, check=False)

            # Create a minimal log file for human model
            with open(log_file, "w") as f:
                f.write(f"=== Scaffold Execution Log ===\n")
                f.write(f"Scaffold: {scaffold_name}\n")
                f.write(f"Executor: {executor_model_spec}\n")
                f.write(f"Input: {input_string}\n")
                f.write(f"Timestamp: {timestamp}\n")
                f.write(f"Exit Code: {result.returncode}\n")
                f.write(f"================================\n\n")
                f.write("Note: Human model execution - no output captured\n")
                f.write("User interaction occurred directly in terminal.\n")

            return result.returncode
        else:
            # For other models, capture output as before
            result = subprocess.run(
                docker_cmd, capture_output=True, text=True, check=False
            )

            # Save execution log to file
            save_execution_log(
                log_file,
                scaffold_name,
                executor_model_spec,
                input_string,
                timestamp,
                result,
            )

        # Print to console for immediate feedback
        if result.stdout:
            print(result.stdout, end="")
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr)

        return result.returncode
    except subprocess.CalledProcessError as e:
        print(f"Failed to run scaffold: {e}")
        return 1


def main():
    parser = argparse.ArgumentParser(description="Run a scaffold script in Docker")
    parser.add_argument("scaffold_name", help="Name of the scaffold directory")
    parser.add_argument("input_string", nargs="?", help="Input string to process")
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
        "--keep-container",
        action="store_true",
        help="Keep the container after execution (for debugging)",
    )

    args = parser.parse_args()

    # Get input string (from command line argument or stdin)
    if args.input_string:
        input_string = args.input_string
    else:
        input_string = input().strip()

    exit_code = run_scaffold(
        args.scaffold_name,
        input_string,
        args.log_level,
        args.model,
        args.keep_container,
    )

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
