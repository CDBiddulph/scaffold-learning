import os
import subprocess
import sys
import time
import json
import threading
import queue
from pathlib import Path
from datetime import datetime
from typing import Optional, TextIO
from scaffold_learning.core.data_structures import ScaffoldExecutionResult
from scaffold_learning.core.experiment_files import ExperimentFileManager
from scaffold_learning.core.llm_interfaces import LLMFactory


class ScaffoldTimeoutError(Exception):
    """Exception raised when scaffold execution times out."""

    def __init__(
        self, message: str, partial_stdout: str = "", partial_stderr: str = ""
    ):
        super().__init__(message)
        self.partial_stdout = partial_stdout
        self.partial_stderr = partial_stderr


def _build_docker_command(
    scaffold_dir: Path, model_spec: str, timeout: int, interactive: bool = False
) -> list[str]:
    """Build the Docker command with all necessary flags and environment variables."""
    docker_cmd = ["docker", "run", "--rm"]

    # Add interactive flags for human model
    if interactive:
        docker_cmd.extend(["-it"])

    # Add timeout
    docker_cmd.extend(["--stop-timeout", str(timeout)])

    docker_cmd.extend(
        [
            "--user",
            f"{os.getuid()}:{os.getgid()}",
            "-v",
            f"{scaffold_dir.absolute()}:/workspace/scaffold:ro",
            # TODO: consider uncommenting if we need to write the result as a txt file
            # "-v",
            # f"{logs_dir.absolute()}:/workspace/logs",
        ]
    )

    # Add environment variables from .env file if it exists
    env_file = Path(".env")
    if env_file.exists():
        docker_cmd.extend(["--env-file", str(env_file.absolute())])

    # Add environment variables for API keys
    for key in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY"]:
        if key in os.environ:
            docker_cmd.extend(["-e", f"{key}={os.environ[key]}"])

    docker_cmd.extend(
        [
            "-e",
            f"EXECUTOR_MODEL_SPEC={model_spec}",
            "-e",
            # TODO: try DEBUG after removing extraneous logs from Anthropic
            "LOG_LEVEL=INFO",
            "scaffold-runner",
        ]
    )

    return docker_cmd


def _generate_python_script(
    input_string: str,
    model_spec: str,
) -> str:
    """Generate the Python script to run inside the Docker container."""
    # Properly escape the input string for Python
    escaped_input = json.dumps(input_string)

    return f"""
import sys
import logging
import json
import os
from datetime import datetime

# Configure logging
log_level = getattr(logging, os.environ.get('LOG_LEVEL', 'INFO').upper(), logging.INFO)
logging.basicConfig(
    level=log_level,
    format='%(asctime)s [%(levelname)s] %(message)s',
)

# Use properly escaped input string
input_string = {escaped_input}

# TODO: Not sure if these logs get saved or printed anywhere
logging.info('Running scaffold execution')
logging.info(f'Input length: {{len(input_string)}} characters')
logging.info(f'Executor: {model_spec}')

try:
    # Import scaffold
    sys.path.insert(0, '/workspace/scaffold')
    from scaffold import process_input
    
    # Run the scaffold
    result = process_input(input_string)
    print(result)

    # TODO: consider saving the result to a file, we'll have to get the filename though
    # with open('/workspace/logs/train_0.txt', 'w') as f:
    #     f.write(result)
        
except Exception as e:
    logging.error(f'Error occurred: {{str(e)}}', exc_info=True)
    sys.exit(1)
"""


def _write_to_log_file(
    log_file: TextIO, content: str, stream_name: str, current_stream: Optional[str]
) -> None:
    if current_stream != stream_name:
        log_file.write(f"\n=== {stream_name.upper()} ===\n")
    log_file.write(content)
    log_file.flush()


def _process_output_from_queue(
    output_queue: queue.Queue,
    lines: dict,
    log_file: Optional[TextIO],
    console_output: bool,
    current_stream: Optional[str],
    timeout: Optional[float] = None,
) -> Optional[str]:
    """Process output from the queue if available.

    Args:
        output_queue: Queue containing output lines
        lines: Dictionary to collect lines by stream
        log_file: Optional file handle to write to
        console_output: If True, also print to console
        current_stream: Current stream name (either 'stdout' or 'stderr')
        timeout: Timeout for getting from queue (None for no wait)

    Returns:
        The stream name if output was processed, None if queue was empty
    """
    try:
        if timeout is not None:
            stream_name, line = output_queue.get(timeout=timeout)
        else:
            stream_name, line = output_queue.get_nowait()

        lines[stream_name].append(line)

        # Handle stream transitions for log file
        if log_file:
            _write_to_log_file(log_file, line, stream_name, current_stream)

        # Write to destinations
        if console_output:
            if stream_name == "stdout":
                print(line, end="")
            else:
                print(line, end="", file=sys.stderr)

        return stream_name
    except queue.Empty:
        return None


def _stream_output(pipe: TextIO, output_queue: queue.Queue, stream_name: str) -> None:
    """Stream output from pipe to queue."""
    try:
        for line in iter(pipe.readline, ""):
            output_queue.put((stream_name, line))
        pipe.close()
    except Exception as e:
        output_queue.put((stream_name, f"Error reading {stream_name}: {e}\n"))


