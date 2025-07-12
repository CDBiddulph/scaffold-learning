import logging
import re
from llm_executor import execute_llm

def parse_input(input_string: str):
    """Parse the input to extract grid and clues"""
    lines = input_string.strip().split('\n')
    
    # Find where the grid ends and clues begin
    grid_lines = []
    clues_start = 0
    
    for i, line in enumerate(lines):
        if line.strip().startswith('Across:'):
            clues_start = i
            break
        grid_lines.append(line)
    
    # Parse grid
    grid = []
    for line in grid_lines:
        if line.strip():
            grid.append(line.strip().split())
    
    # Parse clues
    across_clues = {}
    down_clues = {}
    
    current_section = None
    for i in range(clues_start, len(lines)):
        line = lines[i].strip()
        if line.startswith('Across:'):
            current_section = 'across'
        elif line.startswith('Down:'):
            current_section = 'down'
        elif line and current_section:
            # Parse clue
            match = re.match(r'\s*(\d+)\.\s*(.+)', line)
            if match:
                clue_num = int(match.group(1))
                clue_text = match.group(2).strip()
                if current_section == 'across':
                    across_clues[clue_num] = clue_text
                else:
                    down_clues[clue_num] = clue_text
    
    return grid, across_clues, down_clues

def solve_crossword_holistically(grid, across_clues, down_clues):
    """Solve the crossword using a holistic approach"""
    
    # Create a string representation of the puzzle for the LLM
    grid_str = '\n'.join(' '.join(row) for row in grid)
    
    across_str = '\n'.join(f"  {num}. {clue}" for num, clue in sorted(across_clues.items()))
    down_str = '\n'.join(f"  {num}. {clue}" for num, clue in sorted(down_clues.items()))
    
    puzzle_str = f"""Grid:
{grid_str}

Across:
{across_str}

Down:
{down_str}"""
    
    prompt = f"""You are solving a crossword puzzle. Here is the puzzle:

{puzzle_str}

In the grid:
- "." represents black squares
- "-" represents empty squares to be filled

Your task is to solve all the clues and fill in the grid completely.

Important crossword conventions:
- Clues ending with "?" often involve wordplay or puns
- "e.g." means "for example" 
- Abbreviations are common
- Think about multiple meanings of words
- Common crossword answers are preferred
- All intersections must match

Please provide your solution in exactly this format:

[Grid with all letters filled in]

Across:
  [number]. [ANSWER]
  [number]. [ANSWER]
  ...

Down:
  [number]. [ANSWER]
  [number]. [ANSWER]
  ...

Make sure every answer is in UPPERCASE and every intersection is correct."""

    try:
        response = execute_llm(prompt)
        return parse_llm_solution(response, grid, across_clues, down_clues)
    except Exception as e:
        logging.error(f"Error in holistic solving: {e}")
        return solve_crossword_fallback(grid, across_clues, down_clues)

def parse_llm_solution(response, original_grid, across_clues, down_clues):
    """Parse the LLM's solution response"""
    try:
        lines = response.strip().split('\n')
        
        # Find grid section
        grid_lines = []
        current_section = None
        solved_across = {}
        solved_down = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if line.startswith('Across:'):
                current_section = 'across'
                continue
            elif line.startswith('Down:'):
                current_section = 'down'
                continue
            elif current_section == 'across':
                match = re.match(r'\s*(\d+)\.\s*(.+)', line)
                if match:
                    clue_num = int(match.group(1))
                    answer = match.group(2).strip().upper()
                    answer = ''.join(c for c in answer if c.isalpha())
                    solved_across[clue_num] = answer
            elif current_section == 'down':
                match = re.match(r'\s*(\d+)\.\s*(.+)', line)
                if match:
                    clue_num = int(match.group(1))
                    answer = match.group(2).strip().upper()
                    answer = ''.join(c for c in answer if c.isalpha())
                    solved_down[clue_num] = answer
            elif current_section is None:
                # This should be grid
                if '.' in line or any(c.isalpha() for c in line):
                    grid_lines.append(line.split())
        
        # Parse grid
        filled_grid = []
        for row in grid_lines:
            if row:
                filled_grid.append(row)
        
        # If we don't have a good grid, reconstruct from clues
        if not filled_grid or len(filled_grid) != len(original_grid):
            filled_grid = reconstruct_grid_from_clues(original_grid, solved_across, solved_down)
        
        return filled_grid, solved_across, solved_down
        
    except Exception as e:
        logging.error(f"Error parsing LLM solution: {e}")
        return solve_crossword_fallback(original_grid, across_clues, down_clues)

