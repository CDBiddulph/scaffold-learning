import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    try:
        # Parse the input
        grid, across_clues, down_clues = parse_input(input_string)
        
        # Find clue positions and lengths
        clue_positions = find_clue_positions(grid)
        
        logging.info(f"Grid size: {len(grid)}x{len(grid[0]) if grid else 0}")
        logging.info(f"Found {len(across_clues)} across clues, {len(down_clues)} down clues")
        
        # Initialize solution grid
        solution_grid = [row[:] for row in grid]
        
        # Solve iteratively
        solved_across, solved_down = solve_iteratively(
            across_clues, down_clues, clue_positions, solution_grid
        )
        
        # Format output
        return format_output(solution_grid, solved_across, solved_down)
        
    except Exception as e:
        logging.error(f"Error processing crossword: {e}")
        return "Error: Could not solve crossword"

def parse_input(input_string):
    """Parse input to extract grid and clues"""
    lines = input_string.strip().split('\n')
    
    # Find clue sections
    across_start = None
    down_start = None
    
    for i, line in enumerate(lines):
        if line.strip() == "Across:":
            across_start = i
        elif line.strip() == "Down:":
            down_start = i
    
    if across_start is None or down_start is None:
        raise ValueError("Could not find clue sections")
    
    # Extract grid
    grid = []
    for i in range(across_start):
        line = lines[i].strip()
        if line:
            grid.append(line.split())
    
    # Extract clues
    across_clues = {}
    down_clues = {}
    
    # Parse across clues
    for i in range(across_start + 1, down_start):
        line = lines[i].strip()
        if line:
            match = re.match(r'\s*(\d+)\.\s*(.+)', line)
            if match:
                num = int(match.group(1))
                clue = match.group(2).strip()
                across_clues[num] = clue
    
    # Parse down clues
    for i in range(down_start + 1, len(lines)):
        line = lines[i].strip()
        if line:
            match = re.match(r'\s*(\d+)\.\s*(.+)', line)
            if match:
                num = int(match.group(1))
                clue = match.group(2).strip()
                down_clues[num] = clue
    
    return grid, across_clues, down_clues

def find_clue_positions(grid):
    """Find starting positions and lengths for all clues"""
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0
    
    clue_positions = {}
    current_num = 1
    
    for row in range(height):
        for col in range(width):
            if grid[row][col] == '.':
                continue
            
            # Check if this starts an across word
            starts_across = (
                (col == 0 or grid[row][col - 1] == '.') and
                col + 1 < width and grid[row][col + 1] != '.'
            )
            
            # Check if this starts a down word
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
                    clue_positions[current_num]['across'] = {
                        'row': row, 'col': col, 'length': length
                    }
                
                if starts_down:
                    # Calculate down length
                    length = 0
                    for r in range(row, height):
                        if grid[r][col] == '.':
                            break
                        length += 1
                    clue_positions[current_num]['down'] = {
                        'row': row, 'col': col, 'length': length
                    }
                
                current_num += 1
    
    return clue_positions

def solve_iteratively(across_clues, down_clues, clue_positions, solution_grid):
    """Solve clues iteratively using constraint propagation"""
    solved_across = {}
    solved_down = {}
    
    # Try multiple iterations
    for iteration in range(10):
        progress = False
        
        # Try to solve across clues
        for num, clue in across_clues.items():
            if num in solved_across:
                continue
                
            if num in clue_positions and 'across' in clue_positions[num]:
                pos_info = clue_positions[num]['across']
                constraints = get_constraints(solution_grid, pos_info, 'across')
                
                answer = solve_clue(clue, num, pos_info['length'], constraints)
                
                if answer and is_valid_answer(answer, pos_info['length'], constraints):
                    solved_across[num] = answer
                    place_answer(solution_grid, answer, pos_info, 'across')
                    logging.info(f"Solved {num}A: {answer}")
                    progress = True
        
        # Try to solve down clues
        for num, clue in down_clues.items():
            if num in solved_down:
                continue
                
            if num in clue_positions and 'down' in clue_positions[num]:
                pos_info = clue_positions[num]['down']
                constraints = get_constraints(solution_grid, pos_info, 'down')
                
                answer = solve_clue(clue, num, pos_info['length'], constraints)
                
                if answer and is_valid_answer(answer, pos_info['length'], constraints):
                    solved_down[num] = answer
                    place_answer(solution_grid, answer, pos_info, 'down')
                    logging.info(f"Solved {num}D: {answer}")
                    progress = True
        
        if not progress:
            break
        
        logging.info(f"Iteration {iteration + 1}: {len(solved_across)} across, {len(solved_down)} down")
    
    return solved_across, solved_down

