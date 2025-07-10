import os
import subprocess
import time
import json
from pathlib import Path
from datetime import datetime
from scaffold_learning.core.data_structures import ScaffoldExecutionResult
from scaffold_learning.core.experiment_files import ExperimentFileManager
from scaffold_learning.core.llm_interfaces import LLMFactory


def _build_docker_command(
    scaffold_dir: Path, logs_dir: Path, model_spec: str, timeout: int
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
            f"{scaffold_dir.absolute()}:/workspace/scaffold:ro",
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
            f"EXECUTOR_MODEL_SPEC={model_spec}",
            "-e",
            "LOG_LEVEL=INFO",
            "scaffold-runner",
        ]
    )

    return docker_cmd


def _generate_python_script(
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


def create_execution_log(
    input_string: str,
    model: str,
    timestamp: str,
    output: str = None,
    stderr: str = None,
    execution_time: float = None,
    error_message: str = None,
) -> str:
    """Create execution log content in a unified format."""
    log_content = "=== Scaffold Execution Log ===\n"
    log_content += f"Model: {model}\n"
    log_content += f"Timestamp: {timestamp}\n"
    if error_message:
        log_content += f"Error: {error_message}\n"
    log_content += f"Execution Time: {execution_time:.2f}s\n"
    log_content += "\n--- Input ---\n"
    log_content += input_string
    log_content += "\n\n--- Output ---\n"
    log_content += output or ""
    log_content += "\n\n--- Error Output ---\n"
    log_content += stderr or ""

    return log_content


def execute_scaffold(
    file_manager: ExperimentFileManager,
    scaffold_id: str,
    iteration: int,
    run_type: str,
    input_string: str,
    model_spec: str,
    timeout: int = 120,
) -> ScaffoldExecutionResult:
    """Execute a scaffold in a Docker container with the given input.

    Args:
        file_manager: ExperimentFileManager instance for path resolution
        scaffold_id: Scaffold identifier to execute
        iteration: Iteration number for logging
        run_type: Type of run (e.g., 'train', 'valid')
        input_string: Input to pass to the scaffold's process_input function
        model_spec: Model spec for the executor LLM
        timeout: Maximum execution time in seconds

    Returns:
        ScaffoldExecutionResult with output, stderr, exit code, and execution time
    """
    # Get scaffold directory for Docker mounting
    scaffold_dir = file_manager.get_docker_scaffold_dir(scaffold_id)
    logs_dir = file_manager.get_docker_logs_dir(iteration, scaffold_id)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    model_spec = LLMFactory.resolve_model_spec(model_spec)

    # Build Docker command
    docker_cmd = _build_docker_command(
        scaffold_dir=scaffold_dir,
        logs_dir=logs_dir,
        model_spec=model_spec,
        timeout=timeout,
    )

    # Generate Python script to run in container
    python_script = _generate_python_script(
        input_string=input_string, executor_model_spec=model_spec, timestamp=timestamp
    )

    # Add the Python script as the command to run
    docker_cmd.extend(["python", "-c", python_script])

    error_message = None

    # Execute the scaffold
    start_time = time.time()

    try:
        process = subprocess.Popen(
            docker_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )

        stdout, stderr = process.communicate(timeout=timeout)
        exit_code = process.returncode
        if exit_code != 0:
            error_message = f"Error from scaffold (exit code {exit_code}):\n{stderr}"

    except Exception as e:
        raise RuntimeError(f"Error from Docker when executing scaffold: {e}") from e

    end_time = time.time()
    execution_time = end_time - start_time

    # Save execution log through file manager
    log_content = create_execution_log(
        input_string=input_string,
        model=model_spec,
        timestamp=timestamp,
        output=stdout,
        stderr=stderr,
        execution_time=execution_time,
        error_message=error_message,
    )

    run_id = file_manager.save_execution_log(
        iteration=iteration,
        scaffold_id=scaffold_id,
        run_type=run_type,
        log_content=log_content,
    )

    return ScaffoldExecutionResult(
        output=stdout.strip() if stdout else "",
        stderr=stderr.strip() if stderr else "",
        error_message=error_message,
        execution_time=execution_time,
    )
