import logging
import re
from llm_executor import execute_llm

def parse_input(input_string):
    """Parse input to extract grid structure and clues"""
    lines = input_string.strip().split('\n')
    
    # Find where clues start
    across_start = None
    down_start = None
    
    for i, line in enumerate(lines):
        if line.strip().startswith('Across:'):
            across_start = i
        elif line.strip().startswith('Down:'):
            down_start = i
    
    # Extract grid (everything before clues)
    grid_end = across_start if across_start else len(lines)
    grid = []
    for i in range(grid_end):
        line = lines[i].strip()
        if line:
            grid.append(line.split())
    
    # Extract across clues
    across_clues = {}
    if across_start is not None:
        end_idx = down_start if down_start else len(lines)
        for i in range(across_start + 1, end_idx):
            line = lines[i].strip()
            if line:
                match = re.match(r'\s*(\d+)\.\s*(.+)', line)
                if match:
                    num = int(match.group(1))
                    clue = match.group(2)
                    across_clues[num] = clue
    
    # Extract down clues
    down_clues = {}
    if down_start is not None:
        for i in range(down_start + 1, len(lines)):
            line = lines[i].strip()
            if line:
                match = re.match(r'\s*(\d+)\.\s*(.+)', line)
                if match:
                    num = int(match.group(1))
                    clue = match.group(2)
                    down_clues[num] = clue
    
    return grid, across_clues, down_clues

def get_clue_positions(grid):
    """Determine numbered positions in crossword grid"""
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0
    
    positions = {}
    current_num = 1
    
    for row in range(height):
        for col in range(width):
            if grid[row][col] != '.':
                # Check if this starts an across word
                starts_across = (col == 0 or grid[row][col-1] == '.') and \
                               (col + 1 < width and grid[row][col+1] != '.')
                
                # Check if this starts a down word
                starts_down = (row == 0 or grid[row-1][col] == '.') and \
                             (row + 1 < height and grid[row+1][col] != '.')
                
                if starts_across or starts_down:
                    positions[current_num] = (row, col)
                    current_num += 1
    
    return positions

def get_word_length(grid, row, col, direction):
    """Get the length of a word starting at given position"""
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0
    
    length = 0
    if direction == 'across':
        while col + length < width and grid[row][col + length] != '.':
            length += 1
    else:  # down
        while row + length < height and grid[row + length][col] != '.':
            length += 1
    
    return length

def solve_crossword_holistically(grid, across_clues, down_clues):
    """Solve the entire crossword using LLM with structured output"""
    
    # Get positions and word lengths
    positions = get_clue_positions(grid)
    
    # Create clue info with lengths
    across_info = []
    down_info = []
    
    for num in sorted(across_clues.keys()):
        if num in positions:
            row, col = positions[num]
            length = get_word_length(grid, row, col, 'across')
            across_info.append(f"{num}. {across_clues[num]} ({length} letters)")
    
    for num in sorted(down_clues.keys()):
        if num in positions:
            row, col = positions[num]
            length = get_word_length(grid, row, col, 'down')
            down_info.append(f"{num}. {down_clues[num]} ({length} letters)")
    
    prompt = f"""Solve this crossword puzzle completely. The grid has {len(grid)} rows and {len(grid[0])} columns.

ACROSS CLUES:
{chr(10).join(across_info)}

DOWN CLUES:
{chr(10).join(down_info)}

Respond with ONLY the answers in this exact format:

ACROSS:
1. ANSWER
2. ANSWER
...

DOWN:
1. ANSWER
2. ANSWER
...

Each answer should be in ALL CAPITAL LETTERS with no spaces or punctuation."""
    
    try:
        response = execute_llm(prompt)
        logging.info(f"LLM response: {response}")
        return response
    except Exception as e:
        logging.error(f"Error solving crossword holistically: {e}")
        return None

def parse_llm_response(response, grid, across_clues, down_clues):
    """Parse LLM response and build the complete solution"""
    lines = response.strip().split('\n')
    
    across_answers = {}
    down_answers = {}
    current_section = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if line.upper().startswith('ACROSS'):
            current_section = 'across'
            continue
        elif line.upper().startswith('DOWN'):
            current_section = 'down'
            continue
            
        # Parse answer line
        match = re.match(r'\s*(\d+)\.\s*(.+)', line)
        if match:
            num = int(match.group(1))
            answer = ''.join(c for c in match.group(2).strip().upper() if c.isalpha())
            
            if current_section == 'across':
                across_answers[num] = answer
            elif current_section == 'down':
                down_answers[num] = answer
    
    # Build the filled grid
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0
    filled_grid = [row[:] for row in grid]  # Copy original grid
    
    positions = get_clue_positions(grid)
    
    # Fill in across answers
    for num, answer in across_answers.items():
        if num in positions:
            row, col = positions[num]
            for i, letter in enumerate(answer):
                if col + i < width and filled_grid[row][col + i] != '.':
                    filled_grid[row][col + i] = letter
    
    # Fill in down answers
    for num, answer in down_answers.items():
        if num in positions:
            row, col = positions[num]
            for i, letter in enumerate(answer):
                if row + i < height and filled_grid[row + i][col] != '.':
                    filled_grid[row + i][col] = letter
    
    # Format final output
    result = []
    
    # Add filled grid
    for row in filled_grid:
        result.append(' '.join(row))
    
    result.append('')  # Empty line
    
    # Add across answers
    result.append('Across:')
    for num in sorted(across_clues.keys()):
        if num in across_answers:
            result.append(f'  {num}. {across_answers[num]}')
        else:
            result.append(f'  {num}. UNKNOWN')
    
    result.append('')  # Empty line
    
    # Add down answers
    result.append('Down:')
    for num in sorted(down_clues.keys()):
        if num in down_answers:
            result.append(f'  {num}. {down_answers[num]}')
        else:
            result.append(f'  {num}. UNKNOWN')
    
    return '\n'.join(result)

def process_input(input_string: str) -> str:
    try:
        grid, across_clues, down_clues = parse_input(input_string)
        
        if not grid:
            return "Error: No grid found"
        
        logging.info(f"Parsed grid: {len(grid)} rows, {len(grid[0])} columns")
        logging.info(f"Across clues: {len(across_clues)}")
        logging.info(f"Down clues: {len(down_clues)}")
        
        # Solve the crossword holistically
        llm_response = solve_crossword_holistically(grid, across_clues, down_clues)
        
        if llm_response:
            return parse_llm_response(llm_response, grid, across_clues, down_clues)
        else:
            return "Error: Failed to solve crossword"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return f"Error: {str(e)}"