def _stream_process_output(
    process: subprocess.Popen,
    timeout: int,
    start_time: float,
    log_file: Optional[TextIO],
    console_output: bool,
) -> tuple[str, str]:
    """Stream process output and return collected stdout/stderr.

    Args:
        process: The subprocess.Popen process
        timeout: Maximum execution time in seconds
        start_time: When execution started (for timeout calculation)
        log_file: Optional file handle to write real-time logs to
        console_output: If True, print output to console in real-time

    Returns:
        Tuple of (stdout, stderr) as strings

    Raises:
        Exception: If timeout is exceeded, kills process and raises with partial output
    """

    # Set up output streaming
    output_queue = queue.Queue()
    lines = {"stdout": [], "stderr": []}
    threads = {}
    current_stream = None  # Track current section for log file

    # Create threads for each stream
    for stream_name, pipe in [("stdout", process.stdout), ("stderr", process.stderr)]:
        thread = threading.Thread(
            target=_stream_output, args=(pipe, output_queue, stream_name)
        )
        thread.daemon = True
        thread.start()
        threads[stream_name] = thread

    # Process output in real-time
    while process.poll() is None:
        # Check timeout
        current_time = time.time()
        if timeout and (current_time - start_time) > timeout:
            process.kill()

            # Collect any remaining output
            while not output_queue.empty():
                try:
                    stream_name, line = output_queue.get_nowait()
                    lines[stream_name].append(line)
                except queue.Empty:
                    break

            # Create exception with partial output
            collected_stdout = "".join(lines["stdout"])
            collected_stderr = "".join(lines["stderr"])

            raise ScaffoldTimeoutError(
                f"Execution timed out after {timeout} seconds",
                partial_stdout=collected_stdout,
                partial_stderr=collected_stderr,
            )

        # Get output with short timeout to avoid blocking
        new_stream = _process_output_from_queue(
            output_queue, lines, log_file, console_output, current_stream, timeout=0.1
        )
        if new_stream:
            current_stream = new_stream

    # Process any remaining output after process finishes
    while not output_queue.empty():
        new_stream = _process_output_from_queue(
            output_queue, lines, log_file, console_output, current_stream
        )
        if new_stream:
            current_stream = new_stream
        else:
            break

    # Wait for threads to finish
    for thread in threads.values():
        thread.join(timeout=1)

    # Return collected output
    stdout = "".join(lines["stdout"])
    stderr = "".join(lines["stderr"])

    return stdout, stderr


def execute_scaffold(
    scaffold_dir: Path,
    log_file_path: Path,
    input_string: str,
    model_spec: str,
    timeout: int = 120,
    console_output: bool = False,
) -> ScaffoldExecutionResult:
    """Execute a scaffold in a Docker container with the given input.

    Args:
        scaffold_dir: Path to the scaffold directory
        log_file_path: Path to the file to write logs to
        input_string: Input to pass to the scaffold's process_input function
        model_spec: Model spec for the executor LLM
        timeout: Maximum execution time in seconds
        console_output: If True, print output to console in real-time

    Returns:
        ScaffoldExecutionResult with output, stderr, exit code, and execution time
    """
    model_spec = LLMFactory.resolve_model_spec(model_spec)
    is_interactive = model_spec == "human/human"

    # Build Docker command
    docker_cmd = _build_docker_command(
        scaffold_dir=scaffold_dir,
        model_spec=model_spec,
        timeout=timeout,
        interactive=is_interactive,
    )

    # Generate Python script to run in container
    python_script = _generate_python_script(
        input_string=input_string,
        model_spec=model_spec,
    )

    # Add the Python script as the command to run
    docker_cmd.extend(["python", "-c", python_script])

    error_message = None
    stdout = ""
    stderr = ""

    # Execute the scaffold
    start_time = time.time()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Write to the log file with live streaming
    with open(log_file_path, "w") as log_file:
        # Write log header
        log_file.write("=== Scaffold Execution Log ===\n")
        log_file.write(f"Model: {model_spec}\n")
        log_file.write(f"Timestamp: {timestamp}\n")
        log_file.write("\n=== INPUT ===\n")
        log_file.write(input_string)
        log_file.write("\n")
        log_file.flush()

        try:
            if is_interactive:
                # Interactive mode for human model
                process = subprocess.run(docker_cmd, check=True)
                stdout = "Note: Human model execution - no output captured\nUser interaction occurred directly in terminal."
                stderr = ""
                _write_to_log_file(log_file, stdout, "stdout", current_stream=None)
                exit_code = process.returncode
            else:
                # Standard LLM mode with output streaming
                process = subprocess.Popen(
                    docker_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                    universal_newlines=True,
                )

                # Stream output and collect it
                stdout, stderr = _stream_process_output(
                    process, timeout, start_time, log_file, console_output
                )
                exit_code = process.returncode

            if exit_code != 0:
                error_message = (
                    f"Error from scaffold (exit code {exit_code}):\n{stderr}"
                )

        except ScaffoldTimeoutError as e:
            # Handle timeout case - collect any output that was captured
            stdout = e.partial_stdout
            stderr = e.partial_stderr
            error_message = str(e)
        except Exception as e:
            raise RuntimeError(f"Error from Docker when executing scaffold: {e}") from e

        # Write error message to log if there was one
        if error_message:
            log_file.write(f"\n=== ERROR ===\n{error_message}\n")

    end_time = time.time()
    execution_time = end_time - start_time

    return ScaffoldExecutionResult(
        output=stdout.strip() if stdout else "",
        stderr=stderr.strip() if stderr else "",
        error_message=error_message,
        execution_time=execution_time,
    )
