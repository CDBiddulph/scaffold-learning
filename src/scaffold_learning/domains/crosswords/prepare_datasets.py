#!/usr/bin/env python
"""Prepare crossword datasets by downloading puzzles and saving as JSONL files"""

import argparse
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from .puz import Puzzle

from scaffold_learning.core.dataset_utils import save_dataset_splits

from .puzzle_utils import (
    get_data,
    iterate_puzzles,
    puzzle_to_input_text,
    puzzle_to_solution_text,
)


def puzzle_to_text(puzzle: Puzzle) -> Tuple[str, str]:
    """Convert puzzle to input and solution text strings"""
    numbering = puzzle.clue_numbering()

    input_text = puzzle_to_input_text(puzzle, numbering)
    solution_text = puzzle_to_solution_text(puzzle, numbering)

    return input_text, solution_text


def collect_puzzles(
    data: Dict[str, Dict[str, Dict[str, Dict[str, List[int]]]]],
    header: bytes,
    target_count: int,
    source: str,
    day_pattern: str,
    day_of_week: Optional[str] = None,
) -> List[Dict[str, str]]:
    """Collect puzzles and convert to text format"""
    puzzles = []

    for puzzle, source, date, year, month, day in iterate_puzzles(
        data, header, source, day_pattern, target_count, day_of_week
    ):
        # Convert to text
        input_text, solution_text = puzzle_to_text(puzzle)

        # Generate ID using same format as download_puz
        id = f"{source}_{year}_{month}_{day}".replace(" ", "_")

        puzzles.append(
            {"id": id, "input": input_text, "scoring_data": {"solution": solution_text}}
        )

        print(f"Collected {len(puzzles)}/{target_count}: {source} {date}")

    return puzzles


def create_all_day_datasets(
    data, header, output_dir, puzzle_counts, source, day_filter, seed
) -> None:
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

    for day in days_of_week:
        print(f"\nProcessing {day.capitalize()} puzzles...")
        day_dir = output_dir / day
        day_dir.mkdir(parents=True, exist_ok=True)

        # Collect puzzles for this day
        total_puzzles = sum(puzzle_counts.values())
        day_puzzles = collect_puzzles(
            data, header, total_puzzles, source, day_filter, day
        )

        if len(day_puzzles) < total_puzzles:
            raise ValueError(
                f"Only found {len(day_puzzles)} {day.capitalize()} puzzles, needed {total_puzzles}"
            )

        # Save puzzles to this day's directory (different seed for each day)
        day_seed = (seed, day)
        save_dataset_splits(day_puzzles, day_dir, puzzle_counts, day_seed)


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
        help="Number of training puzzles",
    )
    parser.add_argument(
        "--num-valid",
        type=int,
        help="Number of validation puzzles",
    )
    parser.add_argument(
        "--num-test",
        type=int,
        help="Number of test puzzles",
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

    puzzle_counts = {
        "train": args.num_train,
        "valid": args.num_valid,
        "test": args.num_test,
    }

    if args.day_of_week == "all":
        # Create datasets for all days of the week
        create_all_day_datasets(
            data,
            header,
            output_dir,
            puzzle_counts,
            args.source,
            args.day_filter,
            args.seed,
        )
        return

    # Single day or no day filter
    total_needed = sum(puzzle_counts.values())
    day_filter_msg = f" on {args.day_of_week}s" if args.day_of_week else ""
    print(
        f"Searching for {total_needed} suitable puzzles from {args.source}{day_filter_msg}..."
    )

    all_puzzles = collect_puzzles(
        data, header, total_needed, args.source, args.day_filter, args.day_of_week
    )

    if len(all_puzzles) < total_needed:
        raise ValueError(
            f"Only found {len(all_puzzles)} puzzles, needed {total_needed}"
        )

    save_dataset_splits(all_puzzles, output_dir, puzzle_counts, args.seed)


if __name__ == "__main__":
    main()
