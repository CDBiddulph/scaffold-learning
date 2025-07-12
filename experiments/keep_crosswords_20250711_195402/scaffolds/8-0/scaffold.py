import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    try:
        # Parse the input to extract grid and clues
        grid, across_clues, down_clues = parse_input(input_string)
        
        # Extract answer lengths and positions from grid
        answer_info = extract_answer_info(grid)
        
        logging.info(f"Found {len(across_clues)} across clues and {len(down_clues)} down clues")
        logging.info(f"Extracted answer info for {len(answer_info)} total clues")
        
        # Initialize solution grid
        solution_grid = [row[:] for row in grid]  # Copy grid
        
        # Solve clues iteratively with constraints
        solved_across, solved_down = solve_clues_iteratively(
            across_clues, down_clues, answer_info, solution_grid
        )
        
        # Fill in the solution grid
        fill_solution_grid(solution_grid, solved_across, solved_down, answer_info)
        
        # Format output with both grid and clues
        result = format_output(solution_grid, solved_across, solved_down)
        
        return result
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "Error: Could not process input"

def parse_input(input_string):
    """Parse input to extract grid and clues"""
    lines = input_string.strip().split('\n')
    
    # Find where the clues start
    across_start = None
    down_start = None
    
    for i, line in enumerate(lines):
        if line.strip().startswith("Across:"):
            across_start = i
        elif line.strip().startswith("Down:"):
            down_start = i
    
    if across_start is None or down_start is None:
        raise ValueError("Could not find clues sections")
    
    # Extract grid (everything before clues)
    grid_lines = []
    for i in range(across_start):
        line = lines[i].strip()
        if line:
            grid_lines.append(line.split())
    
    # Extract clues
    across_clues = {}
    down_clues = {}
    
    # Parse across clues
    for i in range(across_start + 1, down_start):
        line = lines[i].strip()
        if line:
            match = re.match(r'\s*(\d+)\.\s*(.+)', line)
            if match:
                clue_num = int(match.group(1))
                clue_text = match.group(2).strip()
                across_clues[clue_num] = clue_text
    
    # Parse down clues  
    for i in range(down_start + 1, len(lines)):
        line = lines[i].strip()
        if line:
            match = re.match(r'\s*(\d+)\.\s*(.+)', line)
            if match:
                clue_num = int(match.group(1))
                clue_text = match.group(2).strip()
                down_clues[clue_num] = clue_text
    
    return grid_lines, across_clues, down_clues

def extract_answer_info(grid):
    """Extract answer lengths and positions from grid structure"""
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0
    
    answer_info = {}
    current_num = 1
    
    for row in range(height):
        for col in range(width):
            # Skip black squares
            if grid[row][col] == '.':
                continue
            
            # Check if this position starts a word
            starts_across = (
                (col == 0 or grid[row][col - 1] == '.') and
                col + 1 < width and grid[row][col + 1] != '.'
            )
            starts_down = (
                (row == 0 or grid[row - 1][col] == '.') and
                row + 1 < height and grid[row + 1][col] != '.'
            )
            
            if starts_across or starts_down:
                if starts_across:
                    # Calculate across length
                    length = 0
                    for c in range(col, width):
                        if grid[row][c] == '.':
                            break
                        length += 1
                    answer_info[current_num] = answer_info.get(current_num, {})
                    answer_info[current_num]['across'] = {
                        'length': length,
                        'row': row,
                        'col': col,
                        'direction': 'across'
                    }
                
                if starts_down:
                    # Calculate down length
                    length = 0
                    for r in range(row, height):
                        if grid[r][col] == '.':
                            break
                        length += 1
                    answer_info[current_num] = answer_info.get(current_num, {})
                    answer_info[current_num]['down'] = {
                        'length': length,
                        'row': row,
                        'col': col,
                        'direction': 'down'
                    }
                
                current_num += 1
    
    return answer_info

