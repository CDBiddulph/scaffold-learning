import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    try:
        lines = input_string.strip().split('\n')
        
        # Find where clues start
        across_start = -1
        for i, line in enumerate(lines):
            if line.strip().startswith('Across:'):
                across_start = i
                break
        
        if across_start == -1:
            logging.error("Could not find 'Across:' section")
            return input_string
        
        # Parse grid
        grid_lines = lines[:across_start]
        grid = []
        for line in grid_lines:
            line = line.strip()
            if line:
                grid.append(line.split())
        
        if not grid:
            logging.error("Empty grid")
            return input_string
        
        logging.info(f"Parsed grid: {len(grid)}x{len(grid[0]) if grid else 0}")
        
        # Parse clues
        clue_lines = lines[across_start:]
        across_clues, down_clues = parse_clues(clue_lines)
        
        logging.info(f"Parsed {len(across_clues)} across clues and {len(down_clues)} down clues")
        
        # Find clue positions and lengths
        clue_positions = find_all_clue_positions(grid)
        
        logging.info(f"Found {len(clue_positions)} clue positions")
        
        # Solve with multiple iterations and cross-checking
        solved_across, solved_down = solve_with_iterations(
            across_clues, down_clues, clue_positions, grid
        )
        
        logging.info(f"Solved {len(solved_across)} across and {len(solved_down)} down clues")
        
        # Fill grid with solutions
        filled_grid = fill_grid_with_solutions(grid, clue_positions, solved_across, solved_down)
        
        # Format output
        return format_crossword_output(filled_grid, solved_across, solved_down)
        
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

def find_all_clue_positions(grid):
    """Find all clue positions and their lengths using proper crossword numbering"""
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0
    
    clue_positions = {}
    current_num = 1
    
    for row in range(height):
        for col in range(width):
            if grid[row][col] == '.':
                continue
            
            # Check if this position starts an across word
            starts_across = (
                (col == 0 or grid[row][col - 1] == '.') and
                col + 1 < width and grid[row][col + 1] != '.'
            )
            
            # Check if this position starts a down word
            starts_down = (
                (row == 0 or grid[row - 1][col] == '.') and
                row + 1 < height and grid[row + 1][col] != '.'
            )
            
            if starts_across or starts_down:
                clue_positions[current_num] = {}
                
                if starts_across:
                    # Calculate across length
                    length = 0
                    for c in range(col, width):
                        if grid[row][c] == '.':
                            break
                        length += 1
                    clue_positions[current_num]['across'] = ((row, col), length)
                
                if starts_down:
                    # Calculate down length
                    length = 0
                    for r in range(row, height):
                        if grid[r][col] == '.':
                            break
                        length += 1
                    clue_positions[current_num]['down'] = ((row, col), length)
                
                current_num += 1
    
    return clue_positions

def solve_with_iterations(across_clues, down_clues, clue_positions, grid):
    """Solve clues with multiple iterations and cross-checking"""
    solved_across = {}
    solved_down = {}
    
    # Multiple solving passes
    for iteration in range(3):
        logging.info(f"Solving iteration {iteration + 1}")
        prev_across_count = len(solved_across)
        prev_down_count = len(solved_down)
        
        # Solve across clues
        for clue_num, clue_text in across_clues.items():
            if clue_num not in solved_across and clue_num in clue_positions and 'across' in clue_positions[clue_num]:
                pos, length = clue_positions[clue_num]['across']
                
                # Get crossing constraints from solved down clues
                constraints = get_crossing_constraints(clue_num, 'across', pos, length, clue_positions, solved_down)
                
                answer = solve_clue_with_constraints(clue_text, length, constraints, clue_num, 'across')
                if answer:
                    solved_across[clue_num] = answer
                    logging.info(f"Solved across {clue_num}: {clue_text} = {answer}")
        
        # Solve down clues  
        for clue_num, clue_text in down_clues.items():
            if clue_num not in solved_down and clue_num in clue_positions and 'down' in clue_positions[clue_num]:
                pos, length = clue_positions[clue_num]['down']
                
                # Get crossing constraints from solved across clues
                constraints = get_crossing_constraints(clue_num, 'down', pos, length, clue_positions, solved_across)
                
                answer = solve_clue_with_constraints(clue_text, length, constraints, clue_num, 'down')
                if answer:
                    solved_down[clue_num] = answer
                    logging.info(f"Solved down {clue_num}: {clue_text} = {answer}")
        
        # Check if we made progress
        if len(solved_across) == prev_across_count and len(solved_down) == prev_down_count:
            logging.info(f"No progress in iteration {iteration + 1}, stopping")
            break
    
    return solved_across, solved_down

