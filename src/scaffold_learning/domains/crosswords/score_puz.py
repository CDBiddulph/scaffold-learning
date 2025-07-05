#!/usr/bin/env python
"""Score a crossword puzzle answer against the solution"""

import sys
import os
import json
import re
from . import puz


def score_puzzle(expected_solution, attempted_solution, mode="strict"):
    """
    Score a puzzle answer against the solution.

    Args:
        expected_solution: String containing the expected solution (like from JSONL "solution" field)
        attempted_solution: String containing the attempted solution
        mode: 'strict' (all instances must be correct) or 'lenient' (any instance can be correct)

    Returns:
        float: Score from 0.0 to 1.0 representing percentage of correct squares
    """
    # Parse the expected solution to extract grid and clues
    expected_lines = expected_solution.strip().split('\n')
    
    # Extract grid
    grid_lines = []
    line_idx = 0
    while line_idx < len(expected_lines):
        line = expected_lines[line_idx].strip()
        if not line or line.startswith("Across:") or line.startswith("Down:"):
            break
        grid_lines.append(line)
        line_idx += 1
    
    # Convert grid to solution string and determine dimensions
    width = len(grid_lines[0].split()) if grid_lines else 0
    height = len(grid_lines)
    solution_string = ""
    for line in grid_lines:
        cells = line.split()
        solution_string += "".join(cells)
    
    # Extract clues sections
    across_clues = []
    down_clues = []
    
    current_section = None
    for i in range(line_idx, len(expected_lines)):
        line = expected_lines[i].strip()
        if line.startswith("Across:"):
            current_section = "across"
        elif line.startswith("Down:"):
            current_section = "down"
        elif line and current_section:
            # Parse clue line
            match = re.match(r'\s*(\d+)\.\s*(.+)', line)
            if match:
                clue_num = int(match.group(1))
                answer = match.group(2).strip()
                if current_section == "across":
                    across_clues.append((clue_num, answer))
                else:
                    down_clues.append((clue_num, answer))
    
    # Create a real puz puzzle object to get proper numbering
    puzzle = puz.Puzzle()
    puzzle.width = width
    puzzle.height = height
    puzzle.solution = solution_string
    puzzle.fill = "-" * len(solution_string)  # All empty
    
    # Set dummy clues (we just need the numbering)
    puzzle.clues = ["dummy"] * (len(across_clues) + len(down_clues))
    
    numbering = puzzle.clue_numbering()
    
    # Now use the original scoring logic
    content = attempted_solution.strip()
    
    # If file is empty, score is 0.0
    if not content:
        return 0.0

    # Split by double newlines to get pieces
    pieces = content.split("\n\n")

    # If no pieces, score is 0.0
    if not pieces or all(not piece.strip() for piece in pieces):
        return 0.0

    # Track correctness of each fillable square
    total_squares = puzzle.width * puzzle.height
    correct_squares = set()
    incorrect_squares = set()

    # Process each piece
    for piece in pieces:
        piece = piece.strip()
        if not piece:
            continue

        if piece.startswith("Across:"):
            _process_clue_section(
                piece,
                numbering.across,
                puzzle,
                correct_squares,
                incorrect_squares,
                "across",
            )
        elif piece.startswith("Down:"):
            _process_clue_section(
                piece,
                numbering.down,
                puzzle,
                correct_squares,
                incorrect_squares,
                "down",
            )
        else:
            # Assume it's a grid
            _process_grid(piece, puzzle, correct_squares, incorrect_squares)

    # Count fillable squares and determine correct squares based on mode
    fillable_count = 0
    final_correct_squares = set()

    for i in range(total_squares):
        if puzzle.solution[i] != ".":  # Not a black square
            fillable_count += 1

            if mode == "strict":
                # Square is correct only if it was never marked incorrect
                if i in correct_squares and i not in incorrect_squares:
                    final_correct_squares.add(i)
            elif mode == "lenient":
                # Square is correct if it was ever marked correct
                if i in correct_squares:
                    final_correct_squares.add(i)

    correct_count = len(final_correct_squares)

    # Calculate score
    if fillable_count == 0:
        return 0.0

    score = correct_count / fillable_count
    return score


