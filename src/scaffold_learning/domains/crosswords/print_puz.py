#!/usr/bin/env python
"""Print the contents of a .puz crossword puzzle file"""

import sys
import puz


def print_puzzle(filename):
    """Print the contents of a puzzle file"""
    # Load the puzzle
    p = puz.read(filename)

    print(f"Title: {p.title}")
    print(f"Author: {p.author}")
    print(f"Copyright: {p.copyright}")
    print(f"Grid size: {p.width}x{p.height}")

    if p.notes:
        print(f"\nNotes: {p.notes}")

    # Print the grid (empty)
    print("\nGrid (empty):")
    for row in range(p.height):
        cell = row * p.width
        # Using fill shows the current state (empty or partially filled)
        print(" ".join(p.fill[cell : cell + p.width]))

    # Print the solution grid
    print("\nSolution:")
    for row in range(p.height):
        cell = row * p.width
        print(" ".join(p.solution[cell : cell + p.width]))

    # Print clues
    numbering = p.clue_numbering()

    print("\nAcross")
    for clue in numbering.across:
        answer = "".join(p.solution[clue["cell"] + i] for i in range(clue["len"]))
        print(f"{clue['num']:3d}. {clue['clue']} - {answer}")

    print("\nDown")
    for clue in numbering.down:
        answer = "".join(
            p.solution[clue["cell"] + i * numbering.width] for i in range(clue["len"])
        )
        print(f"{clue['num']:3d}. {clue['clue']} - {answer}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <puzzle.puz>")
        sys.exit(1)

    print_puzzle(sys.argv[1])
