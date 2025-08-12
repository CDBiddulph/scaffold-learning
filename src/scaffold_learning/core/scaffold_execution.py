import os
import subprocess
import sys
import time
import json
import threading
import queue
import logging
import concurrent.futures
import os
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Optional, TextIO, List, Dict, Any, Callable, Union, Tuple
from concurrent.futures import Future
from scaffold_learning.core.data_structures import (
    ScaffoldExecutionResult,
    ScaffoldExecutionTask,
)
from scaffold_learning.core.llm_interfaces import LLMFactory


def _build_docker_command(
    scaffold_dir: Path,
    model_spec: str,
    timeout: int,
    python_script: str,
    interactive: bool = False,
    thinking_budget_tokens: int = 0,
    results_dir: Optional[Path] = None,
) -> list[str]:
    """Build the Docker command with all necessary flags and environment variables."""
    docker_cmd = ["docker", "run", "--rm"]

    # Add interactive flags for human model
    if interactive:
        docker_cmd.extend(["-it"])

    # Security constraints for untrusted code execution
    docker_cmd.extend(
        [
            # User and filesystem
            "--user",
            f"{os.getuid()}:{os.getgid()}",
            "-v",
            f"{scaffold_dir.absolute()}:/workspace/scaffold:ro",
        ]
    )

    # Mount scaffold_tools.py for meta-optimize domain
    scaffold_tools_path = Path(__file__).parent.parent / "runtime" / "scaffold_tools.py"
    if scaffold_tools_path.exists():
        docker_cmd.extend(
            ["-v", f"{scaffold_tools_path.absolute()}:/tmp/scaffold_tools.py:ro"]
        )

    # Add results directory mount if provided
    if results_dir:
        docker_cmd.extend(["-v", f"{results_dir.absolute()}:/workspace/results:rw"])

    docker_cmd.extend(
        [
            "--read-only",
            "--tmpfs",
            "/tmp:size=100M,noexec",
            # Resource limits
            "--memory",
            "1G",
            "--memory-swap",
            "1G",
            "--cpus",
            "1.0",
            "--pids-limit",
            "100",
            # Security options
            "--security-opt",
            "no-new-privileges",
            "--cap-drop",
            "ALL",
            # TODO: Add network isolation without restricting calls to LLM APIs
            # TODO: consider uncommenting if we need to write the result as a txt file
            # "-v",
            # f"{logs_dir.absolute()}:/workspace/logs",
        ]
    )

    # Add environment variables from .env file if it exists
    env_file = Path(".env")
    if env_file.exists():
        docker_cmd.extend(["--env-file", str(env_file.absolute())])

    # Add environment variables for API keys and other settings
    env_vars = []
    for key in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY"]:
        if key in os.environ:
            env_vars.append(f"{key}={os.environ[key]}")

    # Get primary host IP for scaffold_tools server connectivity
    result = subprocess.run(
        ["hostname", "-I"], capture_output=True, text=True, timeout=5
    )
    if result.returncode != 0:
        raise RuntimeError(f"Failed to get host IP: {result.stderr.strip()}")
    host_ip = result.stdout.strip().split()[0]

    env_vars.extend(
        [
            f"EXECUTOR_MODEL_SPEC={model_spec}",
            f"THINKING_BUDGET_TOKENS={thinking_budget_tokens}",
            f"HOST_IP={host_ip}",
            "LOG_LEVEL=DEBUG",
        ]
    )
    for key in env_vars:
        docker_cmd.extend(["-e", key])

    docker_cmd.append("scaffold-runner")

    # Build the Linux command that runs in Docker

    # Add timeout if needed. The container itself will enforce the time limit.
    if timeout and not interactive:
        docker_cmd.extend(["timeout", str(timeout)])

    # Add the Python script as the command to run
    docker_cmd.extend(["python", "-c", python_script])

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
import time
from datetime import datetime

# Configure logging
log_level = getattr(logging, os.environ.get('LOG_LEVEL', 'INFO').upper(), logging.INFO)
logging.basicConfig(
    level=log_level,
    format='%(asctime)s [%(levelname)s] %(message)s',
)

# Use properly escaped input string
input_string = {escaped_input}

try:
    # Add paths for imports
    sys.path.insert(0, '/workspace/scaffold')
    # Add /tmp to path for scaffold_tools.py (meta-optimize domain)
    if os.path.exists('/tmp/scaffold_tools.py'):
        sys.path.insert(0, '/tmp')
    
    # Import scaffold and logging utilities
    from scaffold import process_input
    from scaffold_learning.core.logging_utils import suppress_all_except_root
    
    # Suppress a specific noisy logger at the library level.
    # It wasn't covered by suppress_all_except_root for some reason.
    for logger_name in ['httpcore']:
        logging.getLogger(logger_name).setLevel(logging.WARNING)
    
    # Suppress all logging except from root logger
    with suppress_all_except_root():
        # Measure execution time inside container (excluding Docker overhead)
        start_time = time.time()
        result = process_input(input_string)
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Save results to file for clean parsing
        results_data = {{
            "output": result,
            "execution_time": execution_time
        }}
        with open('/workspace/results/results.json', 'w') as f:
            json.dump(results_data, f)
        
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
        message = f"Error reading from {stream_name} stream: {e}"
        logging.error(message)
        output_queue.put((stream_name, message))


