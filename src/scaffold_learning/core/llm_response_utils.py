"""Utilities for parsing LLM responses."""

import json
import re
from typing import Any, Dict


def extract_python_code(response: str) -> str:
    """Extract Python code block from an LLM response.

    Args:
        response: Raw LLM response text that may contain markdown formatting

    Returns:
        Extracted Python code

    Raises:
        ValueError: If no Python code block is found
    """
    # Regex to match code block like ```python\n...\n``` or ```\n...\n```
    pattern = re.compile(r"```(?:python)?\n(.*?)(?=\n```)", re.DOTALL | re.IGNORECASE)

    matches = pattern.findall(response)
    if not matches:
        raise ValueError(
            f"LLM response doesn't contain a valid Python code block:\n{response}"
        )
    elif len(matches) > 1:
        import logging

        logging.warning(f"LLM response contains multiple Python code blocks: {matches}")

    return matches[-1]


def extract_json_dict(response: str) -> Dict[str, Any]:
    """Extract JSON dictionary from LLM response text.

    Args:
        response: Raw LLM response text that contains a JSON dictionary

    Returns:
        Parsed dictionary from the JSON

    Raises:
        ValueError: If no valid JSON dictionary is found
    """
    # Try to extract JSON from the response
    # Look for JSON object pattern
    json_match = re.search(r'\{[^{}]*"[^"]+"\s*:\s*[^{}]+.*\}', response, re.DOTALL)

    if not json_match:
        raise ValueError(f"No valid JSON dictionary found in response:\n{response}")

    try:
        result = json.loads(json_match.group())
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON dictionary: {e}\nResponse:\n{response}")

    if not isinstance(result, dict):
        raise ValueError(f"JSON is not a dictionary:\n{result}")

    return result
