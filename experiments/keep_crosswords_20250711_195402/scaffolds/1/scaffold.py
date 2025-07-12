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

def solve_clue_with_context(clue_text, length, intersecting_letters=None):
    """Solve a clue with length constraint and any known intersecting letters"""
    
    context = f"The answer has exactly {length} letters."
    if intersecting_letters:
        letter_info = []
        for pos, letter in intersecting_letters.items():
            letter_info.append(f"position {pos+1}: {letter}")
        if letter_info:
            context += f" Known letters: {', '.join(letter_info)}"
    
    prompt = f"""Solve this crossword clue. {context}

Clue: {clue_text}

Think about crossword conventions like wordplay, abbreviations, puns, and double meanings. 
Respond with only the answer in uppercase letters, no spaces or punctuation."""
    
    try:
        response = execute_llm(prompt)
        answer = response.strip().upper()
        # Remove any non-letter characters
        answer = ''.join(c for c in answer if c.isalpha())
        if len(answer) == length:
            return answer
    except Exception as e:
        logging.error(f"Error solving clue '{clue_text}': {e}")
    
    return None

def solve_crossword_iteratively(grid, across_clues, down_clues):
    """Solve the crossword puzzle iteratively"""
    
    # Find clue positions and lengths
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0
    
    across_info = {}  # clue_num -> (row, col, length)
    down_info = {}    # clue_num -> (row, col, length)
    current_num = 1
    
    for row in range(height):
        for col in range(width):
            # Skip black squares
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
                if starts_across:
                    length = get_word_length(grid, row, col, 'across')
                    across_info[current_num] = (row, col, length)
                if starts_down:
                    length = get_word_length(grid, row, col, 'down')
                    down_info[current_num] = (row, col, length)
                current_num += 1
    
    # Initialize grid with blanks
    filled_grid = [row[:] for row in grid]
    for row in range(height):
        for col in range(width):
            if filled_grid[row][col] == '-':
                filled_grid[row][col] = ' '
    
    # Solve clues iteratively
    solved_across = {}
    solved_down = {}
    
    # First pass: solve clues without intersection constraints
    for clue_num, clue_text in across_clues.items():
        if clue_num in across_info:
            row, col, length = across_info[clue_num]
            answer = solve_clue_with_context(clue_text, length)
            if answer:
                solved_across[clue_num] = answer
                # Fill in the grid
                for i, letter in enumerate(answer):
                    if col + i < width:
                        filled_grid[row][col + i] = letter
    
    for clue_num, clue_text in down_clues.items():
        if clue_num in down_info:
            row, col, length = down_info[clue_num]
            answer = solve_clue_with_context(clue_text, length)
            if answer:
                solved_down[clue_num] = answer
                # Fill in the grid
                for i, letter in enumerate(answer):
                    if row + i < height:
                        filled_grid[row + i][col] = letter
    
    # Second pass: try to solve remaining clues with intersection constraints
    for clue_num, clue_text in across_clues.items():
        if clue_num not in solved_across and clue_num in across_info:
            row, col, length = across_info[clue_num]
            # Get intersecting letters
            intersecting_letters = {}
            for i in range(length):
                if col + i < width and filled_grid[row][col + i] != ' ':
                    intersecting_letters[i] = filled_grid[row][col + i]
            
            answer = solve_clue_with_context(clue_text, length, intersecting_letters)
            if answer:
                solved_across[clue_num] = answer
                # Fill in the grid
                for i, letter in enumerate(answer):
                    if col + i < width:
                        filled_grid[row][col + i] = letter
    
    for clue_num, clue_text in down_clues.items():
        if clue_num not in solved_down and clue_num in down_info:
            row, col, length = down_info[clue_num]
            # Get intersecting letters
            intersecting_letters = {}
            for i in range(length):
                if row + i < height and filled_grid[row + i][col] != ' ':
                    intersecting_letters[i] = filled_grid[row + i][col]
            
            answer = solve_clue_with_context(clue_text, length, intersecting_letters)
            if answer:
                solved_down[clue_num] = answer
                # Fill in the grid
                for i, letter in enumerate(answer):
                    if row + i < height:
                        filled_grid[row + i][col] = letter
    
    return filled_grid, solved_across, solved_down

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
        logging.info("Starting crossword puzzle solution")
        grid, across_clues, down_clues = parse_input(input_string)
        logging.info(f"Parsed grid: {len(grid)}x{len(grid[0]) if grid else 0}")
        logging.info(f"Across clues: {len(across_clues)}, Down clues: {len(down_clues)}")
        
        filled_grid, solved_across, solved_down = solve_crossword_iteratively(grid, across_clues, down_clues)
        logging.info(f"Solved {len(solved_across)} across clues and {len(solved_down)} down clues")
        
        result = format_output(filled_grid, solved_across, solved_down)
        return result
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return ""