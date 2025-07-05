#!/usr/bin/env python
"""Shared utilities for crossword puzzle processing"""

import json
import gzip
import re
from urllib.request import urlopen, Request

from . import puz


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


def convert_github_to_puz(puzzle_data, source, date):
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


def puzzle_to_input_text(puzzle, numbering):
    """Convert puzzle to input text (empty grid and clues)"""
    lines = []
    
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
        lines.append(" ".join(row_text))
    
    lines.append("")  # Empty line after grid
    
    # Write clues without answers
    lines.append("Across:")
    for clue in numbering.across:
        lines.append(f"{clue['num']:3d}. {clue['clue']}")
    
    lines.append("")
    lines.append("Down:")
    for clue in numbering.down:
        lines.append(f"{clue['num']:3d}. {clue['clue']}")
    
    return "\n".join(lines)


def puzzle_to_solution_text(puzzle, numbering):
    """Convert puzzle to solution text (filled grid and answers)"""
    lines = []
    
    # Write solution grid
    for row in range(puzzle.height):
        cell = row * puzzle.width
        lines.append(" ".join(puzzle.solution[cell : cell + puzzle.width]))
    
    lines.append("")  # Empty line after grid
    
    # Write answer list
    lines.append("Across:")
    for clue in numbering.across:
        answer = "".join(
            puzzle.solution[clue["cell"] + i] for i in range(clue["len"])
        )
        lines.append(f"{clue['num']:3d}. {answer}")
    
    lines.append("")
    lines.append("Down:")
    for clue in numbering.down:
        answer = "".join(
            puzzle.solution[clue["cell"] + i * numbering.width]
            for i in range(clue["len"])
        )
        lines.append(f"{clue['num']:3d}. {answer}")
    
    return "\n".join(lines)


def iterate_puzzles(data, header, source, day_pattern, max_count=None):
    """
    Generator that yields puzzle objects from the GitHub archive
    
    Args:
        data: Archive data dictionary
        header: Header data for requests
        source: Puzzle source name (e.g. "NY Times")
        day_pattern: Regex pattern to filter day names
        max_count: Optional maximum number of puzzles to yield
        
    Yields:
        tuple: (puzzle_object, source, date_string, year, month, day)
    """
    if source not in data:
        print(f"Error: Source '{source}' not found in archive")
        available_sources = sorted(data.keys())
        print(f"Available sources: {', '.join(available_sources)}")
        return

    count = 0
    years = data[source]
    for year, months in sorted(years.items(), reverse=True):
        for month, days in sorted(months.items(), reverse=True):
            for day, info in sorted(days.items(), reverse=True):
                if not re.match(day_pattern, day):
                    continue
                
                try:
                    puzzle_data = get_data(*info, mode="gzip", header=header)
                    date = f"{year}-{month}-{day}"
                    puzzle = convert_github_to_puz(puzzle_data, source, date)

                    if puzzle is None:
                        continue  # Skip problematic/acrostic/diagramless

                    yield puzzle, source, date, year, month, day
                    count += 1
                    
                    if max_count and count >= max_count:
                        return

                except Exception as e:
                    print(f"Error processing {source} {year}-{month}-{day}: {e}")
                    continue