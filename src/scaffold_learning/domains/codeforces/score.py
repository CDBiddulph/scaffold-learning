#!/usr/bin/env python
"""Score CodeForces solutions by executing code against test cases"""

import argparse
import json
import logging
from pathlib import Path
from typing import Dict, Any

from .code_execution import execute_code_against_tests, parse_test_results
from scaffold_learning.core.llm_response_utils import extract_python_code


def score(
    test_cases: list,
    time_limit: float,
    memory_limit: float,
    attempted_code: str,
) -> float:
    """
    Score a CodeForces solution by executing it against test cases.

    Args:
        test_cases: List of test case dictionaries with 'input' and 'output' keys
        time_limit: Time limit in seconds
        memory_limit: Memory limit in MB
        attempted_code: The Python code to test

    Returns:
        1.0 if all tests pass, 0.0 otherwise
    """
    try:
        attempted_code = extract_python_code(attempted_code)
    except ValueError:
        # Attempt to extract a code fence failed, so it might already be valid Python code.
        pass

    # Execute code against test cases
    execution_result = execute_code_against_tests(
        user_code=attempted_code,
        test_cases=test_cases,
        time_limit=time_limit,
        memory_limit=memory_limit,
    )

    # Parse results
    results = parse_test_results(execution_result)

    # Return 1.0 only if all tests passed, 0.0 otherwise
    return 1.0 if results["passed"] else 0.0


def _load_expected_data(file_path: str, problem_id: str) -> Dict[str, Any]:
    """
    Load expected test data from JSONL file for a specific problem.

    Args:
        file_path: Path to the JSONL file
        problem_id: ID of the problem to find

    Returns:
        Dictionary with scoring data
    """
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            data = json.loads(line.strip())
            if data.get("id") == problem_id:
                return data["scoring_data"]

    raise ValueError(f"Problem '{problem_id}' not found in JSONL file")


def main():
    """Command line interface for scoring CodeForces solutions"""
    parser = argparse.ArgumentParser(
        description="Score a CodeForces solution against test cases",
    )

    parser.add_argument("expected_file", help="JSONL file with expected test data")
    parser.add_argument(
        "attempted_code_file", help="File containing the Python code to test"
    )
    parser.add_argument(
        "--problem",
        "-p",
        required=True,
        help="Problem ID to score",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed test results",
    )

    args = parser.parse_args()

    # Set up logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    # Load expected data
    scoring_data = _load_expected_data(args.expected_file, args.problem)

    test_cases = scoring_data["held_out_tests"]
    time_limit = scoring_data.get("time_limit", 2.0)
    memory_limit = scoring_data.get("memory_limit", 256.0)

    # Load attempted code
    with open(args.attempted_code_file, "r", encoding="utf-8") as f:
        attempted_code = f.read()

    # Score the solution
    if args.verbose:
        logging.info(f"Testing problem {args.problem}")
        logging.info(f"Time limit: {time_limit}s, Memory limit: {memory_limit}MB")
        logging.info(f"Running {len(test_cases)} test cases...")

    # Execute and get detailed results for verbose output
    if args.verbose:
        execution_result = execute_code_against_tests(
            user_code=attempted_code,
            test_cases=test_cases,
            time_limit=time_limit,
            memory_limit=memory_limit,
        )

        results = parse_test_results(execution_result)

        logging.info(f"Status: {results['status']}")
        logging.info(
            f"Passed: {results['passed_tests']}/{results['total_tests']} tests"
        )

        if "results" in results:
            for i, test_result in enumerate(results["results"]):
                status = test_result["status"]
                if status == "passed":
                    logging.info(f"  Test {i+1}: PASSED")
                else:
                    logging.info(f"  Test {i+1}: FAILED ({status})")
                    if "error" in test_result:
                        logging.info(f"    Error: {test_result['error']}")
                    elif status == "wrong_answer":
                        logging.info(f"    Expected: {repr(test_result['expected'])}")
                        logging.info(f"    Actual: {repr(test_result['actual'])}")

        score_value = 1.0 if results["passed"] else 0.0
    else:
        score_value = score(test_cases, time_limit, memory_limit, attempted_code)

    print(f"Score: {score_value:.1f}")


if __name__ == "__main__":
    main()
