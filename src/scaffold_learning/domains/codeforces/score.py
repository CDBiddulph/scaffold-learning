#!/usr/bin/env python
"""Score CodeForces solutions by executing code against test cases"""

import logging
from .code_execution import execute_and_score_tests
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
        Proportion of tests that passed (0.0 to 1.0)
    """
    try:
        attempted_code = extract_python_code(attempted_code)
    except ValueError:
        # Attempt to extract a code fence failed, so it might already be valid Python code.
        pass

    # Execute code against test cases and get results
    try:
        return execute_and_score_tests(
            user_code=attempted_code,
            test_cases=test_cases,
            time_limit=time_limit,
            memory_limit=memory_limit,
        )
    except Exception as e:
        logging.error(f"CodeForces scoring failed: {e}")
        return 0.0
