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
from .puzzle_utils import (
    get_data,
    iterate_puzzles,
    puzzle_to_input_text,
    puzzle_to_solution_text,
)


# get_data function moved to puzzle_utils.py


def puzzle_to_text(puzzle):
    """Convert puzzle to input and solution text strings"""
    numbering = puzzle.clue_numbering()

    input_text = puzzle_to_input_text(puzzle, numbering)
    solution_text = puzzle_to_solution_text(puzzle, numbering)

    return input_text, solution_text


def collect_puzzles(data, header, target_count, source, day_pattern, day_of_week=None):
    """Collect puzzles and convert to text format"""
    puzzles = []

    for puzzle, source, date, year, month, day in iterate_puzzles(
        data, header, source, day_pattern, target_count, day_of_week
    ):
        # Convert to text
        input_text, solution_text = puzzle_to_text(puzzle)

        # Generate ID using same format as download_puz
        id = f"{source}_{year}_{month}_{day}".replace(" ", "_")

        puzzles.append({"id": id, "input": input_text, "solution": solution_text})

        print(f"Collected {len(puzzles)}/{target_count}: {source} {date}")

    return puzzles


def save_puzzles_to_dir(puzzles, output_dir, num_train, num_valid, seed):
    """Save puzzles to train.jsonl and valid.jsonl in the given directory"""
    # Shuffle with deterministic seed
    random.seed(seed)
    random.shuffle(puzzles)

    # Split into train and validation
    train_puzzles = puzzles[:num_train]
    valid_puzzles = puzzles[num_train : num_train + num_valid]

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

    print(f"Saved {len(train_puzzles)} training puzzles to {train_file}")
    print(f"Saved {len(valid_puzzles)} validation puzzles to {valid_file}")

    return len(train_puzzles), len(valid_puzzles)


def create_all_day_datasets(
    data, header, output_dir, num_train, num_valid, source, day_filter, seed
):
    """Create datasets for all days of the week in separate directories"""
    days_of_week = [
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    ]
    total_train = 0
    total_valid = 0

    for day in days_of_week:
        print(f"\nProcessing {day}s...")
        day_dir = output_dir / day
        day_dir.mkdir(parents=True, exist_ok=True)

        # Collect puzzles for this day
        day_puzzles = collect_puzzles(
            data, header, num_train + num_valid, source, day_filter, day
        )

        if len(day_puzzles) < num_train + num_valid:
            print(
                f"Warning: Only found {len(day_puzzles)} {day} puzzles, needed {num_train + num_valid}"
            )

        # Save puzzles to this day's directory (different seed for each day)
        train_count, valid_count = save_puzzles_to_dir(
            day_puzzles, day_dir, num_train, num_valid, seed + hash(day)
        )
        total_train += train_count
        total_valid += valid_count

    return total_train, total_valid


def main():
    """Download puzzles and save as JSONL files"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Prepare crossword datasets from GitHub archive"
    )
    parser.add_argument(
        "output_dir", help="Directory to save train.jsonl and valid.jsonl files"
    )
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
        "--day-of-week",
        choices=[
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
            "all",
        ],
        help="Filter puzzles by day of the week (e.g., monday, tuesday, etc.) or 'all' for all days",
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

    if args.day_of_week == "all":
        return create_all_day_datasets(
            data,
            header,
            output_dir,
            args.num_train,
            args.num_valid,
            args.source,
            args.day_filter,
            args.seed,
        )
    else:
        # Original behavior for single day or no day filter
        total_needed = args.num_train + args.num_valid
        day_filter_msg = f" on {args.day_of_week}s" if args.day_of_week else ""
        print(
            f"Searching for {total_needed} suitable puzzles from {args.source}{day_filter_msg}..."
        )

        all_puzzles = collect_puzzles(
            data, header, total_needed, args.source, args.day_filter, args.day_of_week
        )

        if len(all_puzzles) < total_needed:
            print(
                f"Warning: Only found {len(all_puzzles)} puzzles, needed {total_needed}"
            )

        return save_puzzles_to_dir(
            all_puzzles, output_dir, args.num_train, args.num_valid, args.seed
        )


if __name__ == "__main__":
    main()