def get_constraints(grid, pos_info, direction):
    """Get constraint letters from intersecting words"""
    constraints = {}
    row, col = pos_info['row'], pos_info['col']
    
    if direction == 'across':
        for i in range(pos_info['length']):
            if col + i < len(grid[0]):
                cell = grid[row][col + i]
                if cell != '-' and cell != '.':
                    constraints[i] = cell.upper()
    else:  # down
        for i in range(pos_info['length']):
            if row + i < len(grid):
                cell = grid[row + i][col]
                if cell != '-' and cell != '.':
                    constraints[i] = cell.upper()
    
    return constraints

def solve_clue(clue, num, length, constraints):
    """Solve a single clue with constraints"""
    constraint_text = ""
    if constraints:
        constraint_parts = []
        for pos, letter in constraints.items():
            constraint_parts.append(f"position {pos + 1}: {letter}")
        constraint_text = f"\nKnown letters: {', '.join(constraint_parts)}"
    
    # Try multiple prompt strategies
    prompts = [
        f"Solve this crossword clue. Answer must be exactly {length} letters.\n\nClue: {clue}\nLength: {length}{constraint_text}\n\nAnswer (uppercase letters only):",
        f"Crossword clue: {clue}\nAnswer length: {length} letters{constraint_text}\n\nWhat is the answer? Respond with just the word in capital letters:",
        f"Clue #{num}: {clue}\nThe answer is {length} letters long.{constraint_text}\n\nAnswer:",
    ]
    
    for prompt in prompts:
        try:
            response = execute_llm(prompt)
            answer = clean_answer(response)
            
            if answer and len(answer) == length and answer.isalpha():
                # Check constraints
                valid = True
                for pos, expected in constraints.items():
                    if pos < len(answer) and answer[pos] != expected:
                        valid = False
                        break
                
                if valid:
                    return answer
            
        except Exception as e:
            logging.warning(f"Error solving clue {num}: {e}")
    
    return None

def clean_answer(response):
    """Clean up LLM response to extract answer"""
    # Remove common prefixes and suffixes
    response = response.strip()
    
    # Remove quotes
    response = response.strip('"\'')
    
    # Look for uppercase words
    words = re.findall(r'[A-Z]+', response)
    if words:
        return words[0]
    
    # Try to find any word
    words = re.findall(r'[a-zA-Z]+', response)
    if words:
        return words[0].upper()
    
    return None

def is_valid_answer(answer, length, constraints):
    """Check if answer is valid given constraints"""
    if not answer or len(answer) != length:
        return False
    
    for pos, expected in constraints.items():
        if pos < len(answer) and answer[pos] != expected:
            return False
    
    return True

def place_answer(grid, answer, pos_info, direction):
    """Place answer in grid"""
    row, col = pos_info['row'], pos_info['col']
    
    if direction == 'across':
        for i, letter in enumerate(answer):
            if col + i < len(grid[0]):
                grid[row][col + i] = letter
    else:  # down
        for i, letter in enumerate(answer):
            if row + i < len(grid):
                grid[row + i][col] = letter

def format_output(grid, solved_across, solved_down):
    """Format output with grid and answers"""
    result = []
    
    # Add grid
    for row in grid:
        result.append(' '.join(row))
    
    result.append('')
    
    # Add across answers
    result.append('Across:')
    for num in sorted(solved_across.keys()):
        result.append(f'  {num}. {solved_across[num]}')
    
    result.append('')
    
    # Add down answers
    result.append('Down:')
    for num in sorted(solved_down.keys()):
        result.append(f'  {num}. {solved_down[num]}')
    
    return '\n'.join(result)