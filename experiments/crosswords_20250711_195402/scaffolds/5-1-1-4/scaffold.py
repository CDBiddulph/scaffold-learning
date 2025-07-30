import logging
import re
from llm_executor import execute_llm

def parse_crossword_input(input_string):
    """Parse the input crossword puzzle into grid and clues"""
    lines = input_string.strip().split('\n')
    
    # Parse grid
    grid = []
    line_idx = 0
    while line_idx < len(lines):
        line = lines[line_idx].strip()
        if not line or line.startswith('Across:') or line.startswith('Down:'):
            break
        grid.append(line.split())
        line_idx += 1
    
    # Parse clues
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

def find_clue_position(clue_num, grid, direction):
    """Find the starting position of a clue in the grid based on crossword numbering"""
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

def get_clue_length(clue_num, grid, direction):
    """Get the length of a clue based on grid structure"""
    pos = find_clue_position(clue_num, grid, direction)
    if pos is None:
        return None
    
    row, col = pos
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0
    
    if direction == 'across':
        length = 0
        for c in range(col, width):
            if grid[row][c] == ".":
                break
            length += 1
        return length
    else:  # down
        length = 0
        for r in range(row, height):
            if grid[r][col] == ".":
                break
            length += 1
        return length

def solve_entire_crossword_robust(grid, across_clues, down_clues):
    """Solve the entire crossword puzzle holistically with robust parsing"""
    
    # Create a detailed, structured prompt
    prompt = """Solve this crossword puzzle completely. Fill in all empty squares (-) with letters.

GRID:
"""
    for row in grid:
        prompt += ' '.join(row) + '\n'
    
    prompt += "\nACROSS CLUES:\n"
    for num, clue in sorted(across_clues.items()):
        prompt += f"{num}. {clue}\n"
    
    prompt += "\nDOWN CLUES:\n"
    for num, clue in sorted(down_clues.items()):
        prompt += f"{num}. {clue}\n"
    
    prompt += """
INSTRUCTIONS:
1. Replace each - with the correct letter
2. Keep all . (black squares) unchanged
3. Make sure across and down words intersect correctly
4. Consider common crossword conventions and wordplay
5. Output ONLY the completed grid
6. Format: one row per line, letters/dots separated by single spaces

COMPLETED GRID:"""
    
    try:
        response = execute_llm(prompt)
        
        # More robust parsing
        lines = response.strip().split('\n')
        completed_grid = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Skip lines that contain explanatory text
            if any(word in line.lower() for word in ['grid', 'across', 'down', 'clue', 'answer', 'instructions', 'completed']):
                continue
            
            cells = line.split()
            if len(cells) == len(grid[0]):
                # Validate that all cells are single characters
                valid_cells = []
                for cell in cells:
                    if len(cell) == 1 and (cell.isalpha() or cell == '.'):
                        valid_cells.append(cell.upper())
                    else:
                        break
                
                if len(valid_cells) == len(cells):
                    completed_grid.append(valid_cells)
            
            if len(completed_grid) == len(grid):
                break
        
        if len(completed_grid) == len(grid):
            logging.info("Successfully solved crossword holistically")
            return completed_grid
        else:
            logging.warning(f"Holistic parsing failed: expected {len(grid)} rows, got {len(completed_grid)}")
            return None
            
    except Exception as e:
        logging.error(f"Holistic approach failed: {e}")
        return None

def solve_clue_with_context(clue_text, length=None, attempts=3):
    """Solve a single crossword clue with multiple strategies"""
    
    for attempt in range(attempts):
        # Try different prompting strategies
        if attempt == 0:
            prompt = f"Solve this crossword clue (consider wordplay, puns, abbreviations): {clue_text}"
        elif attempt == 1:
            prompt = f"This crossword clue may involve double meanings or tricks: {clue_text}"
        else:
            prompt = f"Think step by step about this crossword clue: {clue_text}"
        
        if length:
            prompt += f"\nThe answer must be exactly {length} letters long."
        
        prompt += "\nRespond with only the answer in UPPERCASE letters."
        
        try:
            response = execute_llm(prompt)
            answer = ''.join(c for c in response.strip().upper() if c.isalpha())
            
            if length and len(answer) != length:
                continue
            
            if len(answer) > 0:
                logging.info(f"Solved '{clue_text}' -> {answer}")
                return answer
                
        except Exception as e:
            logging.warning(f"Clue solving attempt {attempt} failed: {e}")
            continue
    
    logging.warning(f"Failed to solve clue: {clue_text}")
    return ""

