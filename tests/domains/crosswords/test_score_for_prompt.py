"""Validates that score_lenient.py and score_strict.py are simple modifications of score.py."""

import re


def transform_score_for_mode(content, mode):
    """
    Transform score.py content to match either score_lenient.py or score_strict.py.

    Args:
        content: String content of score.py
        mode: Either "lenient" or "strict"

    Returns:
        str: Transformed content that should match the target file
    """
    if mode not in ["lenient", "strict"]:
        raise ValueError(f"Invalid mode: {mode}")

    # Step 1: Delete everything up until imports
    lines = content.split("\n")
    import_start = None
    for i, line in enumerate(lines):
        if line.strip() == "import re":
            import_start = i
            break

    result = "\n".join(lines[import_start:])

    # Step 2: Delete the "import json" line
    result = "\n".join(
        line for line in result.split("\n") if line.strip() != "import json"
    )

    # Step 3: Delete everything starting with "_load_expected_solution"
    lines = result.split("\n")
    load_start = None
    for i, line in enumerate(lines):
        if line.strip().startswith("def _load_expected_solution"):
            load_start = i
            break

    if load_start is not None:
        result = "\n".join(lines[:load_start])

    # Step 4: Extract and replace mode conditional
    lines = result.split("\n")
    block_start = None
    block_end = None

    # Find the mode conditional block
    for i, line in enumerate(lines):
        if 'if mode == "strict":' in line:
            block_start = i

            # Find the end of the entire block (after the empty line)
            j = i + 1
            while j < len(lines):
                if (
                    lines[j].strip() == ""
                    and j + 1 < len(lines)
                    and not lines[j + 1].startswith("                ")
                ):
                    # Found empty line followed by line with less indentation
                    block_end = j + 1
                    break
                j += 1
            break

    if block_start is not None and block_end is not None:
        # Extract the appropriate logic based on mode
        if mode == "strict":
            replacement = [
                "                if pos in correct_squares and pos not in incorrect_squares:",
                "                    final_correct_squares.add(pos)",
                "",
            ]
        else:  # lenient
            replacement = [
                "                if pos in correct_squares:",
                "                    final_correct_squares.add(pos)",
                "",
            ]

        # Replace the entire block
        lines = lines[:block_start] + replacement + lines[block_end:]

    result = "\n".join(lines)

    # Step 5: Delete ', mode="strict"'
    result = result.replace(', mode="strict"', "")

    # Step 6: Delete lines that start with "(whitespace)mode:"
    lines = result.split("\n")
    result = "\n".join(
        line
        for line in lines
        if not (line.strip().startswith("mode:") and line.startswith(" "))
    )

    # Step 7: Delete the block from end of score docstring to end of _score_detailed docstring
    lines = result.split("\n")
    score_docstring_end = None
    score_detailed_docstring_end = None

    # Find end of score function docstring (second """)
    in_score_func = False
    docstring_count = 0
    for i, line in enumerate(lines):
        if line.strip().startswith("def score("):
            in_score_func = True
            docstring_count = 0
        elif in_score_func and line.strip() == '"""':
            docstring_count += 1
            if docstring_count == 2:  # This is the closing """
                score_docstring_end = i
                break

    # Find end of _score_detailed function docstring (second """)
    in_detailed_func = False
    docstring_count = 0
    for i, line in enumerate(lines):
        if line.strip().startswith("def _score_detailed("):
            in_detailed_func = True
            docstring_count = 0
        elif in_detailed_func and line.strip() == '"""':
            docstring_count += 1
            if docstring_count == 2:  # This is the closing """
                score_detailed_docstring_end = i
                break

    if score_docstring_end is not None and score_detailed_docstring_end is not None:
        # Delete from line after score docstring end to score_detailed docstring end (inclusive)
        lines = (
            lines[: score_docstring_end + 1] + lines[score_detailed_docstring_end + 1 :]
        )

    result = "\n".join(lines)

    # Step 8: Remove mode parameter from function signature
    result = result.replace(', mode="strict"', "")

    # Step 9: Fix trailing whitespace
    result = result.rstrip() + "\n"

    return result


def test_transform_score_lenient():
    """Test that transforming score.py with 'lenient' matches score_lenient.py exactly."""
    with open("src/scaffold_learning/domains/crosswords/score/score.py", "r") as f:
        score_content = f.read()

    with open(
        "src/scaffold_learning/domains/crosswords/score/score_lenient.py", "r"
    ) as f:
        expected_lenient = f.read()

    transformed = transform_score_for_mode(score_content, "lenient")
    assert transformed == expected_lenient


def test_transform_score_strict():
    """Test that transforming score.py with 'strict' matches score_strict.py exactly."""
    with open("src/scaffold_learning/domains/crosswords/score/score.py", "r") as f:
        score_content = f.read()

    with open(
        "src/scaffold_learning/domains/crosswords/score/score_strict.py", "r"
    ) as f:
        expected_strict = f.read()

    transformed = transform_score_for_mode(score_content, "strict")
    assert transformed == expected_strict
