#!/usr/bin/env python
"""Download crossword puzzles from GitHub archive and save as .puz files"""

import argparse
import os
import sys
from pathlib import Path
from urllib.request import urlopen, Request
import gzip
import json

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


def download_puzzles(data, header, output_dir, target_count, source):
    """Download puzzles until target count is reached"""
    saved_count = 0

    if source not in data:
        print(f"Error: Source '{source}' not found in archive")
        available_sources = sorted(data.keys())
        print(f"Available sources: {', '.join(available_sources)}")
        return 0

    years = data[source]
    for year, months in sorted(years.items(), reverse=True):
        for month, days in sorted(months.items(), reverse=True):
            for day, info in sorted(days.items(), reverse=True):
                if day.endswith("-mini"):
                    continue
                # Fetch puzzle data
                try:
                    puzzle_data = get_data(*info, mode="gzip", header=header)

                    # Convert to puz format
                    date = f"{year}-{month}-{day}"
                    puzzle = convert_to_puz(puzzle_data, source, date)

                    if puzzle is None:
                        continue  # Skip problematic/acrostic/diagramless

                    # Save puzzle
                    filename = f"{source}_{year}_{month}_{day}.puz".replace(" ", "_")
                    filepath = output_dir / filename
                    puzzle.save(str(filepath))

                    saved_count += 1
                    print(f"Saved {saved_count}/{target_count}: {filename}")

                    if saved_count >= target_count:
                        return saved_count

                except Exception as e:
                    print(f"Error processing {source} {year}-{month}-{day}: {e}")
                    continue

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

    saved_count = download_puzzles(data, header, output_dir, target_count, args.source)

    print(f"\nSuccessfully downloaded {saved_count} puzzles to {output_dir}")
    return saved_count


if __name__ == "__main__":
    main()
