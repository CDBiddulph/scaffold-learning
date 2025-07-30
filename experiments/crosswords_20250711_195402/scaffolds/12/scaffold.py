import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    try:
        # Parse the input crossword
        lines = input_string.strip().split('\n')
        
        # Find where grid ends and clues begin
        grid_lines = []
        clue_start = -1
        
        for i, line in enumerate(lines):
            if line.strip().startswith('Across:'):
                clue_start = i
                break
            grid_lines.append(line)
        
        if clue_start == -1:
            logging.error("Could not find 'Across:' section")
            return input_string
        
        # Parse the grid
        grid = [line.split() for line in grid_lines]
        height = len(grid)
        width = len(grid[0]) if height > 0 else 0
        
        # Parse clues
        clue_lines = lines[clue_start:]
        across_clues, down_clues = parse_clues(clue_lines)
        
        # Solve clues using LLM
        solved_across = solve_clues(across_clues, grid, 'across')
        solved_down = solve_clues(down_clues, grid, 'down')
        
        # Fill the grid with solutions
        filled_grid = fill_grid(grid, solved_across, solved_down)
        
        # Format output
        result = []
        for row in filled_grid:
            result.append(' '.join(row))
        
        result.append('')
        result.append('Across:')
        for clue_num in sorted(solved_across.keys()):
            result.append(f'  {clue_num}. {solved_across[clue_num]}')
        
        result.append('')
        result.append('Down:')
        for clue_num in sorted(solved_down.keys()):
            result.append(f'  {clue_num}. {solved_down[clue_num]}')
        
        return '\n'.join(result)
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return input_string

def parse_clues(clue_lines):
    across_clues = {}
    down_clues = {}
    current_section = None
    
    for line in clue_lines:
        line = line.strip()
        if line.startswith('Across:'):
            current_section = 'across'
        elif line.startswith('Down:'):
            current_section = 'down'
        elif line and current_section:
            match = re.match(r'\s*(\d+)\.\s*(.+)', line)
            if match:
                clue_num = int(match.group(1))
                clue_text = match.group(2).strip()
                if current_section == 'across':
                    across_clues[clue_num] = clue_text
                else:
                    down_clues[clue_num] = clue_text
    
    return across_clues, down_clues

def solve_clues(clues, grid, direction):
    solved = {}
    
    for clue_num, clue_text in clues.items():
        try:
            # Get the length of the answer
            length = get_clue_length(clue_num, grid, direction)
            if length == 0:
                continue
                
            # Solve the clue
            answer = solve_single_clue(clue_text, length)
            if answer:
                solved[clue_num] = answer
                
        except Exception as e:
            logging.error(f"Failed to solve {direction} clue {clue_num}: {e}")
            continue
    
    return solved

def solve_single_clue(clue_text, length):
    prompt = f"""Solve this crossword clue. The answer is exactly {length} letters long.
Respond with ONLY the answer in capital letters, nothing else.

Clue: {clue_text}
Length: {length} letters"""
    
    try:
        response = execute_llm(prompt).strip().upper()
        
        # Extract words from response
        words = re.findall(r'[A-Z]+', response)
        
        # Find word of correct length
        for word in words:
            if len(word) == length:
                return word
        
        # If no exact match, return first word that's close
        for word in words:
            if word.isalpha() and len(word) > 0:
                return word[:length] if len(word) > length else word
                
        return None
        
    except Exception as e:
        logging.error(f"Error solving clue '{clue_text}': {e}")
        return None

def get_clue_length(clue_num, grid, direction):
    pos = find_clue_position(clue_num, grid)
    if pos is None:
        return 0
    
    row, col = pos
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0
    
    if direction == 'across':
        length = 0
        for c in range(col, width):
            if grid[row][c] == '.':
                break
            length += 1
        return length
    else:  # down
        length = 0
        for r in range(row, height):
            if grid[r][col] == '.':
                break
            length += 1
        return length

def find_clue_position(clue_num, grid):
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0
    current_num = 1
    
    for row in range(height):
        for col in range(width):
            if grid[row][col] == '.':
                continue
            
            # Check if this position starts a word
            starts_across = (
                (col == 0 or grid[row][col - 1] == '.')
                and col + 1 < width
                and grid[row][col + 1] != '.'
            )
            starts_down = (
                (row == 0 or grid[row - 1][col] == '.')
                and row + 1 < height
                and grid[row + 1][col] != '.'
            )
            
            if starts_across or starts_down:
                if current_num == clue_num:
                    return (row, col)
                current_num += 1
    
    return None

def fill_grid(grid, solved_across, solved_down):
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0
    
    # Create filled grid
    filled = [row[:] for row in grid]
    
    # Fill across answers
    for clue_num, answer in solved_across.items():
        pos = find_clue_position(clue_num, grid)
        if pos is None:
            continue
        
        row, col = pos
        for i, letter in enumerate(answer):
            if col + i < width and grid[row][col + i] != '.':
                filled[row][col + i] = letter
    
    # Fill down answers (may override across if conflicting)
    for clue_num, answer in solved_down.items():
        pos = find_clue_position(clue_num, grid)
        if pos is None:
            continue
        
        row, col = pos
        for i, letter in enumerate(answer):
            if row + i < height and grid[row + i][col] != '.':
                filled[row + i][col] = letter
    
    return filled