#!/usr/bin/env python3

import argparse
import json
import random
import subprocess
import sys
import tempfile
from typing import Optional, Any, Dict

from scaffold_learning.core.domain_params import parse_domain_params
from scaffold_learning.core.scoring_utils import create_scoring_function


JSON_SEPARATOR_LINE = "=== EDIT SCORING DATA BELOW (JSON FORMAT) ==="
RESPONSE_SEPARATOR_LINE = "=== SUBMIT YOUR ANSWER BELOW THIS LINE ==="


def load_example(jsonl_path: str, example_id: Optional[str] = None) -> dict:
    """Load a specific example from a JSONL file.

    Args:
        jsonl_path: Path to the JSONL file
        example_id: ID of the example to load, or None to pick randomly

    Returns:
        The example dict from the JSONL file

    Raises:
        ValueError: If example_id not found in file or file is empty
    """
    examples = []
    with open(jsonl_path, "r") as f:
        for line in f:
            example = json.loads(line.strip())
            examples.append(example)
            if example_id and example.get("id") == example_id:
                return example

    if example_id:
        raise ValueError(f"Example with id '{example_id}' not found in {jsonl_path}")

    if not examples:
        raise ValueError(f"No examples found in {jsonl_path}")

    chosen = random.choice(examples)
    print(f"Randomly selected example: {chosen['id']}")
    print(f"Input: {chosen['input']}")
    print(f"Scoring data: {chosen['scoring_data']}")
    return chosen


def flatten_dict(d: Dict[str, Any], parent_key: str = "") -> Dict[str, Any]:
    """Flatten nested dictionary using dot notation."""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}.{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key).items())
        else:
            items.append((new_key, v))
    return dict(items)


def format_prompt(example: dict) -> str:
    """Format the example data into a readable prompt.

    Shows field names and values in a readable format.
    Flattens nested fields using dot notation (e.g., scoring_data.solution).

    Args:
        example: The example dict loaded from JSONL

    Returns:
        Formatted string with fields and separator line
    """
    flattened = flatten_dict(example)
    lines = []

    for key, value in flattened.items():
        lines.append(f"{key}: {value}")

    lines.append("")
    lines.append(JSON_SEPARATOR_LINE)
    lines.append(json.dumps(example["scoring_data"], indent=2))
    lines.append("")
    lines.append(RESPONSE_SEPARATOR_LINE)
    lines.append("")

    return "\n".join(lines)


def extract_answer(content: str) -> str:
    """Extract the answer portion from the vim buffer content.

    Finds the response separator line and returns everything below it, stripped.

    Args:
        content: Full vim buffer content

    Returns:
        The user's answer (text below response separator line)
    """
    if RESPONSE_SEPARATOR_LINE not in content:
        return ""

    parts = content.split(RESPONSE_SEPARATOR_LINE)
    if len(parts) < 2:
        return ""

    return parts[1].strip()


def extract_scoring_data(content: str) -> dict:
    """Extract the scoring data JSON from the vim buffer content.

    Args:
        content: Full vim buffer content

    Returns:
        Parsed JSON scoring data, or empty dict if not found/invalid
    """
    if JSON_SEPARATOR_LINE not in content:
        return {}

    # Get content after JSON separator but before response separator
    parts = content.split(JSON_SEPARATOR_LINE)
    if len(parts) < 2:
        return {}

    json_section = parts[1]
    if RESPONSE_SEPARATOR_LINE in json_section:
        json_section = json_section.split(RESPONSE_SEPARATOR_LINE)[0]

    json_section = json_section.strip()
    if not json_section:
        return {}

    try:
        return json.loads(json_section)
    except json.JSONDecodeError:
        return {}


def compare_scoring_data(original: dict, modified: dict) -> None:
    """Compare scoring data and print modifications.

    Args:
        original: Original scoring data from example
        modified: Modified scoring data from user
    """
    flattened_original = flatten_dict(original, "scoring_data")
    flattened_modified = flatten_dict(modified, "scoring_data")

    for key, value in flattened_modified.items():
        if key not in flattened_original or flattened_original[key] != value:
            print(f'Modified {key}: "{value}"')

    # Check for removed keys
    for key in flattened_original:
        if key not in flattened_modified:
            print(f"Removed {key}")


def get_final_scoring_data(original: dict, user_json: dict) -> dict:
    """Get final scoring data by merging original with user modifications.

    Args:
        original: Original scoring data from example
        user_json: User's JSON modifications

    Returns:
        Final scoring data to use
    """
    if not user_json:
        return original

    # Deep copy original and update with user changes
    import copy

    final = copy.deepcopy(original)
    final.update(user_json)
    return final


def edit_in_vim(content: str) -> str:
    """Open vim with the given content and return the edited result.

    Args:
        content: Initial content for the vim buffer

    Returns:
        The edited content after user saves and exits vim
    """
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".txt", delete=False) as f:
        temp_path = f.name
        f.write(content)

    subprocess.run(["vim", temp_path])

    with open(temp_path, "r") as f:
        result = f.read()

    return result


def run_scoring_loop(example: dict, scoring_fn) -> None:
    """Run the interactive vim editing and scoring loop.

    Opens vim with the formatted prompt, gets user input, scores it,
    displays results, and asks whether to continue.

    Args:
        example: The example dict loaded from JSONL
        scoring_fn: Scoring function for the domain
    """
    original_scoring_data = example["scoring_data"]
    prompt = format_prompt(example)
    current_content = prompt

    while True:
        current_content = edit_in_vim(current_content)
        answer = extract_answer(current_content)
        user_scoring_json = extract_scoring_data(current_content)
        final_scoring_data = get_final_scoring_data(
            original_scoring_data, user_scoring_json
        )

        # Show modifications
        if user_scoring_json:
            compare_scoring_data(original_scoring_data, final_scoring_data)

        if not answer:
            print("No answer provided.")
        else:
            score = scoring_fn(answer, final_scoring_data)
            print(f"\nAnswer: {answer}")
            print(f"Score: {score:.3f}")

        response = input("\nPress Enter to continue editing, or 'q' to quit: ")
        print("\033[1A\033[K", end="")  # Move cursor up and clear line
        if response.lower() == "q":
            break


def main() -> None:
    """Entry point for the try-scoring CLI tool.

    Parses command line arguments and runs the interactive scoring loop.

    Raises:
        ValueError: If domain is not recognized or example ID not found
    """
    parser = argparse.ArgumentParser(
        description="Iteratively test scoring functions on domain examples"
    )
    parser.add_argument("jsonl_path", help="Path to the JSONL data file")
    parser.add_argument(
        "example_id", nargs="?", help="ID of the example to test (omit for random)"
    )
    parser.add_argument(
        "--domain", required=True, help="Domain name (e.g., crosswords)"
    )
    parser.add_argument(
        "--domain-param", action="append", help="Domain parameter (key=value)"
    )

    args = parser.parse_args()

    # Parse domain parameters
    domain_params = parse_domain_params(args.domain_param or [])

    # Create scoring function
    scoring_fn = create_scoring_function(args.domain, domain_params=domain_params)

    # Load example
    example = load_example(args.jsonl_path, args.example_id)

    # Run scoring loop
    run_scoring_loop(example, scoring_fn)


if __name__ == "__main__":
    main()
