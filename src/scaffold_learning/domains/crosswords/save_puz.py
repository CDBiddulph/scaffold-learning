#!/usr/bin/env python
"""Save .puz crossword puzzle file contents to separate puzzle and answer files"""

import sys
import os
from . import puz
from .puzzle_utils import puzzle_to_input_text, puzzle_to_solution_text


def save_puzzle_file(puzzle, numbering, output_path):
    """Save the puzzle file with empty grid and clues"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(puzzle_to_input_text(puzzle, numbering))


def save_answer_file(puzzle, numbering, output_path):
    """Save the answer file with solution grid and answers"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(puzzle_to_solution_text(puzzle, numbering))


def save_puzzle_files(filename, output_dir=None):
    """Save puzzle and answer files from a .puz file"""
    # Load the puzzle
    p = puz.read(filename)

    # Get base name without extension
    base_name = os.path.splitext(os.path.basename(filename))[0]

    # Use provided output directory or default
    if output_dir is None:
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

    return puzzle_file, answer_file


def process_directory(input_dir, output_dir=None):
    """Process all .puz files in a directory"""
    # Find all .puz files
    puz_files = []
    for filename in os.listdir(input_dir):
        if filename.endswith(".puz"):
            puz_files.append(os.path.join(input_dir, filename))

    if not puz_files:
        print(f"No .puz files found in {input_dir}")
        return

    print(f"Found {len(puz_files)} .puz files to process")

    # Process each file
    for i, puz_file in enumerate(puz_files, 1):
        print(f"\nProcessing {i}/{len(puz_files)}: {os.path.basename(puz_file)}")
        try:
            save_puzzle_files(puz_file, output_dir)
        except Exception as e:
            print(f"Error processing {puz_file}: {e}")
            continue

    print(f"\nFinished processing {len(puz_files)} puzzles")


if __name__ == "__main__":
    if len(sys.argv) != 2 and len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <puzzle.puz or directory> [output_directory]")
        print("Examples:")
        print(f"  {sys.argv[0]} puzzle.puz")
        print(f"  {sys.argv[0]} input_dir/")
        print(f"  {sys.argv[0]} input_dir/ output_dir/")
        sys.exit(1)

    input_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) == 3 else None

    if os.path.isdir(input_path):
        process_directory(input_path, output_dir)
    elif os.path.isfile(input_path) and input_path.endswith(".puz"):
        save_puzzle_files(input_path, output_dir)
    else:
        print(f"Error: {input_path} is not a valid .puz file or directory")
        sys.exit(1)
