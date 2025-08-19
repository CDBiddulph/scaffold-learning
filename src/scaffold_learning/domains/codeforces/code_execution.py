"""Code execution module for CodeForces problems using Docker containers."""

import json
import os
import subprocess
import logging
from typing import List, Dict
import time


def _generate_test_runner_script(
    user_code: str,
    test_cases: List[Dict[str, str]],
    time_limit: float,
    memory_limit: float,
) -> str:
    """Generate Python script that runs user code against test cases.

    Args:
        user_code: The Python code submitted by the user
        test_cases: List of test case dictionaries with 'input' and 'output' keys
        time_limit: Time limit in seconds
        memory_limit: Memory limit in MB

    Returns:
        Python script as string
    """
    # Escape the user code and test cases for embedding in script
    escaped_user_code = json.dumps(user_code)
    escaped_test_cases = json.dumps(test_cases)

    return f"""
import json
import sys
import io
import signal
import resource
from contextlib import redirect_stdout, redirect_stderr


def _normalize_output(text: str) -> str:
    return text.replace('\\r\\n', '\\n').replace('\\r', '\\n')


# Set resource limits
try:
    # Memory limit in bytes (convert MB to bytes)
    memory_limit_bytes = int({memory_limit} * 1024 * 1024)
    resource.setrlimit(resource.RLIMIT_AS, (memory_limit_bytes, memory_limit_bytes))
except:
    pass  # Some systems don't support memory limits

# Timeout handler
def timeout_handler(signum, frame):
    raise TimeoutError("Code execution timed out")

# Set alarm for time limit
signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(int({time_limit}))

try:
    # Load user code and test cases
    user_code = {escaped_user_code}
    test_cases = {escaped_test_cases}
    
    # Compile user code
    try:
        compiled_code = compile(user_code, '<user_code>', 'exec')
    except SyntaxError as e:
        print(json.dumps({{"error": str(e)}}))
        sys.exit(0)
    
    # Track results
    results = []
    
    for i, test_case in enumerate(test_cases):
        test_input = test_case['input'].strip()
        expected_output = test_case['output'].strip()
        
        try:
            # Capture output
            output_buffer = io.StringIO()
            error_buffer = io.StringIO()
            
            # Mock input for the user code
            original_stdin = sys.stdin
            sys.stdin = io.StringIO(test_input)
            
            # Execute user code with output capture
            with redirect_stdout(output_buffer), redirect_stderr(error_buffer):
                # Create clean namespace for execution
                exec_globals = {{'__builtins__': __builtins__}}
                exec(compiled_code, exec_globals)
            
            # Restore stdin
            sys.stdin = original_stdin
            
            # Get output and compare
            actual_output = output_buffer.getvalue().strip()
            stderr_output = error_buffer.getvalue().strip()
            
            # Normalize line endings for comparison
            normalized_actual = _normalize_output(actual_output)
            normalized_expected = _normalize_output(expected_output)
            
            if stderr_output:
                results.append({{
                    "test_case": i,
                    "passed": False,
                    "error": stderr_output,
                    "input": test_input,
                    "expected": normalized_expected,
                    "actual": normalized_actual
                }})
            else:
                passed = normalized_actual == normalized_expected
                results.append({{
                    "test_case": i,
                    "passed": passed,
                    "input": test_input,
                    "expected": normalized_expected,
                    "actual": normalized_actual
                }})
            
        except Exception as e:
            results.append({{
                "test_case": i,
                "passed": False,
                "error": str(e),
                "input": test_input,
                "expected": expected_output
            }})
    
    # Print results as JSON
    print(json.dumps({{"results": results}}))
    
except Exception as e:
    print(json.dumps({{"error": str(e)}}))
    
finally:
    signal.alarm(0)  # Cancel alarm
"""