def _stream_process_output(
    process: subprocess.Popen,
    log_file: Optional[TextIO],
    console_output: bool,
    timeout: Optional[int] = None,
) -> tuple[str, str]:
    """Stream process output and return collected stdout/stderr.

    Args:
        process: The subprocess.Popen process
        log_file: Optional file handle to write real-time logs to
        console_output: If True, print output to console in real-time
        timeout: Maximum time in seconds to wait for process completion

    Returns:
        Tuple of (stdout, stderr) as strings
    """

    # Set up output streaming
    output_queue = queue.Queue()
    lines = {"stdout": [], "stderr": []}
    threads = {}
    current_stream = None  # Track current section for log file
    start_time = time.time()

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
        # Check for timeout
        if timeout and (time.time() - start_time) > timeout:
            logging.warning(
                f"Process exceeded timeout of {timeout} seconds, terminating..."
            )
            process.terminate()
            # Give it a chance to terminate gracefully
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logging.warning("Process did not terminate gracefully, killing...")
                process.kill()
                process.wait()
            break

        # Get output with short timeout to avoid blocking
        new_stream = _process_output_from_queue(
            output_queue, lines, log_file, console_output, current_stream, timeout=0.1
        )
        if new_stream:
            current_stream = new_stream

    # Process any remaining output after process finishes
    # Use a timeout to prevent hanging if queue operations fail
    timeout_count = 0
    max_timeout_attempts = 10
    while not output_queue.empty() and timeout_count < max_timeout_attempts:
        new_stream = _process_output_from_queue(
            output_queue, lines, log_file, console_output, current_stream, timeout=0.1
        )
        if new_stream:
            current_stream = new_stream
            timeout_count = 0  # Reset counter on successful read
        else:
            timeout_count += 1
    if not output_queue.empty():
        logging.warning("Failed to read all output from the queue")

    # Force close pipes to ensure threads can exit
    for pipe in [process.stdout, process.stderr]:
        if pipe:
            pipe.close()

    # Wait for threads to finish
    for stream_name, thread in threads.items():
        thread.join(timeout=1)
        if thread.is_alive():
            logging.warning(
                f"Thread for {stream_name} did not terminate after 1 second timeout"
            )

    # Return collected output
    stdout = "".join(lines["stdout"])
    stderr = "".join(lines["stderr"])

    return stdout, stderr


def _execute_scaffold(
    scaffold_dir: Path,
    log_file_path: Path,
    input_string: str,
    model_spec: str,
    timeout: int = 120,
    console_output: bool = False,
    thinking_budget_tokens: int = 0,
) -> ScaffoldExecutionResult:
    """Execute a scaffold in a Docker container with the given input.

    Args:
        scaffold_dir: Path to the scaffold directory
        log_file_path: Path to the file to write logs to
        input_string: Input to pass to the scaffold's process_input function
        model_spec: Model spec for the executor LLM
        timeout: Maximum execution time in seconds
        console_output: If True, print output to console in real-time
        thinking_budget_tokens: Budget for thinking tokens

    Returns:
        ScaffoldExecutionResult with output, stderr, exit code, and execution time
    """
    model_spec = LLMFactory.resolve_model_spec(model_spec)
    is_interactive = model_spec == "human/human"

    # Generate Python script to run in container
    python_script = _generate_python_script(
        input_string=input_string,
        model_spec=model_spec,
    )

    # Create temporary directory for results
    results_dir = None
    if not is_interactive:
        results_dir = Path(tempfile.mkdtemp())
        # Ensure the directory is writable by Docker
        os.chmod(results_dir, 0o777)

    # Build Docker command
    docker_cmd = _build_docker_command(
        scaffold_dir=scaffold_dir,
        model_spec=model_spec,
        timeout=timeout,
        python_script=python_script,
        interactive=is_interactive,
        thinking_budget_tokens=thinking_budget_tokens,
        results_dir=results_dir,
    )

    error_message = None
    stdout = ""
    stderr = ""

    # Execute the scaffold
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
                    process,
                    log_file=log_file,
                    console_output=console_output,
                    timeout=timeout,
                )
                exit_code = process.returncode

            # Check for timeout (exit code 124 from timeout command)
            if exit_code == 124:
                error_message = f"Execution timed out after {timeout} seconds"
            elif exit_code != 0:
                error_message = (
                    f"Error from scaffold (exit code {exit_code}):\n{stderr}"
                )

        except Exception as e:
            raise RuntimeError(f"Error from Docker when executing scaffold: {e}") from e

        # Write error message to log if there was one
        if error_message:
            log_file.write(f"\n=== ERROR ===\n{error_message}\n")

    # Read results from file (for non-interactive mode)
    execution_time = 0.0
    final_output = stdout.strip() if stdout else ""
    warning_message = None

    if results_dir and not error_message:
        results_file = results_dir / "results.json"
        try:
            with open(results_file, "r") as f:
                results_data = json.load(f)
                final_output = results_data["output"]
                execution_time = results_data["execution_time"]
        except Exception as e:
            # If we can't read results, fall back to stdout and log warning
            warning_message = f"Failed to read results file: {e}"

    # Write clean output and timing to log file
    with open(log_file_path, "a") as log_file:
        if warning_message:
            log_file.write(f"\n=== WARNING ===\n{warning_message}\n")
        if final_output:
            log_file.write(f"\n=== OUTPUT ===\n{final_output}\n")
        if execution_time > 0:
            log_file.write(f"\n=== EXECUTION TIME ===\n{execution_time:.3f} seconds\n")

    return ScaffoldExecutionResult(
        output=final_output,
        stderr=stderr.strip() if stderr else "",
        error_message=error_message,
        execution_time=execution_time,
    )


