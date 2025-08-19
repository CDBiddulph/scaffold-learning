"""Code execution module for CodeForces problems using Docker containers."""

import json
import os
import subprocess
import logging
from typing import List, Dict, Any
import time

from scaffold_learning.core.data_structures import ScaffoldExecutionResult


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
import traceback
from contextlib import redirect_stdout, redirect_stderr

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
signal.alarm(int({time_limit}) + 1)  # Add 1 second buffer

try:
    # Load user code and test cases
    user_code = {escaped_user_code}
    test_cases = {escaped_test_cases}
    
    # Compile user code
    try:
        compiled_code = compile(user_code, '<user_code>', 'exec')
    except SyntaxError as e:
        print(json.dumps({{"status": "syntax_error", "error": str(e)}}))
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
            
            if stderr_output:
                results.append({{
                    "test_case": i,
                    "status": "runtime_error", 
                    "error": stderr_output,
                    "input": test_input,
                    "expected": expected_output,
                    "actual": actual_output
                }})
            elif actual_output == expected_output:
                results.append({{
                    "test_case": i,
                    "status": "passed",
                    "input": test_input,
                    "expected": expected_output,
                    "actual": actual_output
                }})
            else:
                results.append({{
                    "test_case": i,
                    "status": "wrong_answer",
                    "input": test_input,
                    "expected": expected_output,
                    "actual": actual_output
                }})
                
        except TimeoutError:
            results.append({{
                "test_case": i,
                "status": "timeout",
                "input": test_input,
                "expected": expected_output
            }})
            break  # Don't run remaining tests if one times out
            
        except Exception as e:
            results.append({{
                "test_case": i,
                "status": "runtime_error",
                "error": str(e),
                "traceback": traceback.format_exc(),
                "input": test_input,
                "expected": expected_output
            }})
    
    # Print results as JSON
    print(json.dumps({{"status": "completed", "results": results}}))
    
except Exception as e:
    print(json.dumps({{"status": "execution_error", "error": str(e), "traceback": traceback.format_exc()}}))
    
finally:
    signal.alarm(0)  # Cancel alarm
"""


def execute_code_against_tests(
    user_code: str,
    test_cases: List[Dict[str, str]],
    time_limit: float = 2.0,
    memory_limit: float = 256.0,
) -> ScaffoldExecutionResult:
    """Execute user code against test cases in a Docker container.

    Args:
        user_code: Python code to execute
        test_cases: List of test case dictionaries with 'input' and 'output' keys
        time_limit: Time limit in seconds
        memory_limit: Memory limit in MB

    Returns:
        ScaffoldExecutionResult with test execution results
    """
    if not test_cases:
        return ScaffoldExecutionResult(
            output="",
            stderr="",
            error_message="No test cases provided",
            execution_time=0.0,
        )

    # Generate the test runner script
    script = _generate_test_runner_script(
        user_code, test_cases, time_limit, memory_limit
    )

    # Build Docker command
    docker_timeout = (
        int(time_limit * len(test_cases)) + 30
    )  # Allow extra time for overhead
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
            timeout=docker_timeout + 10,  # Additional timeout buffer
        )

        end_time = time.time()
        execution_time = end_time - start_time

        logging.info("=== CodeForces Code Execution ===\n")
        logging.info(f"Test cases: {len(test_cases)}\n")
        logging.info(f"Time limit: {time_limit}s\n")
        logging.info(f"Memory limit: {memory_limit}MB\n\n")
        logging.info("=== INPUT CODE ===\n")
        logging.info(user_code)
        logging.info("\n\n=== STDOUT ===\n")
        logging.info(process.stdout)
        if process.stderr:
            logging.info("\n=== STDERR ===\n")
            logging.info(process.stderr)
        logging.info(f"\n\n=== EXECUTION TIME ===\n{execution_time:.3f} seconds\n")

        # Handle different exit codes
        if process.returncode == 124:  # timeout command exit code
            logging.error(f"Code execution timed out after {docker_timeout} seconds")
        elif process.returncode != 0:
            logging.error(
                f"Code execution failed (exit code {process.returncode}): {process.stderr}"
            )

        return process.stdout

    except subprocess.TimeoutExpired:
        return ScaffoldExecutionResult(
            output="",
            stderr="",
            error_message=f"Docker execution timed out after {docker_timeout + 10} seconds",
            execution_time=0.0,
        )
    except Exception as e:
        logging.error(f"Error executing code: {e}")
        return ScaffoldExecutionResult(
            output="",
            stderr=str(e),
            error_message=f"Code execution failed: {str(e)}",
            execution_time=0.0,
        )


def parse_test_results(execution_output: str) -> Dict[str, Any]:
    """Parse the JSON output from code execution to extract test results.

    Args:
        execution_output: Output from execute_code_against_tests

    Returns:
        Dictionary with parsed test results
    """
    try:
        # Parse JSON output from the test runner
        output_json = json.loads(execution_output.strip())

        if output_json["status"] == "syntax_error":
            return {
                "status": "syntax_error",
                "error": output_json["error"],
                "passed": False,
                "total_tests": 0,
                "passed_tests": 0,
            }

        if output_json["status"] == "execution_error":
            return {
                "status": "execution_error",
                "error": output_json["error"],
                "passed": False,
                "total_tests": 0,
                "passed_tests": 0,
            }

        if output_json["status"] == "completed":
            results = output_json["results"]
            total_tests = len(results)
            passed_tests = sum(1 for r in results if r["status"] == "passed")

            # All tests must pass for the solution to be considered correct
            all_passed = passed_tests == total_tests

            return {
                "status": "completed",
                "passed": all_passed,
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "results": results,
            }

        return {
            "status": "unknown_error",
            "error": f"Unknown status: {output_json.get('status', 'missing')}",
            "passed": False,
            "total_tests": 0,
            "passed_tests": 0,
        }

    except json.JSONDecodeError as e:
        return {
            "status": "parse_error",
            "error": f"Failed to parse execution output as JSON: {e}",
            "raw_output": execution_output,
            "passed": False,
            "total_tests": 0,
            "passed_tests": 0,
        }
    except Exception as e:
        return {
            "status": "parse_error",
            "error": f"Error parsing results: {e}",
            "passed": False,
            "total_tests": 0,
            "passed_tests": 0,
        }
