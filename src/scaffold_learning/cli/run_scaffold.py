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
from typing import Optional, Union
import threading
import queue
import time


def _get_exit_code(
    completed_process: Optional[subprocess.CompletedProcess] = None,
    error: Optional[Exception] = None,
) -> int:
    """Determine the appropriate exit code."""
    if completed_process is not None and error is not None:
        raise ValueError("Cannot provide both completed_process and error")
    if completed_process is None and error is None:
        raise ValueError("Must provide either completed_process or error")

    if completed_process is not None:
        return completed_process.returncode
    else:  # error is not None
        # Determine exit code based on error type
        if hasattr(error, "returncode"):
            return error.returncode
        elif isinstance(error, subprocess.TimeoutExpired):
            return 124  # Standard timeout exit code
        else:
            return 1  # General error


def _log_results(
    log_file: Path,
    scaffold_name: str,
    executor_model_spec: str,
    input_string: str,
    timestamp: str,
    stdout: Optional[Union[str, bytes]] = None,
    stderr: Optional[Union[str, bytes]] = None,
    error_message: Optional[str] = None,
) -> None:
    """Save execution log in a unified format."""

    def decode_output(output: Optional[Union[str, bytes]]) -> Optional[str]:
        """Convert bytes to string if needed."""
        if output is None:
            return None
        if isinstance(output, bytes):
            return output.decode("utf-8", errors="replace")
        return output.strip()

    stdout = decode_output(stdout)
    stderr = decode_output(stderr)

    # Save to log file
    with open(log_file, "w") as f:
        # Header
        f.write("=== Scaffold Execution Log ===\n")
        f.write(f"Scaffold: {scaffold_name}\n")
        f.write(f"Executor: {executor_model_spec}\n")
        f.write(f"Timestamp: {timestamp}\n")
        if error_message:
            f.write(f"Error: {error_message}\n")

        f.write("================================\n\n")

        # Input
        f.write("=== INPUT ===\n")
        f.write(input_string)
        f.write("\n\n")

        # Output
        if stderr:
            f.write("=== STDERR ===\n")
            f.write(stderr)
            f.write("\n\n")

        if stdout:
            f.write("=== STDOUT ===\n")
            f.write(stdout)
            f.write("\n\n")


def _print_results(stdout: Optional[str], stderr: Optional[str]) -> None:
    """Print results to console."""
    if stderr:
        print(stderr, file=sys.stderr, end="")
    if stdout:
        print(stdout, end="")


def _load_metadata(scaffold_name: str, scaffold_dir: str) -> dict:
    """Load metadata for a scaffold."""
    metadata_path = Path(scaffold_dir) / scaffold_name / "metadata.json"
    if not metadata_path.exists():
        raise FileNotFoundError(f"Metadata file not found: {metadata_path}")

    with open(metadata_path, "r") as f:
        return json.load(f)


def _ensure_docker_image():
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


def _resolve_executor_model_spec(metadata: dict, override_model: str = None) -> str:
    """Resolve executor specification, handling overrides."""
    if override_model:
        from scaffold_learning.core.llm_interfaces import LLMFactory

        return LLMFactory.resolve_model_spec(override_model)
    else:
        return metadata["executor_model_spec"]