def solve_clues_iteratively(across_clues, down_clues, answer_info, grid):
    """Solve clues iteratively using intersection constraints"""
    solved_across = {}
    solved_down = {}
    
    # Keep track of grid state for intersections
    current_grid = [row[:] for row in grid]
    
    # Multiple passes to solve clues
    max_iterations = 5
    for iteration in range(max_iterations):
        logging.info(f"Iteration {iteration + 1}")
        
        # Solve across clues
        for clue_num, clue_text in across_clues.items():
            if clue_num in solved_across:
                continue
                
            if clue_num in answer_info and 'across' in answer_info[clue_num]:
                info = answer_info[clue_num]['across']
                constraints = get_intersection_constraints(
                    info['row'], info['col'], info['length'], 'across', current_grid
                )
                
                answer = solve_single_clue_with_constraints(
                    clue_text, clue_num, info['length'], constraints
                )
                
                if answer and len(answer) == info['length']:
                    solved_across[clue_num] = answer
                    fill_answer_in_grid(current_grid, answer, info)
                    logging.info(f"Solved across {clue_num}: {answer}")
        
        # Solve down clues
        for clue_num, clue_text in down_clues.items():
            if clue_num in solved_down:
                continue
                
            if clue_num in answer_info and 'down' in answer_info[clue_num]:
                info = answer_info[clue_num]['down']
                constraints = get_intersection_constraints(
                    info['row'], info['col'], info['length'], 'down', current_grid
                )
                
                answer = solve_single_clue_with_constraints(
                    clue_text, clue_num, info['length'], constraints
                )
                
                if answer and len(answer) == info['length']:
                    solved_down[clue_num] = answer
                    fill_answer_in_grid(current_grid, answer, info)
                    logging.info(f"Solved down {clue_num}: {answer}")
        
        # Check if we made progress
        total_solved = len(solved_across) + len(solved_down)
        logging.info(f"Total solved after iteration {iteration + 1}: {total_solved}")
        
        if total_solved == len(across_clues) + len(down_clues):
            break
    
    return solved_across, solved_down

def get_intersection_constraints(row, col, length, direction, grid):
    """Get constraint letters from intersecting answers"""
    constraints = {}
    
    if direction == 'across':
        for i in range(length):
            c = col + i
            if c < len(grid[0]) and grid[row][c] != '-':
                constraints[i] = grid[row][c].upper()
    else:  # down
        for i in range(length):
            r = row + i
            if r < len(grid) and grid[r][col] != '-':
                constraints[i] = grid[r][col].upper()
    
    return constraints

def solve_single_clue_with_constraints(clue_text, clue_num, length, constraints):
    """Solve a single clue with length and intersection constraints"""
    constraint_text = ""
    if constraints:
        constraint_parts = []
        for pos, letter in constraints.items():
            constraint_parts.append(f"position {pos + 1}: {letter}")
        constraint_text = f"\nKnown letters: {', '.join(constraint_parts)}"
    
    prompt = f"""Solve this crossword clue. The answer is exactly {length} letters long.

Clue {clue_num}: {clue_text}
Answer length: {length} letters{constraint_text}

Think about:
- The answer must be exactly {length} letters
- Common crossword patterns and abbreviations
- Word play, puns, multiple meanings
- Pop culture and general knowledge

Respond with ONLY the answer in capital letters, no explanations:"""
    
    try:
        response = execute_llm(prompt)
        answer = response.strip().upper()
        
        # Clean up the response
        answer = answer.strip('"').strip("'")
        
        # Remove any explanations - take first word
        words = answer.split()
        if words:
            answer = words[0]
        
        # Remove non-letter characters
        answer = ''.join(c for c in answer if c.isalpha())
        
        # Validate length and constraints
        if len(answer) != length:
            logging.warning(f"Answer '{answer}' has wrong length {len(answer)}, expected {length}")
            return None
        
        # Check constraints
        for pos, expected_letter in constraints.items():
            if pos < len(answer) and answer[pos] != expected_letter:
                logging.warning(f"Answer '{answer}' violates constraint at position {pos}: got {answer[pos]}, expected {expected_letter}")
                return None
        
        return answer
        
    except Exception as e:
        logging.error(f"Error solving clue '{clue_text}': {e}")
        return None

def fill_answer_in_grid(grid, answer, info):
    """Fill an answer into the grid"""
    row, col = info['row'], info['col']
    
    if info['direction'] == 'across':
        for i, letter in enumerate(answer):
            if col + i < len(grid[0]):
                grid[row][col + i] = letter
    else:  # down
        for i, letter in enumerate(answer):
            if row + i < len(grid):
                grid[row + i][col] = letter

def fill_solution_grid(grid, solved_across, solved_down, answer_info):
    """Fill all solved answers into the grid"""
    for clue_num, answer in solved_across.items():
        if clue_num in answer_info and 'across' in answer_info[clue_num]:
            fill_answer_in_grid(grid, answer, answer_info[clue_num]['across'])
    
    for clue_num, answer in solved_down.items():
        if clue_num in answer_info and 'down' in answer_info[clue_num]:
            fill_answer_in_grid(grid, answer, answer_info[clue_num]['down'])

def format_output(grid, solved_across, solved_down):
    """Format output with both grid and clues"""
    result = ""
    
    # Add grid
    for row in grid:
        result += " ".join(row) + "\n"
    
    result += "\n"
    
    # Add across clues
    result += "Across:\n"
    for clue_num in sorted(solved_across.keys()):
        result += f"  {clue_num}. {solved_across[clue_num]}\n"
    
    result += "\n"
    
    # Add down clues
    result += "Down:\n"
    for clue_num in sorted(solved_down.keys()):
        result += f"  {clue_num}. {solved_down[clue_num]}\n"
    
    return result