def execute_and_score_tests(
    user_code: str,
    test_cases: List[Dict[str, str]],
    time_limit: float = 2.0,
    memory_limit: float = 256.0,
) -> float:
    """Execute user code against test cases and return scoring results.

    Args:
        user_code: Python code to execute
        test_cases: List of test case dictionaries with 'input' and 'output' keys
        time_limit: Time limit in seconds
        memory_limit: Memory limit in MB

    Returns:
        Float representing proportion of tests passed (0.0 to 1.0)

    Raises:
        ValueError: If no test cases provided
        RuntimeError: If code execution fails
    """
    if not test_cases:
        raise ValueError("No test cases provided")

    # Generate the test runner script
    script = _generate_test_runner_script(
        user_code, test_cases, time_limit, memory_limit
    )

    # Build Docker command
    docker_timeout = int(time_limit * len(test_cases)) + 10
    docker_memory = f"{int(memory_limit * 2)}m"  # Double the limit for safety

    docker_cmd = [
        "docker",
        "run",
        "--rm",
        "--user",
        f"{os.getuid()}:{os.getgid()}",
        "--read-only",
        "--tmpfs",
        "/tmp:size=100M,noexec",
        "--memory",
        docker_memory,
        "--memory-swap",
        docker_memory,
        "--cpus",
        "1.0",
        "--pids-limit",
        "100",
        "--security-opt",
        "no-new-privileges",
        "--cap-drop",
        "ALL",
        "--network",
        "none",  # No network access for code execution
        "python:3.11-slim",
        "timeout",
        str(docker_timeout),
        "python",
        "-c",
        script,
    ]

    try:
        start_time = time.time()

        # Execute the Docker command
        process = subprocess.run(
            docker_cmd,
            capture_output=True,
            text=True,
            timeout=docker_timeout,
        )

        end_time = time.time()
        execution_time = end_time - start_time

        # Log execution details
        logging.info("=== CodeForces Code Execution ===")
        logging.info(f"Test cases: {len(test_cases)}")
        logging.info(f"Time limit: {time_limit}s")
        logging.info(f"Memory limit: {memory_limit}MB")
        logging.info("=== input code ===")
        logging.info(user_code)
        logging.info("=== stdout ===")
        logging.info(process.stdout)
        if process.stderr:
            logging.info("=== stderr ===")
            logging.info(process.stderr)
        logging.info(f"Execution time: {execution_time:.3f} seconds")

        # Handle different exit codes
        if process.returncode == 124:  # timeout command exit code
            raise RuntimeError(
                f"Code execution timed out after {docker_timeout} seconds"
            )
        elif process.returncode != 0:
            raise RuntimeError(
                f"Code execution failed (exit code {process.returncode}): {process.stderr}"
            )

        # Parse JSON output from the test runner
        try:
            output_json = json.loads(process.stdout.strip())
        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"Failed to parse execution output as JSON: {e}\nExecution output: {process.stdout}"
            )

        if "error" in output_json:
            # Syntax error case
            raise SyntaxError(f"Syntax error in user code: {output_json['error']}")

        if "results" in output_json:
            results = output_json["results"]
            total_tests = len(results)
            # Test passed if it has "passed": True
            passed_tests = sum(1 for r in results if r.get("passed", False))

            # Log test results
            logging.info(f"Test Results: {passed_tests}/{total_tests} passed")
            for i, test_result in enumerate(results):
                if test_result.get("passed", False):
                    logging.info(f"  Test {i+1}: PASSED")
                else:
                    logging.info(f"  Test {i+1}: FAILED")
                    if "error" in test_result:
                        logging.info(f"    Error: {test_result['error']}")
                    if "expected" in test_result and "actual" in test_result:
                        logging.info(f"    Expected: {repr(test_result['expected'])}")
                        logging.info(f"    Actual: {repr(test_result['actual'])}")

            # Return proportion of tests passed
            return passed_tests / total_tests if total_tests > 0 else 0.0

        # Unknown output format
        raise RuntimeError(f"Unexpected output format from test runner: {output_json}")

    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Docker execution timed out after {docker_timeout} seconds")
