import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 115  # Leave buffer for safety
    
    try:
        # Parse input
        grid, across_clues, down_clues = parse_input(input_string)
        logging.info(f"Parsed {len(across_clues)} across clues and {len(down_clues)} down clues")
        
        # Solve clues with LLM
        across_answers = {}
        down_answers = {}
        
        # Solve across clues
        for clue_num, clue_text in across_clues.items():
            if time.time() - start_time > timeout:
                logging.warning("Timeout approaching, stopping clue solving")
                break
            answer = solve_clue(clue_text, clue_num, 'across', grid)
            if answer:
                across_answers[clue_num] = answer
                logging.info(f"Solved across {clue_num}: {answer}")
        
        # Solve down clues
        for clue_num, clue_text in down_clues.items():
            if time.time() - start_time > timeout:
                logging.warning("Timeout approaching, stopping clue solving")
                break
            answer = solve_clue(clue_text, clue_num, 'down', grid)
            if answer:
                down_answers[clue_num] = answer
                logging.info(f"Solved down {clue_num}: {answer}")
        
        # Create solution grid
        solution_grid = create_solution_grid(grid, across_answers, down_answers)
        
        # Format output
        result = format_solution(solution_grid, across_answers, down_answers)
        return result
        
    except Exception as e:
        logging.error(f"Error in process_input: {e}")
        return ""

def parse_input(input_string):
    """Parse the input to extract grid and clues"""
    lines = input_string.strip().split('\n')
    
    # Extract grid
    grid = []
    line_idx = 0
    while line_idx < len(lines) and not lines[line_idx].strip().startswith(('Across:', 'Down:')):
        if lines[line_idx].strip():
            grid.append(lines[line_idx].strip().split())
        line_idx += 1
    
    # Extract clues
    across_clues = {}
    down_clues = {}
    current_section = None
    
    for i in range(line_idx, len(lines)):
        line = lines[i].strip()
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
    
    return grid, across_clues, down_clues

def solve_clue(clue_text, clue_num, direction, grid):
    """Solve a single crossword clue using LLM"""
    # Find the length of the answer by looking at the grid
    clue_pos = find_clue_position(clue_num, grid, direction)
    if not clue_pos:
        logging.warning(f"Could not find position for clue {clue_num} {direction}")
        return None
    
    row, col = clue_pos
    length = get_word_length(grid, row, col, direction)
    
    # Create prompt for LLM
    prompt = f"""Solve this crossword clue. The answer is exactly {length} letters long.

Clue: {clue_text}

Respond with just the answer word in capital letters, no explanation or punctuation."""
    
    try:
        response = execute_llm(prompt)
        answer = response.strip().upper()
        
        # Clean the answer - remove non-alphabetic characters
        answer = ''.join(c for c in answer if c.isalpha())
        
        if len(answer) == length:
            return answer
        else:
            logging.warning(f"Answer length mismatch for clue {clue_num}: got {len(answer)}, expected {length}")
            
            # Try to extract the right length answer from the response
            words = response.split()
            for word in words:
                clean_word = ''.join(c for c in word.upper() if c.isalpha())
                if len(clean_word) == length:
                    return clean_word
            
    except Exception as e:
        logging.error(f"Error solving clue {clue_num}: {e}")
    
    return None

def find_clue_position(clue_num, grid, direction):
    """Find the starting position of a clue in the grid (same logic as scoring function)"""
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0
    
    current_num = 1
    
    for row in range(height):
        for col in range(width):
            if grid[row][col] == ".":
                continue
            
            starts_across = (
                (col == 0 or grid[row][col - 1] == ".")
                and col + 1 < width
                and grid[row][col + 1] != "."
            )
            starts_down = (
                (row == 0 or grid[row - 1][col] == ".")
                and row + 1 < height
                and grid[row + 1][col] != "."
            )
            
            if starts_across or starts_down:
                if current_num == clue_num:
                    return (row, col)
                current_num += 1
    
    return None

def get_word_length(grid, row, col, direction):
    """Get the length of a word starting at the given position"""
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

def create_solution_grid(grid, across_answers, down_answers):
    """Create the solution grid by filling in answers"""
    # Create a copy of the grid
    solution = [row[:] for row in grid]
    
    # Fill in across answers
    for clue_num, answer in across_answers.items():
        pos = find_clue_position(clue_num, grid, 'across')
        if pos:
            row, col = pos
            for i, letter in enumerate(answer):
                if col + i < len(solution[0]):
                    solution[row][col + i] = letter
    
    # Fill in down answers
    for clue_num, answer in down_answers.items():
        pos = find_clue_position(clue_num, grid, 'down')
        if pos:
            row, col = pos
            for i, letter in enumerate(answer):
                if row + i < len(solution):
                    solution[row + i][col] = letter
    
    return solution

def format_solution(grid, across_answers, down_answers):
    """Format the solution in the expected format"""
    # Format the grid
    grid_str = '\n'.join(' '.join(row) for row in grid)
    
    # Format across answers
    across_str = "Across:\n"
    for clue_num in sorted(across_answers.keys()):
        across_str += f"  {clue_num}. {across_answers[clue_num]}\n"
    
    # Format down answers
    down_str = "Down:\n"
    for clue_num in sorted(down_answers.keys()):
        down_str += f"  {clue_num}. {down_answers[clue_num]}\n"
    
    return f"{grid_str}\n\n{across_str}\n{down_str}"