def get_crossing_constraints(clue_num, direction, pos, length, clue_positions, other_solved):
    """Get letter constraints from crossing words"""
    constraints = {}  # position -> letter
    row, col = pos
    
    # Check each position for crossing constraints
    for i in range(length):
        if direction == 'across':
            check_row, check_col = row, col + i
        else:
            check_row, check_col = row + i, col
        
        # Find if there's a crossing word at this position
        for other_clue_num, other_answer in other_solved.items():
            if other_clue_num in clue_positions:
                other_dir = 'down' if direction == 'across' else 'across'
                if other_dir in clue_positions[other_clue_num]:
                    other_pos, other_length = clue_positions[other_clue_num][other_dir]
                    other_row, other_col = other_pos
                    
                    # Check if this position intersects
                    intersects = False
                    letter_idx = -1
                    
                    if other_dir == 'across':
                        if (other_row == check_row and 
                            other_col <= check_col < other_col + other_length):
                            intersects = True
                            letter_idx = check_col - other_col
                    else:  # other_dir == 'down'
                        if (other_col == check_col and 
                            other_row <= check_row < other_row + other_length):
                            intersects = True
                            letter_idx = check_row - other_row
                    
                    if intersects and 0 <= letter_idx < len(other_answer):
                        constraints[i] = other_answer[letter_idx]
                        logging.info(f"Constraint for {direction} {clue_num} pos {i}: {other_answer[letter_idx]} from {other_dir} {other_clue_num}")
    
    return constraints

def solve_clue_with_constraints(clue_text, length, constraints, clue_num, direction):
    """Solve a clue with letter constraints from crossing words"""
    
    # Try with constraints first if we have them
    if constraints:
        constraint_desc = []
        pattern = ['_'] * length
        for pos, letter in constraints.items():
            if 0 <= pos < length:
                pattern[pos] = letter
                constraint_desc.append(f"position {pos+1} is {letter}")
        
        pattern_str = ''.join(pattern)
        constraint_text = '; '.join(constraint_desc)
        
        prompt = f"""Solve this crossword clue with letter constraints.

Clue: {clue_text}
Length: {length} letters
Pattern: {pattern_str} (where _ means unknown letter)
Constraints: {constraint_text}

The answer must fit the exact pattern shown. Respond with ONLY the complete answer in capital letters, no explanation."""
        
        try:
            response = execute_llm(prompt).strip().upper()
            words = re.findall(r'[A-Z]+', response)
            
            for word in words:
                if len(word) == length and word.isalpha():
                    # Check if word satisfies all constraints
                    valid = True
                    for pos, required_letter in constraints.items():
                        if 0 <= pos < len(word) and word[pos] != required_letter:
                            valid = False
                            break
                    if valid:
                        return word
            
            logging.warning(f"No valid constrained answer found for {direction} {clue_num}")
        except Exception as e:
            logging.error(f"Error solving constrained clue: {e}")
    
    # Fall back to unconstrained solving with better prompts
    return solve_single_clue_improved(clue_text, length, clue_num, direction)

def solve_single_clue_improved(clue_text, length, clue_num, direction):
    """Improved clue solving with better prompting"""
    
    # Try multiple prompting strategies
    strategies = [
        f"""Crossword clue: {clue_text}
Answer length: {length} letters

Think step by step:
1. What type of clue is this? (definition, wordplay, abbreviation, etc.)
2. Are there any indicators or wordplay?
3. What's the most likely answer?

Respond with ONLY the answer in capital letters.""",

        f"""Solve this crossword clue:
{clue_text}
({length} letters)

Answer:""",

        f"""This is a crossword clue that needs exactly {length} letters:
"{clue_text}"

Common crossword answer:"""
    ]
    
    for i, prompt in enumerate(strategies):
        try:
            response = execute_llm(prompt).strip().upper()
            
            # Extract words and find the best match
            words = re.findall(r'[A-Z]+', response)
            
            # First try exact length matches
            for word in words:
                if len(word) == length and word.isalpha():
                    return word
            
            # For longer clues, try removing spaces and combining words
            if length > 10:
                combined = ''.join(words)
                if len(combined) == length and combined.isalpha():
                    return combined
            
        except Exception as e:
            logging.error(f"Error with strategy {i+1} for clue '{clue_text}': {e}")
    
    logging.warning(f"Failed to solve {direction} {clue_num}: {clue_text}")
    return None

def fill_grid_with_solutions(grid, clue_positions, solved_across, solved_down):
    """Fill the grid with solved answers"""
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0
    
    # Create a copy of the grid
    filled = [row[:] for row in grid]
    
    # Fill across answers
    for clue_num, answer in solved_across.items():
        if clue_num in clue_positions and 'across' in clue_positions[clue_num]:
            (row, col), length = clue_positions[clue_num]['across']
            for i, letter in enumerate(answer):
                if i < length and col + i < width:
                    filled[row][col + i] = letter
    
    # Fill down answers
    for clue_num, answer in solved_down.items():
        if clue_num in clue_positions and 'down' in clue_positions[clue_num]:
            (row, col), length = clue_positions[clue_num]['down']
            for i, letter in enumerate(answer):
                if i < length and row + i < height:
                    filled[row + i][col] = letter
    
    return filled

def format_crossword_output(filled_grid, solved_across, solved_down):
    """Format the output to match expected format"""
    result = []
    
    # Add grid
    for row in filled_grid:
        result.append(' '.join(row))
    
    result.append('')
    
    # Add across clues
    result.append('Across:')
    for clue_num in sorted(solved_across.keys()):
        result.append(f'  {clue_num}. {solved_across[clue_num]}')
    
    result.append('')
    
    # Add down clues
    result.append('Down:')
    for clue_num in sorted(solved_down.keys()):
        result.append(f'  {clue_num}. {solved_down[clue_num]}')
    
    return '\n'.join(result)