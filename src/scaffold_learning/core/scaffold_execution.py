import os
import subprocess
import time
import json
from pathlib import Path
from datetime import datetime
from scaffold_learning.core.data_structures import ScaffoldExecutionResult


def build_docker_command(
    scaffold_dir: Path, logs_dir: Path, executor_model_spec: str, timeout: int
) -> list[str]:
    """Build the Docker command with all necessary flags and environment variables."""
    docker_cmd = ["docker", "run", "--rm"]

    # Add timeout
    docker_cmd.extend(["--stop-timeout", str(timeout)])

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

    # Add environment variables for API keys
    for key in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY"]:
        if key in os.environ:
            docker_cmd.extend(["-e", f"{key}={os.environ[key]}"])

    docker_cmd.extend(
        [
            "-e",
            f"EXECUTOR_MODEL_SPEC={executor_model_spec}",
            "-e",
            "LOG_LEVEL=INFO",
            "scaffold-runner",
        ]
    )

    return docker_cmd


def generate_python_script(
    input_string: str,
    executor_model_spec: str,
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
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
)

# Use properly escaped input string
input_string = {escaped_input}

logging.info('Running scaffold execution')
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
        'timestamp': datetime.now().isoformat(),
        'input': input_string,
        'result': result,
        'executor_model_spec': '{executor_model_spec}',
    }}
    
    with open('/workspace/logs/{timestamp}.json', 'w') as f:
        json.dump(log_data, f, indent=2)
        
except Exception as e:
    logging.error(f'Error occurred: {{str(e)}}', exc_info=True)
    sys.exit(1)
"""


def save_execution_log(
    logs_path: Path,
    input_string: str,
    model: str,
    timestamp: str,
    output: str = None,
    stderr: str = None,
    exit_code: int = None,
    execution_time: float = None,
    error_message: str = None,
) -> None:
    """Save execution log in a unified format."""
    logs_path.parent.mkdir(parents=True, exist_ok=True)

    with open(logs_path, "w") as f:
        f.write("=== Scaffold Execution Log ===\\n")
        f.write(f"Model: {model}\\n")
        f.write(f"Timestamp: {timestamp}\\n")
        if error_message:
            f.write(f"Error: {error_message}\\n")
        f.write(f"Exit Code: {exit_code}\\n")
        f.write(f"Execution Time: {execution_time:.2f}s\\n")
        f.write("\\n--- Input ---\\n")
        f.write(input_string)
        f.write("\\n\\n--- Output ---\\n")
        f.write(output or "")
        f.write("\\n\\n--- Error Output ---\\n")
        f.write(stderr or "")


def execute_scaffold(
    scaffold_dir: Path,
    input_string: str,
    model: str,
    logs_path: Path,
    timeout: int = 120,  # TODO: make this configurable
) -> ScaffoldExecutionResult:
    """Execute a scaffold in a Docker container with the given input.

    Args:
        scaffold_dir: Path to directory containing scaffold.py and related files
        input_string: Input to pass to the scaffold's process_input function
        model: Model name for the executor LLM
        logs_path: Path where execution logs should be saved
        timeout: Maximum execution time in seconds

    Returns:
        ScaffoldExecutionResult with output, stderr, exit code, and execution time
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Build Docker command
    docker_cmd = build_docker_command(
        scaffold_dir=scaffold_dir,
        logs_dir=logs_path.parent,
        executor_model_spec=model,
        timeout=timeout,
    )

    # Generate Python script to run in container
    python_script = generate_python_script(
        input_string=input_string, executor_model_spec=model, timestamp=timestamp
    )

    # Add the Python script as the command to run
    docker_cmd.extend(["python", "-c", python_script])

    # Execute the scaffold
    start_time = time.time()

    try:
        process = subprocess.Popen(
            docker_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )

        stdout, stderr = process.communicate(timeout=timeout)
        exit_code = process.returncode

    except subprocess.TimeoutExpired:
        process.kill()
        stdout, stderr = process.communicate()
        exit_code = 124  # Standard timeout exit code
        stderr = stderr + "\\nProcess killed due to timeout"
    except Exception as e:
        stdout = ""
        stderr = f"Execution error: {str(e)}"
        exit_code = 1

    end_time = time.time()
    execution_time = end_time - start_time

    # Save execution log
    save_execution_log(
        logs_path=logs_path,
        input_string=input_string,
        model=model,
        timestamp=timestamp,
        output=stdout,
        stderr=stderr,
        exit_code=exit_code,
        execution_time=execution_time,
    )

    return ScaffoldExecutionResult(
        output=stdout.strip() if stdout else "",
        stderr=stderr.strip() if stderr else "",
        exit_code=exit_code,
        execution_time=execution_time,
    )
