#!/usr/bin/env python
"""Score a crossword puzzle answer against the solution"""

import sys
import puz
import re


def score_puzzle(puz_file, answer_file):
    """
    Score a puzzle answer file against the solution.
    
    Args:
        puz_file: Path to .puz file
        answer_file: Path to .txt file with answers
    
    Returns:
        tuple: (score_float, correct_count, total_count)
    """
    # Load the puzzle
    puzzle = puz.read(puz_file)
    numbering = puzzle.clue_numbering()
    
    # Read the answer file
    with open(answer_file, 'r', encoding='utf-8') as f:
        content = f.read().strip()
    
    # If file is empty, score is 0.0
    if not content:
        return (0.0, 0, 0)
    
    # Split by double newlines to get pieces
    pieces = content.split('\n\n')
    
    # If no pieces, score is 0.0
    if not pieces or all(not piece.strip() for piece in pieces):
        return (0.0, 0, 0)
    
    # Track correctness of each fillable square
    # We'll use None for unfilled, True for correct, False for incorrect
    total_squares = puzzle.width * puzzle.height
    square_correctness = [None] * total_squares
    
    # Process each piece
    for piece in pieces:
        piece = piece.strip()
        if not piece:
            continue
            
        if piece.startswith('Across:'):
            _process_clue_section(piece, numbering.across, puzzle, square_correctness, 'across')
        elif piece.startswith('Down:'):
            _process_clue_section(piece, numbering.down, puzzle, square_correctness, 'down')
        else:
            # Assume it's a grid
            _process_grid(piece, puzzle, square_correctness)
    
    # Count fillable squares and correct squares
    fillable_count = 0
    correct_count = 0
    
    for i in range(total_squares):
        if puzzle.solution[i] != '.':  # Not a black square
            fillable_count += 1
            if square_correctness[i] is True:
                correct_count += 1
    
    # Calculate score
    if fillable_count == 0:
        return (0.0, 0, 0)
    
    score = correct_count / fillable_count
    return (score, correct_count, fillable_count)


def _process_grid(grid_text, puzzle, square_correctness):
    """Process a grid format piece"""
    lines = grid_text.strip().split('\n')
    
    for row_idx, line in enumerate(lines):
        if row_idx >= puzzle.height:
            break
            
        # Split by spaces and process each cell
        cells = line.split()
        for col_idx, cell in enumerate(cells):
            if col_idx >= puzzle.width:
                break
                
            square_idx = row_idx * puzzle.width + col_idx
            expected = puzzle.solution[square_idx].upper()
            actual = cell.upper()
            
            # Skip black squares
            if expected == '.':
                continue
                
            # Mark square as correct or incorrect
            if actual == expected:
                if square_correctness[square_idx] is None:
                    square_correctness[square_idx] = True
            else:
                square_correctness[square_idx] = False


def _process_clue_section(section_text, clues, puzzle, square_correctness, direction):
    """Process an Across: or Down: section"""
    lines = section_text.split('\n')[1:]  # Skip the "Across:" or "Down:" line
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Parse clue number and answer
        match = re.match(r'\s*(\d+)\.\s*(.+)', line)
        if not match:
            continue
            
        clue_num = int(match.group(1))
        answer = match.group(2).strip().upper()
        
        # Find the clue with this number
        target_clue = None
        for clue in clues:
            if clue['num'] == clue_num:
                target_clue = clue
                break
        
        if target_clue is None:
            continue
            
        # Check each letter of the answer
        for i, letter in enumerate(answer):
            if i >= target_clue['len']:
                break  # Answer is too long, ignore extra characters
                
            if direction == 'across':
                square_idx = target_clue['cell'] + i
            else:  # down
                square_idx = target_clue['cell'] + i * puzzle.width
                
            if square_idx >= len(puzzle.solution):
                break
                
            expected = puzzle.solution[square_idx].upper()
            
            # Skip black squares
            if expected == '.':
                continue
                
            # Mark square as correct or incorrect
            if letter == expected:
                if square_correctness[square_idx] is None:
                    square_correctness[square_idx] = True
            else:
                square_correctness[square_idx] = False


def main():
    """Command line interface"""
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <puzzle.puz> <answer.txt>")
        sys.exit(1)
    
    puz_file = sys.argv[1]
    answer_file = sys.argv[2]
    
    score, correct, total = score_puzzle(puz_file, answer_file)
    print(f"Score: {score:.3f} ({correct}/{total})")


if __name__ == '__main__':
    main()