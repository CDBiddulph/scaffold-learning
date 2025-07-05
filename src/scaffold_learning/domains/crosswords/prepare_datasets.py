#!/usr/bin/env python
"""Prepare crossword datasets by downloading puzzles and saving as JSONL files"""

import argparse
import json
import os
import random
import re
import sys
from pathlib import Path
from urllib.request import urlopen, Request
import gzip

from . import puz


# Constants from view_archive.py
def get_data(num, start, len, mode="json", header=None):
    """Fetch data from GitHub archive"""
    req = Request(
        f"https://q726kbxun.github.io/xwords/xwords_data_{num:02d}.dat",
        headers={
            "Range": f"bytes={start}-{start+len-1}",
        },
    )
    resp = urlopen(req)
    data = resp.read()

    if header is not None:
        data = header + data

    if mode == "json":
        return json.loads(data)
    elif mode == "raw":
        return data
    elif mode == "gzip":
        data = gzip.decompress(data)
        return json.loads(data)
    else:
        raise Exception("Invalid mode")


def convert_to_puz(puzzle_data, source, date):
    """Convert puzzle data from GitHub format to puz format"""
    # Extract data
    width = puzzle_data[0]
    height = puzzle_data[1]
    cells = puzzle_data[2]
    clues_data = puzzle_data[3]

    # Check if problematic
    if len(puzzle_data) > 4 and puzzle_data[4]:
        return None  # Skip problematic puzzles

    # Check puzzle type
    if len(puzzle_data) > 5 and puzzle_data[5] in ["acrostic", "diagramless"]:
        return None  # Skip acrostic and diagramless puzzles

    # Create puzzle object
    puzzle = puz.Puzzle()
    puzzle.width = width
    puzzle.height = height

    # Build solution and fill strings
    solution = ""
    fill = ""
    for row in cells:
        for cell in row:
            if cell == 0:
                solution += "."
                fill += "."
            else:
                solution += cell[0].upper()  # First character is the solution
                fill += "-"  # Empty cell

    puzzle.solution = solution
    puzzle.fill = fill

    # Set metadata
    puzzle.title = f"{source} - {date}"
    puzzle.author = source
    puzzle.copyright = f"(c) {source}"

    # Process clues
    # Create a mapping of clue numbers to their clues and directions
    clue_map = {}

    for clue_data in clues_data:
        clue_text = clue_data[0]
        direction = clue_data[1]  # 0 = Across, 1 = Down
        clue_num = clue_data[2]

        if clue_num not in clue_map:
            clue_map[clue_num] = {}

        if direction == 0:
            clue_map[clue_num]["across"] = clue_text
        else:
            clue_map[clue_num]["down"] = clue_text

    # Build clues list in the order expected by .puz format:
    # For each numbered square (in order), add across clue first (if exists), then down clue (if exists)
    puzzle.clues = []
    for num in sorted(clue_map.keys()):
        if "across" in clue_map[num]:
            puzzle.clues.append(clue_map[num]["across"])
        if "down" in clue_map[num]:
            puzzle.clues.append(clue_map[num]["down"])

    return puzzle


def puzzle_to_text(puzzle):
    """Convert puzzle to input and solution text strings"""
    numbering = puzzle.clue_numbering()
    
    # Generate input text (empty grid and clues)
    input_lines = []
    
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
        input_lines.append(" ".join(row_text))
    
    input_lines.append("")  # Empty line after grid
    
    # Write clues without answers
    input_lines.append("Across:")
    for clue in numbering.across:
        input_lines.append(f"{clue['num']:3d}. {clue['clue']}")
    
    input_lines.append("")
    input_lines.append("Down:")
    for clue in numbering.down:
        input_lines.append(f"{clue['num']:3d}. {clue['clue']}")
    
    input_text = "\n".join(input_lines)
    
    # Generate solution text (solution grid and answers)
    solution_lines = []
    
    # Write solution grid
    for row in range(puzzle.height):
        cell = row * puzzle.width
        solution_lines.append(" ".join(puzzle.solution[cell : cell + puzzle.width]))
    
    solution_lines.append("")  # Empty line after grid
    
    # Write answer list
    solution_lines.append("Across:")
    for clue in numbering.across:
        answer = "".join(
            puzzle.solution[clue["cell"] + i] for i in range(clue["len"])
        )
        solution_lines.append(f"{clue['num']:3d}. {answer}")
    
    solution_lines.append("")
    solution_lines.append("Down:")
    for clue in numbering.down:
        answer = "".join(
            puzzle.solution[clue["cell"] + i * numbering.width]
            for i in range(clue["len"])
        )
        solution_lines.append(f"{clue['num']:3d}. {answer}")
    
    solution_text = "\n".join(solution_lines)
    
    return input_text, solution_text