def reconstruct_grid_from_clues(original_grid, solved_across, solved_down):
    """Reconstruct the grid from solved clues"""
    height = len(original_grid)
    width = len(original_grid[0]) if height > 0 else 0
    
    # Initialize grid
    filled_grid = [row[:] for row in original_grid]
    for row in range(height):
        for col in range(width):
            if filled_grid[row][col] == '-':
                filled_grid[row][col] = ' '
    
    # Find clue positions
    across_info = {}
    down_info = {}
    current_num = 1
    
    for row in range(height):
        for col in range(width):
            if original_grid[row][col] == '.':
                continue
            
            starts_across = (
                (col == 0 or original_grid[row][col - 1] == '.')
                and col + 1 < width
                and original_grid[row][col + 1] != '.'
            )
            starts_down = (
                (row == 0 or original_grid[row - 1][col] == '.')
                and row + 1 < height
                and original_grid[row + 1][col] != '.'
            )
            
            if starts_across or starts_down:
                if starts_across:
                    length = get_word_length(original_grid, row, col, 'across')
                    across_info[current_num] = (row, col, length)
                if starts_down:
                    length = get_word_length(original_grid, row, col, 'down')
                    down_info[current_num] = (row, col, length)
                current_num += 1
    
    # Fill in across answers
    for clue_num, answer in solved_across.items():
        if clue_num in across_info:
            row, col, length = across_info[clue_num]
            for i, letter in enumerate(answer):
                if i < length and col + i < width:
                    filled_grid[row][col + i] = letter
    
    # Fill in down answers
    for clue_num, answer in solved_down.items():
        if clue_num in down_info:
            row, col, length = down_info[clue_num]
            for i, letter in enumerate(answer):
                if i < length and row + i < height:
                    filled_grid[row + i][col] = letter
    
    return filled_grid

def get_word_length(grid, row, col, direction):
    """Get the length of a word starting at (row, col) in the given direction"""
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0
    
    length = 0
    if direction == 'across':
        for c in range(col, width):
            if grid[row][c] == '.':
                break
            length += 1
    else:  # down
        for r in range(row, height):
            if grid[r][col] == '.':
                break
            length += 1
    
    return length

def solve_crossword_fallback(grid, across_clues, down_clues):
    """Fallback to iterative solving if holistic approach fails"""
    
    # Find clue positions and lengths
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0
    
    across_info = {}
    down_info = {}
    current_num = 1
    
    for row in range(height):
        for col in range(width):
            if grid[row][col] == '.':
                continue
            
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
                if starts_across:
                    length = get_word_length(grid, row, col, 'across')
                    across_info[current_num] = (row, col, length)
                if starts_down:
                    length = get_word_length(grid, row, col, 'down')
                    down_info[current_num] = (row, col, length)
                current_num += 1
    
    # Initialize grid
    filled_grid = [row[:] for row in grid]
    for row in range(height):
        for col in range(width):
            if filled_grid[row][col] == '-':
                filled_grid[row][col] = ' '
    
    # Solve clues
    solved_across = {}
    solved_down = {}
    
    # Solve each clue individually with better prompting
    for clue_num, clue_text in across_clues.items():
        if clue_num in across_info:
            row, col, length = across_info[clue_num]
            answer = solve_single_clue(clue_text, length)
            if answer:
                solved_across[clue_num] = answer
                for i, letter in enumerate(answer):
                    if col + i < width:
                        filled_grid[row][col + i] = letter
    
    for clue_num, clue_text in down_clues.items():
        if clue_num in down_info:
            row, col, length = down_info[clue_num]
            answer = solve_single_clue(clue_text, length)
            if answer:
                solved_down[clue_num] = answer
                for i, letter in enumerate(answer):
                    if row + i < height:
                        filled_grid[row + i][col] = letter
    
    return filled_grid, solved_across, solved_down

def solve_single_clue(clue_text, length):
    """Solve a single clue with improved prompting"""
    
    prompt = f"""Solve this crossword clue:

Clue: "{clue_text}"
Length: {length} letters

This is a standard crossword puzzle clue. Consider:
- Wordplay and puns (especially if clue ends with "?")
- Multiple meanings of words
- Common crossword answers
- Abbreviations and acronyms
- Pop culture references

Respond with ONLY the answer in uppercase letters."""
    
    try:
        response = execute_llm(prompt)
        answer = response.strip().upper()
        answer = ''.join(c for c in answer if c.isalpha())
        
        if len(answer) == length:
            return answer
    except Exception as e:
        logging.error(f"Error solving clue '{clue_text}': {e}")
    
    return None

def format_output(filled_grid, solved_across, solved_down):
    """Format the output as expected"""
    result = []
    
    # Add grid
    for row in filled_grid:
        result.append(' '.join(row))
    
    result.append('')  # Empty line
    
    # Add across clues
    result.append('Across:')
    for clue_num in sorted(solved_across.keys()):
        result.append(f'  {clue_num}. {solved_across[clue_num]}')
    
    result.append('')  # Empty line
    
    # Add down clues
    result.append('Down:')
    for clue_num in sorted(solved_down.keys()):
        result.append(f'  {clue_num}. {solved_down[clue_num]}')
    
    return '\n'.join(result)

def process_input(input_string: str) -> str:
    try:
        logging.info("Starting crossword puzzle solution with holistic approach")
        grid, across_clues, down_clues = parse_input(input_string)
        logging.info(f"Parsed grid: {len(grid)}x{len(grid[0]) if grid else 0}")
        logging.info(f"Across clues: {len(across_clues)}, Down clues: {len(down_clues)}")
        
        filled_grid, solved_across, solved_down = solve_crossword_holistically(grid, across_clues, down_clues)
        logging.info(f"Solved {len(solved_across)} across clues and {len(solved_down)} down clues")
        
        result = format_output(filled_grid, solved_across, solved_down)
        return result
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return ""