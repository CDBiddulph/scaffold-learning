import logging
import re
import time
from llm_executor import execute_llm

def parse_input(input_string):
    """Parse the input to extract grid and clues"""
    lines = input_string.strip().split('\n')
    
    # Find where grid ends and clues begin
    grid_lines = []
    clue_start = -1
    
    for i, line in enumerate(lines):
        if line.strip().startswith('Across:'):
            clue_start = i
            break
        if line.strip():
            grid_lines.append(line.strip().split())
    
    # Parse clues
    across_clues = {}
    down_clues = {}
    current_section = None
    
    for i in range(clue_start, len(lines)):
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
    
    return grid_lines, across_clues, down_clues

def get_clue_positions(grid):
    """Get positions and lengths for each clue number"""
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0
    
    clue_positions = {}
    current_num = 1
    
    for row in range(height):
        for col in range(width):
            if grid[row][col] == '.':
                continue
                
            starts_across = (
                (col == 0 or grid[row][col-1] == '.') and
                col + 1 < width and grid[row][col+1] != '.'
            )
            starts_down = (
                (row == 0 or grid[row-1][col] == '.') and
                row + 1 < height and grid[row+1][col] != '.'
            )
            
            if starts_across or starts_down:
                clue_positions[current_num] = {'row': row, 'col': col}
                
                if starts_across:
                    # Calculate across length
                    length = 0
                    for c in range(col, width):
                        if grid[row][c] == '.':
                            break
                        length += 1
                    clue_positions[current_num]['across_length'] = length
                
                if starts_down:
                    # Calculate down length
                    length = 0
                    for r in range(row, height):
                        if grid[r][col] == '.':
                            break
                        length += 1
                    clue_positions[current_num]['down_length'] = length
                
                current_num += 1
    
    return clue_positions

def solve_clue(clue_text, length):
    """Use LLM to solve a single clue"""
    prompt = f"""You are solving a crossword clue. Respond with ONLY the answer in capital letters, no explanation or punctuation.

Clue: {clue_text}
Length: {length} letters

Answer:"""
    
    try:
        response = execute_llm(prompt)
        answer = response.strip().upper()
        # Keep only letters
        answer = ''.join(c for c in answer if c.isalpha())
        return answer if len(answer) == length else None
    except Exception as e:
        logging.error(f"Error solving clue '{clue_text}': {e}")
        return None

def solve_clue_with_constraints(clue_text, length, pattern=None):
    """Solve clue with known letters as constraints"""
    pattern_str = ""
    if pattern:
        pattern_str = f"\nKnown letters: {pattern} (use _ for unknown)"
    
    prompt = f"""Solve this crossword clue. Respond with ONLY the answer in capital letters, no explanation.

Clue: {clue_text}
Length: {length} letters{pattern_str}

Answer:"""
    
    try:
        response = execute_llm(prompt)
        answer = response.strip().upper()
        answer = ''.join(c for c in answer if c.isalpha())
        return answer if len(answer) == length else None
    except Exception as e:
        logging.error(f"Error solving clue with constraints '{clue_text}': {e}")
        return None

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Parse input
        grid, across_clues, down_clues = parse_input(input_string)
        clue_positions = get_clue_positions(grid)
        
        # Initialize solution grid
        height = len(grid)
        width = len(grid[0]) if height > 0 else 0
        solution_grid = [row[:] for row in grid]  # Copy grid
        
        # Track solved answers
        across_answers = {}
        down_answers = {}
        
        # First pass: solve clues without constraints
        logging.info("Solving across clues...")
        for clue_num, clue_text in across_clues.items():
            if time.time() - start_time > 100:  # Leave 20 seconds buffer
                break
                
            if clue_num in clue_positions and 'across_length' in clue_positions[clue_num]:
                length = clue_positions[clue_num]['across_length']
                answer = solve_clue(clue_text, length)
                if answer and len(answer) == length:
                    across_answers[clue_num] = answer
                    logging.info(f"Solved across {clue_num}: {answer}")
                    
                    # Fill in grid
                    row = clue_positions[clue_num]['row']
                    col = clue_positions[clue_num]['col']
                    for i, letter in enumerate(answer):
                        if col + i < width and solution_grid[row][col + i] != '.':
                            solution_grid[row][col + i] = letter
        
        logging.info("Solving down clues...")
        for clue_num, clue_text in down_clues.items():
            if time.time() - start_time > 100:  # Leave 20 seconds buffer
                break
                
            if clue_num in clue_positions and 'down_length' in clue_positions[clue_num]:
                length = clue_positions[clue_num]['down_length']
                answer = solve_clue(clue_text, length)
                if answer and len(answer) == length:
                    down_answers[clue_num] = answer
                    logging.info(f"Solved down {clue_num}: {answer}")
                    
                    # Fill in grid
                    row = clue_positions[clue_num]['row']
                    col = clue_positions[clue_num]['col']
                    for i, letter in enumerate(answer):
                        if row + i < height and solution_grid[row + i][col] != '.':
                            solution_grid[row + i][col] = letter
        
        # Second pass: try to solve remaining clues with constraints
        logging.info("Second pass with constraints...")
        for clue_num, clue_text in across_clues.items():
            if time.time() - start_time > 100:
                break
                
            if clue_num not in across_answers and clue_num in clue_positions and 'across_length' in clue_positions[clue_num]:
                length = clue_positions[clue_num]['across_length']
                row = clue_positions[clue_num]['row']
                col = clue_positions[clue_num]['col']
                
                # Build pattern with known letters
                pattern = []
                for i in range(length):
                    if col + i < width and solution_grid[row][col + i] != '-':
                        pattern.append(solution_grid[row][col + i])
                    else:
                        pattern.append('_')
                
                pattern_str = ''.join(pattern)
                if '_' in pattern_str:  # Only if we have some constraints
                    answer = solve_clue_with_constraints(clue_text, length, pattern_str)
                    if answer and len(answer) == length:
                        across_answers[clue_num] = answer
                        logging.info(f"Solved across {clue_num} with constraints: {answer}")
        
        for clue_num, clue_text in down_clues.items():
            if time.time() - start_time > 100:
                break
                
            if clue_num not in down_answers and clue_num in clue_positions and 'down_length' in clue_positions[clue_num]:
                length = clue_positions[clue_num]['down_length']
                row = clue_positions[clue_num]['row']
                col = clue_positions[clue_num]['col']
                
                # Build pattern with known letters
                pattern = []
                for i in range(length):
                    if row + i < height and solution_grid[row + i][col] != '-':
                        pattern.append(solution_grid[row + i][col])
                    else:
                        pattern.append('_')
                
                pattern_str = ''.join(pattern)
                if '_' in pattern_str:  # Only if we have some constraints
                    answer = solve_clue_with_constraints(clue_text, length, pattern_str)
                    if answer and len(answer) == length:
                        down_answers[clue_num] = answer
                        logging.info(f"Solved down {clue_num} with constraints: {answer}")
        
        # Format output
        result = []
        
        # Add original grid (the scoring function can handle this)
        for row in grid:
            result.append(' '.join(row))
        
        result.append('')  # Empty line
        
        # Add across clues
        result.append('Across:')
        for clue_num in sorted(across_answers.keys()):
            result.append(f'  {clue_num}. {across_answers[clue_num]}')
        
        result.append('')  # Empty line
        
        # Add down clues
        result.append('Down:')
        for clue_num in sorted(down_answers.keys()):
            result.append(f'  {clue_num}. {down_answers[clue_num]}')
        
        logging.info(f"Solved {len(across_answers)} across and {len(down_answers)} down clues")
        return '\n'.join(result)
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return ""