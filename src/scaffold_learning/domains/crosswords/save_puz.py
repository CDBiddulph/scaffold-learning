#!/usr/bin/env python
"""Save .puz crossword puzzle file contents to separate puzzle and answer files"""

import sys
import os
import puz


def save_puzzle_file(puzzle, numbering, output_path):
    """Save the puzzle file with empty grid and clues"""
    with open(output_path, "w", encoding="utf-8") as f:
        # Write empty grid
        for row in range(puzzle.height):
            cell = row * puzzle.width
            row_text = []
            for col in range(puzzle.width):
                idx = cell + col
                if puzzle.solution[idx] == ".":
                    row_text.append(".")
                else:
                    row_text.append("-")
            f.write(" ".join(row_text) + "\n")
        f.write("\n")

        # Write clues without answers
        f.write("Across:\n")
        for clue in numbering.across:
            f.write(f"{clue['num']:3d}. {clue['clue']}\n")

        f.write("\nDown:\n")
        for clue in numbering.down:
            f.write(f"{clue['num']:3d}. {clue['clue']}\n")


def save_answer_file(puzzle, numbering, output_path):
    """Save the answer file with solution grid and answers"""
    with open(output_path, "w", encoding="utf-8") as f:
        # Write solution grid
        for row in range(puzzle.height):
            cell = row * puzzle.width
            f.write(" ".join(puzzle.solution[cell : cell + puzzle.width]) + "\n")
        f.write("\n")

        # Write answer list
        f.write("Across:\n")
        for clue in numbering.across:
            answer = "".join(
                puzzle.solution[clue["cell"] + i] for i in range(clue["len"])
            )
            f.write(f"{clue['num']:3d}. {answer}\n")

        f.write("\nDown:\n")
        for clue in numbering.down:
            answer = "".join(
                puzzle.solution[clue["cell"] + i * numbering.width]
                for i in range(clue["len"])
            )
            f.write(f"{clue['num']:3d}. {answer}\n")


def save_puzzle_files(filename):
    """Save puzzle and answer files from a .puz file"""
    # Load the puzzle
    p = puz.read(filename)

    # Get base name without extension
    base_name = os.path.splitext(os.path.basename(filename))[0]

    # Create output directory if it doesn't exist
    output_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(output_dir, exist_ok=True)

    # Define output file paths
    puzzle_file = os.path.join(output_dir, f"{base_name}_puz.txt")
    answer_file = os.path.join(output_dir, f"{base_name}_ans.txt")

    # Get numbering for clues
    numbering = p.clue_numbering()

    # Save both files
    save_puzzle_file(p, numbering, puzzle_file)
    save_answer_file(p, numbering, answer_file)

    print(f"Saved puzzle to: {puzzle_file}")
    print(f"Saved answers to: {answer_file}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <puzzle.puz>")
        sys.exit(1)

    save_puzzle_files(sys.argv[1])