def collect_puzzles(data, header, target_count, source, day_pattern):
    """Collect puzzles and convert to text format"""
    puzzles = []

    if source not in data:
        print(f"Error: Source '{source}' not found in archive")
        available_sources = sorted(data.keys())
        print(f"Available sources: {', '.join(available_sources)}")
        return puzzles

    years = data[source]
    for year, months in sorted(years.items(), reverse=True):
        for month, days in sorted(months.items(), reverse=True):
            for day, info in sorted(days.items(), reverse=True):
                if not re.match(day_pattern, day):
                    continue
                # Fetch puzzle data
                try:
                    puzzle_data = get_data(*info, mode="gzip", header=header)

                    # Convert to puz format
                    date = f"{year}-{month}-{day}"
                    puzzle = convert_to_puz(puzzle_data, source, date)

                    if puzzle is None:
                        continue  # Skip problematic/acrostic/diagramless

                    # Convert to text
                    input_text, solution_text = puzzle_to_text(puzzle)
                    
                    # Generate name using same format as download_puz
                    name = f"{source}_{year}_{month}_{day}".replace(" ", "_")
                    
                    puzzles.append({
                        "name": name,
                        "input": input_text,
                        "solution": solution_text
                    })

                    print(f"Collected {len(puzzles)}/{target_count}: {source} {date}")

                    if len(puzzles) >= target_count:
                        return puzzles

                except Exception as e:
                    print(f"Error processing {source} {year}-{month}-{day}: {e}")
                    continue

    return puzzles


def main():
    """Download puzzles and save as JSONL files"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Prepare crossword datasets from GitHub archive"
    )
    parser.add_argument("output_dir", help="Directory to save train.jsonl and valid.jsonl files")
    parser.add_argument(
        "--num-train",
        type=int,
        default=50,
        help="Number of training puzzles (default: 50)",
    )
    parser.add_argument(
        "--num-valid",
        type=int,
        default=50,
        help="Number of validation puzzles (default: 50)",
    )
    parser.add_argument(
        "-s",
        "--source",
        default="NY Times",
        help="Puzzle source to download from (default: NY Times)",
    )
    parser.add_argument(
        "--day-filter",
        default=r"^\d+$",
        help="Regex pattern to filter day names (default: '^\\d+$' for numbered days only)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for shuffling puzzles (default: 42)",
    )
    args = parser.parse_args()

    # Output directory from argument
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Get metadata
    print("Fetching puzzle metadata...")
    meta = get_data(0, 22, 78)
    header = get_data(*meta[5:8], mode="raw")
    data = get_data(*meta[2:5], mode="gzip", header=header)

    # Collect training puzzles
    total_needed = args.num_train + args.num_valid
    print(f"Searching for {total_needed} suitable puzzles from {args.source}...")
    
    all_puzzles = collect_puzzles(data, header, total_needed, args.source, args.day_filter)
    
    if len(all_puzzles) < total_needed:
        print(f"Warning: Only found {len(all_puzzles)} puzzles, needed {total_needed}")
    
    # Shuffle with deterministic seed
    random.seed(args.seed)
    random.shuffle(all_puzzles)
    
    # Split into train and validation
    train_puzzles = all_puzzles[:args.num_train]
    valid_puzzles = all_puzzles[args.num_train:args.num_train + args.num_valid]
    
    # Save training set
    train_file = output_dir / "train.jsonl"
    with open(train_file, "w", encoding="utf-8") as f:
        for puzzle in train_puzzles:
            f.write(json.dumps(puzzle) + "\n")
    
    # Save validation set
    valid_file = output_dir / "valid.jsonl"
    with open(valid_file, "w", encoding="utf-8") as f:
        for puzzle in valid_puzzles:
            f.write(json.dumps(puzzle) + "\n")

    print(f"\nSaved {len(train_puzzles)} training puzzles to {train_file}")
    print(f"Saved {len(valid_puzzles)} validation puzzles to {valid_file}")
    
    return len(train_puzzles), len(valid_puzzles)


if __name__ == "__main__":
    main()