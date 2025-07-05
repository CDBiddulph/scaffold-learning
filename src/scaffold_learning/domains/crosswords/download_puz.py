#!/usr/bin/env python
"""Download crossword puzzles from GitHub archive and save as .puz files"""

import argparse
import os
import re
import sys
from pathlib import Path
from urllib.request import urlopen, Request
import gzip
import json

from . import puz
from .puzzle_utils import get_data, iterate_puzzles


# get_data function moved to puzzle_utils.py


def download_puzzles(data, header, output_dir, target_count, source, day_pattern):
    """Download puzzles until target count is reached"""
    saved_count = 0

    for puzzle, source_name, date, year, month, day in iterate_puzzles(data, header, source, day_pattern, target_count):
        # Save puzzle
        filename = f"{source_name}_{year}_{month}_{day}.puz".replace(" ", "_")
        filepath = output_dir / filename
        puzzle.save(str(filepath))

        saved_count += 1
        print(f"Saved {saved_count}/{target_count}: {filename}")

    return saved_count


def main():
    """Download puzzles and save as .puz files"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Download crossword puzzles from GitHub archive"
    )
    parser.add_argument("output_dir", help="Directory to save downloaded .puz files")
    parser.add_argument(
        "-n",
        "--num-puzzles",
        type=int,
        default=10,
        help="Number of puzzles to download (default: 10)",
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
    args = parser.parse_args()

    # Output directory from argument
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Get metadata
    print("Fetching puzzle metadata...")
    meta = get_data(0, 22, 78)
    header = get_data(*meta[5:8], mode="raw")
    data = get_data(*meta[2:5], mode="gzip", header=header)

    # Download puzzles
    target_count = args.num_puzzles
    print(f"Searching for {target_count} suitable puzzles from {args.source}...")

    saved_count = download_puzzles(
        data, header, output_dir, target_count, args.source, args.day_filter
    )

    print(f"\nSuccessfully downloaded {saved_count} puzzles to {output_dir}")
    return saved_count


if __name__ == "__main__":
    main()