def _build_docker_command(
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


def _generate_python_script(
    scaffold_name: str,
    input_string: str,
    executor_model_spec: str,
    log_level: str,
    timestamp: str,
) -> str:
    """Generate the Python script to run inside the Docker container."""
    # Properly escape the input string for Python
    escaped_input = json.dumps(input_string)

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

# Use properly escaped input string
input_string = {escaped_input}

logging.info(f'Running scaffold: {scaffold_name}')
logging.info(f'Input length: {{len(input_string)}} characters')
logging.info(f'Executor: {executor_model_spec}')

try:
    # Import scaffold
    sys.path.insert(0, '/workspace/scaffold')
    from scaffold import process_input
    
    # Run the scaffold
    result = process_input(input_string)
    print(result)
    
    # Save result to log file
    log_data = {{
        'scaffold_name': '{scaffold_name}',
        'timestamp': datetime.now().isoformat(),
        'input': input_string,
        'result': result,
        'executor_model_spec': '{executor_model_spec}',
        'log_level': '{log_level}'
    }}
    
    with open('/workspace/logs/{timestamp}.json', 'w') as f:
        json.dump(log_data, f, indent=2)
        
except Exception as e:
    logging.error(f'Error occurred: {{str(e)}}', exc_info=True)
    sys.exit(1)
"""


def _setup_scaffold_execution(
    scaffold_name: str, scaffold_base_dir: str, override_model: str
) -> tuple[str, Path, Path, str]:
    """Setup and validate scaffold execution environment."""
    # Load metadata
    try:
        metadata = _load_metadata(scaffold_name, scaffold_base_dir)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Ensure Docker image exists
    _ensure_docker_image()

    # Prepare directories and paths
    scaffold_dir = Path(scaffold_base_dir) / scaffold_name
    if not scaffold_dir.exists():
        print(f"Error: Scaffold directory not found: {scaffold_dir}")
        sys.exit(1)

    # Create scaffold-specific log directory
    logs_dir = Path("logs") / scaffold_name
    logs_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Resolve executor specification
    executor_model_spec = _resolve_executor_model_spec(metadata, override_model)

    return executor_model_spec, scaffold_dir, logs_dir, timestamp


def _prepare_docker_execution(
    scaffold_name: str,
    scaffold_dir: Path,
    logs_dir: Path,
    timestamp: str,
    executor_model_spec: str,
    log_level: str,
    keep_container: bool,
    input_string: str,
) -> list[str]:
    """Prepare Docker command for execution."""
    # Build Docker command
    docker_cmd = _build_docker_command(
        scaffold_dir,
        logs_dir,
        scaffold_name,
        timestamp,
        executor_model_spec,
        log_level,
        keep_container,
    )

    # Add Python script to execute
    python_script = _generate_python_script(
        scaffold_name, input_string, executor_model_spec, log_level, timestamp
    )
    docker_cmd.extend(["python", "-c", python_script])

    return docker_cmd


def _execute_human_scaffold(
    docker_cmd: list[str],
    timeout: int,
    log_file: Path,
    scaffold_name: str,
    executor_model_spec: str,
    input_string: str,
    timestamp: str,
) -> int:
    """Execute scaffold with human model."""
    if timeout:
        print("Warning: Timeout not supported for human model (interactive mode)")

    result = subprocess.run(docker_cmd, check=False)

    # Save log for human model
    _log_results(
        log_file,
        scaffold_name,
        executor_model_spec,
        input_string,
        timestamp,
        stdout="Note: Human model execution - no output captured\nUser interaction occurred directly in terminal.\n",
    )
    return _get_exit_code(completed_process=result)


def _execute_llm_scaffold(
    docker_cmd: list[str],
    timeout: int,
    log_file: Path,
    scaffold_name: str,
    executor_model_spec: str,
    input_string: str,
    timestamp: str,
) -> int:
    """Execute scaffold with LLM model."""

    def stream_output(pipe, output_queue, stream_name):
        """Stream output from pipe to queue."""
        try:
            for line in iter(pipe.readline, ""):
                output_queue.put((stream_name, line))
            pipe.close()
        except Exception as e:
            output_queue.put((stream_name, f"Error reading {stream_name}: {e}\n"))

    try:
        # Start process
        process = subprocess.Popen(
            docker_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )

        # Set up output streaming
        output_queue = queue.Queue()
        stdout_thread = threading.Thread(
            target=stream_output, args=(process.stdout, output_queue, "stdout")
        )
        stderr_thread = threading.Thread(
            target=stream_output, args=(process.stderr, output_queue, "stderr")
        )

        stdout_thread.daemon = True
        stderr_thread.daemon = True
        stdout_thread.start()
        stderr_thread.start()

        stdout_lines = []
        stderr_lines = []
        start_time = time.time()

        # Process output in real-time
        while process.poll() is None:
            # Check timeout
            if timeout and (time.time() - start_time) > timeout:
                process.kill()
                raise subprocess.TimeoutExpired(docker_cmd, timeout)

            try:
                # Get output with short timeout to avoid blocking
                stream_name, line = output_queue.get(timeout=0.1)

                if stream_name == "stdout":
                    stdout_lines.append(line)
                    print(line, end="")  # Print immediately
                elif stream_name == "stderr":
                    stderr_lines.append(line)
                    print(line, end="", file=sys.stderr)  # Print immediately

            except queue.Empty:
                continue  # No output available, continue checking

        # Process any remaining output after process finishes
        while not output_queue.empty():
            try:
                stream_name, line = output_queue.get_nowait()
                if stream_name == "stdout":
                    stdout_lines.append(line)
                    print(line, end="")
                elif stream_name == "stderr":
                    stderr_lines.append(line)
                    print(line, end="", file=sys.stderr)
            except queue.Empty:
                break

        # Wait for threads to finish
        stdout_thread.join(timeout=1)
        stderr_thread.join(timeout=1)

        # Combine all output
        full_stdout = "".join(stdout_lines)
        full_stderr = "".join(stderr_lines)

        # Save execution log to file
        _log_results(
            log_file,
            scaffold_name,
            executor_model_spec,
            input_string,
            timestamp,
            stdout=full_stdout,
            stderr=full_stderr,
        )

        return process.returncode

    except subprocess.TimeoutExpired:
        error_msg = f"Execution timed out after {timeout} seconds"
        print(f"Error: {error_msg}", file=sys.stderr)

        _log_results(
            log_file,
            scaffold_name,
            executor_model_spec,
            input_string,
            timestamp,
            error_message=error_msg,
        )
        return 124  # Timeout exit code


def _handle_execution_error(
    e: Exception,
    log_file: Path,
    scaffold_name: str,
    executor_model_spec: str,
    input_string: str,
    timestamp: str,
) -> int:
    """Handle execution errors and log them."""
    # Extract stdout/stderr from exception if available
    error_stdout = e.stdout if hasattr(e, "stdout") else None
    error_stderr = e.stderr if hasattr(e, "stderr") else None

    _log_results(
        log_file,
        scaffold_name,
        executor_model_spec,
        input_string,
        timestamp,
        stdout=error_stdout,
        stderr=error_stderr,
        error_message=str(e),
    )
    # Print error information to console
    _print_results(error_stdout, error_stderr)
    return _get_exit_code(error=e)


def run_scaffold(
    scaffold_name: str,
    scaffold_base_dir: str,
    input_string: str,
    log_level: str,
    override_model: str,
    keep_container: bool,
    timeout: int = None,
) -> int:
    """Run a scaffold in Docker container."""

    # Setup and validation
    executor_model_spec, scaffold_dir, logs_dir, timestamp = _setup_scaffold_execution(
        scaffold_name, scaffold_base_dir, override_model
    )

    log_file = logs_dir / f"{timestamp}.log"

    # Prepare Docker execution
    docker_cmd = _prepare_docker_execution(
        scaffold_name,
        scaffold_dir,
        logs_dir,
        timestamp,
        executor_model_spec,
        log_level,
        keep_container,
        input_string,
    )

    print(f"Running scaffold '{scaffold_name}' with executor {executor_model_spec}")
    print(f"Logs will be saved to: {log_file}")

    try:
        if executor_model_spec == "human/human":
            return _execute_human_scaffold(
                docker_cmd,
                timeout,
                log_file,
                scaffold_name,
                executor_model_spec,
                input_string,
                timestamp,
            )
        else:
            return _execute_llm_scaffold(
                docker_cmd,
                timeout,
                log_file,
                scaffold_name,
                executor_model_spec,
                input_string,
                timestamp,
            )

    except Exception as e:
        return _handle_execution_error(
            e, log_file, scaffold_name, executor_model_spec, input_string, timestamp
        )


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
        "--keep-container",
        action="store_true",
        help="Keep the container after execution (for debugging)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        help="Timeout in seconds for scaffold execution (default: no timeout)",
    )

    args = parser.parse_args()

    # Validate that file and input_string are not both provided
    if args.file and args.input_string:
        raise ValueError("Cannot specify both --file and input_string argument")

    return args


def _get_input_string(args: argparse.Namespace) -> str:
    """Get the input string from the command line arguments or stdin."""
    try:
        if args.file:
            with open(args.file, "r", encoding="utf-8") as f:
                return f.read().strip()
        elif args.input_string:
            return args.input_string
        else:
            return input().strip()
    except FileNotFoundError:
        print(f"Error: Input file '{args.file}' not found")
        sys.exit(2)  # File not found error
    except PermissionError:
        print(f"Error: Permission denied reading file '{args.file}'")
        sys.exit(2)  # Permission error
    except (EOFError, KeyboardInterrupt):
        print("\nError: No input provided")
        sys.exit(130)  # Interrupted by user (Ctrl+C)


def main():
    try:
        args = _parse_args()

        # Get input string (from file, command line argument, or stdin)
        input_string = _get_input_string(args)

        exit_code = run_scaffold(
            args.scaffold_name,
            args.scaffold_dir,
            input_string,
            args.log_level,
            args.model,
            args.keep_container,
            args.timeout,
        )

        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(130)  # Interrupted by user (Ctrl+C)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)  # General error


if __name__ == "__main__":
    main()