def solve_crossword_iteratively(grid, across_clues, down_clues):
    """Solve crossword by solving clues iteratively with constraints"""
    
    # Get all clues with their lengths
    all_clues = []
    for clue_num, clue_text in across_clues.items():
        length = get_clue_length(clue_num, grid, 'across')
        if length:
            all_clues.append((clue_num, clue_text, 'across', length))
    
    for clue_num, clue_text in down_clues.items():
        length = get_clue_length(clue_num, grid, 'down')
        if length:
            all_clues.append((clue_num, clue_text, 'down', length))
    
    # Sort by length (shorter clues first, they're often easier)
    all_clues.sort(key=lambda x: x[3])
    
    # Solve clues
    solutions = {}
    for clue_num, clue_text, direction, length in all_clues:
        answer = solve_clue_with_context(clue_text, length)
        if answer:
            solutions[(clue_num, direction)] = answer
    
    # Build grid from solutions
    return build_grid_from_solutions(grid, solutions)

def build_grid_from_solutions(grid, solutions):
    """Build the completed crossword grid from individual solutions"""
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0
    completed = [row[:] for row in grid]  # Deep copy
    
    # Fill in across answers first
    for (clue_num, direction), answer in solutions.items():
        if direction == 'across':
            pos = find_clue_position(clue_num, grid, 'across')
            if pos:
                row, col = pos
                for i, letter in enumerate(answer):
                    if col + i < width and grid[row][col + i] != ".":
                        completed[row][col + i] = letter
    
    # Fill in down answers, allowing conflicts to be resolved by keeping across answers
    for (clue_num, direction), answer in solutions.items():
        if direction == 'down':
            pos = find_clue_position(clue_num, grid, 'down')
            if pos:
                row, col = pos
                conflicts = 0
                for i, letter in enumerate(answer):
                    if row + i < height and grid[row + i][col] != ".":
                        if completed[row + i][col] != "-" and completed[row + i][col] != letter:
                            conflicts += 1
                
                # Only fill if there are few conflicts
                if conflicts <= 1:
                    for i, letter in enumerate(answer):
                        if row + i < height and grid[row + i][col] != ".":
                            completed[row + i][col] = letter
    
    return completed

def process_input(input_string: str) -> str:
    try:
        grid, across_clues, down_clues = parse_crossword_input(input_string)
        logging.info(f"Parsed {len(across_clues)} across clues and {len(down_clues)} down clues")
        
        # Try holistic approach first with robust parsing
        completed_grid = solve_entire_crossword_robust(grid, across_clues, down_clues)
        
        # If holistic approach fails, use iterative approach
        if completed_grid is None:
            logging.info("Holistic approach failed, using iterative approach")
            completed_grid = solve_crossword_iteratively(grid, across_clues, down_clues)
        
        # Generate the complete solution format
        result = []
        
        # Add the grid
        for row in completed_grid:
            result.append(' '.join(row))
        
        result.append("")  # Empty line separator
        
        # Add across answers
        result.append("Across:")
        for clue_num in sorted(across_clues.keys()):
            # Extract the answer from the grid
            pos = find_clue_position(clue_num, grid, 'across')
            if pos:
                row, col = pos
                answer = ""
                for i in range(get_clue_length(clue_num, grid, 'across') or 0):
                    if col + i < len(completed_grid[0]) and completed_grid[row][col + i] != ".":
                        answer += completed_grid[row][col + i]
                result.append(f"  {clue_num}. {answer}")
        
        result.append("")  # Empty line separator
        
        # Add down answers
        result.append("Down:")
        for clue_num in sorted(down_clues.keys()):
            # Extract the answer from the grid
            pos = find_clue_position(clue_num, grid, 'down')
            if pos:
                row, col = pos
                answer = ""
                for i in range(get_clue_length(clue_num, grid, 'down') or 0):
                    if row + i < len(completed_grid) and completed_grid[row + i][col] != ".":
                        answer += completed_grid[row + i][col]
                result.append(f"  {clue_num}. {answer}")
        
        final_result = '\n'.join(result)
        logging.info("Generated complete solution with grid and clue answers")
        return final_result
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return ""