def _execute_single_task(task: ScaffoldExecutionTask) -> ScaffoldExecutionResult:
    """Execute a single scaffold task and return result.

    Args:
        task: ScaffoldExecutionTask to execute

    Returns:
        ScaffoldExecutionResult with execution output and metadata
    """
    try:
        result = _execute_scaffold(
            scaffold_dir=Path(task.scaffold_dir),
            log_file_path=Path(task.log_file_path),
            input_string=task.input_string,
            model_spec=task.model_spec,
            timeout=task.timeout,
            console_output=task.console_output,
            thinking_budget_tokens=task.thinking_budget_tokens,
        )
        return result
    except Exception as e:
        # Create an error result instead of raising
        return ScaffoldExecutionResult(
            output="",
            stderr=str(e),
            error_message=f"Execution failed: {str(e)}",
            execution_time=0.0,
        )


def _collect_results_with_progress(
    futures: List[Future[ScaffoldExecutionResult]],
    total_tasks: int,
    max_workers: int,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> List[ScaffoldExecutionResult]:
    """Collect results from futures with progress tracking and error handling.

    Args:
        futures: List of futures to collect results from
        total_tasks: Total number of tasks for progress tracking
        max_workers: Number of parallel workers for logging decisions
        progress_callback: Optional callback for progress updates

    Returns:
        List of ScaffoldExecutionResult objects in order
    """
    results = []
    errors = []
    completed = 0

    # Process futures in order to maintain result order
    for i, future in enumerate(futures):
        try:
            result = future.result()
            results.append(result)
            completed += 1

            # Call progress callback if provided
            if progress_callback:
                progress_callback(completed, total_tasks)

            # Log progress for parallel execution
            if max_workers > 1 and completed % 10 == 0:
                logging.info(
                    f"Completed scaffold execution ({completed}/{total_tasks})"
                )

            # Track errors but don't stop execution
            if result.error_message:
                errors.append((i, result.error_message))

        except Exception as e:
            error_msg = f"Task {i} failed with exception: {str(e)}"
            logging.error(error_msg)
            errors.append((i, error_msg))
            # Still need to put something in results to maintain order
            results.append(
                ScaffoldExecutionResult(
                    output="",
                    stderr=str(e),
                    error_message=error_msg,
                    execution_time=0.0,
                )
            )
            completed += 1
            if progress_callback:
                progress_callback(completed, total_tasks)

    # Log summary of errors if any occurred
    _log_execution_errors(errors, total_tasks)

    return results


def _log_execution_errors(errors: List[Tuple[int, str]], total_tasks: int) -> None:
    """Log summary of execution errors.

    Args:
        errors: List of (task_index, error_message) tuples
        total_tasks: Total number of tasks executed
    """
    if not errors:
        return

    logging.warning(f"Completed with {len(errors)} errors out of {total_tasks} tasks")
    for index, error in errors[:5]:  # Show first 5 errors
        logging.warning(f"  Task {index}: {error}")
    if len(errors) > 5:
        logging.warning(f"  ... and {len(errors) - 5} more errors")


def execute_scaffolds(
    tasks: List[ScaffoldExecutionTask],
    max_workers: int = 1,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> List[ScaffoldExecutionResult]:
    """Execute multiple scaffold tasks using ThreadPoolExecutor.

    Args:
        tasks: List of ScaffoldExecutionTask objects
        max_workers: Maximum number of parallel executions (default 1 for sequential)
        progress_callback: Optional callback function that receives (completed_count, total_count)

    Returns:
        List of ScaffoldExecutionResult objects in order
    """
    total_tasks = len(tasks)

    # Log execution mode
    if max_workers > 1:
        logging.info(
            f"Executing {total_tasks} scaffolds (up to {max_workers} in parallel)"
        )
    else:
        logging.info(f"Executing {total_tasks} scaffolds sequentially")

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        futures = [executor.submit(_execute_single_task, task) for task in tasks]

        # Wait for all futures and collect results
        return _collect_results_with_progress(
            futures, total_tasks, max_workers, progress_callback
        )
