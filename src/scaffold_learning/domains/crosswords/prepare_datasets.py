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
from .puzzle_utils import get_data, iterate_puzzles, puzzle_to_input_text, puzzle_to_solution_text


# get_data function moved to puzzle_utils.py


def puzzle_to_text(puzzle):
    """Convert puzzle to input and solution text strings"""
    numbering = puzzle.clue_numbering()
    
    input_text = puzzle_to_input_text(puzzle, numbering)
    solution_text = puzzle_to_solution_text(puzzle, numbering)
    
    return input_text, solution_text


def collect_puzzles(data, header, target_count, source, day_pattern):
    """Collect puzzles and convert to text format"""
    puzzles = []

    for puzzle, source_name, date, year, month, day in iterate_puzzles(data, header, source, day_pattern, target_count):
        # Convert to text
        input_text, solution_text = puzzle_to_text(puzzle)
        
        # Generate name using same format as download_puz
        name = f"{source_name}_{year}_{month}_{day}".replace(" ", "_")
        
        puzzles.append({
            "name": name,
            "input": input_text,
            "solution": solution_text
        })

        print(f"Collected {len(puzzles)}/{target_count}: {source_name} {date}")

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