def _process_grid(grid_text, puzzle, correct_squares, incorrect_squares):
    """Process a grid format piece"""
    lines = grid_text.strip().split("\n")

    for row_idx, line in enumerate(lines):
        if row_idx >= puzzle.height:
            break

        # Split by spaces and process each cell
        cells = line.split()
        for col_idx, cell in enumerate(cells):
            if col_idx >= puzzle.width:
                break

            square_idx = row_idx * puzzle.width + col_idx
            expected = puzzle.solution[square_idx].upper()
            actual = cell.upper()

            # Skip black squares
            if expected == ".":
                continue

            # Mark square as correct or incorrect
            if actual == expected:
                correct_squares.add(square_idx)
            else:
                incorrect_squares.add(square_idx)


def _process_clue_section(
    section_text, clues, puzzle, correct_squares, incorrect_squares, direction
):
    """Process an Across: or Down: section"""
    lines = section_text.split("\n")[1:]  # Skip the "Across:" or "Down:" line

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Parse clue number and answer
        match = re.match(r"\s*(\d+)\.\s*(.+)", line)
        if not match:
            continue

        clue_num = int(match.group(1))
        answer = match.group(2).strip().upper()

        # Find the clue with this number
        target_clue = None
        for clue in clues:
            if clue["num"] == clue_num:
                target_clue = clue
                break

        if target_clue is None:
            continue

        # Check each letter of the answer
        for i, letter in enumerate(answer):
            if i >= target_clue["len"]:
                break  # Answer is too long, ignore extra characters

            if direction == "across":
                square_idx = target_clue["cell"] + i
            else:  # down
                square_idx = target_clue["cell"] + i * puzzle.width

            if square_idx >= len(puzzle.solution):
                break

            expected = puzzle.solution[square_idx].upper()

            # Skip black squares
            if expected == ".":
                continue

            # Mark square as correct or incorrect
            if letter == expected:
                correct_squares.add(square_idx)
            else:
                incorrect_squares.add(square_idx)


def load_expected_solution(file_path, puzzle_name=None):
    """
    Load expected solution from either a text file or JSONL file
    
    Args:
        file_path: Path to the file
        puzzle_name: If JSONL file, the name of the puzzle to find
    
    Returns:
        str: Expected solution string
    """
    if file_path.endswith('.jsonl'):
        if puzzle_name is None:
            raise ValueError("puzzle_name required when using JSONL file")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                data = json.loads(line.strip())
                if data.get('name') == puzzle_name:
                    return data['solution']
        
        raise ValueError(f"Puzzle '{puzzle_name}' not found in JSONL file")
    
    else:
        # Assume it's a text file with the expected solution
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()


def main():
    """Command line interface"""
    if len(sys.argv) < 3 or len(sys.argv) > 5:
        print(f"Usage: {sys.argv[0]} <expected_solution> <attempted_solution> [puzzle_name] [mode]")
        print("  expected_solution: Text file with expected solution OR JSONL file")
        print("  attempted_solution: Text file with attempted solution")
        print("  puzzle_name: Required if expected_solution is JSONL file")
        print("  mode: 'strict' (default) or 'lenient'")
        print()
        print("Examples:")
        print(f"  {sys.argv[0]} expected.txt attempted.txt")
        print(f"  {sys.argv[0]} dataset.jsonl attempted.txt NY_Times_2025_06_23")
        print(f"  {sys.argv[0]} dataset.jsonl attempted.txt NY_Times_2025_06_23 lenient")
        sys.exit(1)

    expected_file = sys.argv[1]
    attempted_file = sys.argv[2]
    
    # Handle variable arguments
    if len(sys.argv) == 4:
        if sys.argv[3] in ["strict", "lenient"]:
            puzzle_name = None
            mode = sys.argv[3]
        else:
            puzzle_name = sys.argv[3]
            mode = "strict"
    elif len(sys.argv) == 5:
        puzzle_name = sys.argv[3]
        mode = sys.argv[4]
    else:
        puzzle_name = None
        mode = "strict"

    if mode not in ["strict", "lenient"]:
        print("Mode must be 'strict' or 'lenient'")
        sys.exit(1)

    if not os.path.exists(expected_file):
        print(f"Error: Expected solution file '{expected_file}' not found")
        sys.exit(1)
    
    if not os.path.exists(attempted_file):
        print(f"Error: Attempted solution file '{attempted_file}' not found")
        sys.exit(1)

    try:
        # Load expected solution
        expected_solution = load_expected_solution(expected_file, puzzle_name)
        
        # Load attempted solution
        with open(attempted_file, 'r', encoding='utf-8') as f:
            attempted_solution = f.read()

        score = score_puzzle(expected_solution, attempted_solution, mode)
        print(f"Score: {score:.3f} ({int(score * 100)}/100) [{mode}]")

    except Exception as e:
        print(f"Error scoring puzzle: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()