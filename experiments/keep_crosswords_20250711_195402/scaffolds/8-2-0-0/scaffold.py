import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    try:
        # Try to solve the entire puzzle at once with the LLM
        prompt = f"""You are an expert crossword puzzle solver. Please solve this crossword puzzle completely.

The input contains:
1. A grid where "-" represents empty squares and "." represents black squares
2. Across clues numbered according to standard crossword conventions
3. Down clues numbered according to standard crossword conventions

Please return the solution in this exact format:
1. The completed grid (replace "-" with letters, keep "." as black squares)
2. A blank line
3. "Across:" followed by numbered answers
4. A blank line  
5. "Down:" followed by numbered answers

Make sure:
- All answers fit the grid properly
- Across and down answers intersect correctly
- Use only capital letters in answers
- All clues are solved

Here is the puzzle:

{input_string}"""

        response = execute_llm(prompt)
        
        # Validate and clean up the response
        if response and len(response.strip()) > 0:
            # Clean up the response to ensure proper formatting
            cleaned_response = clean_response(response)
            logging.info("Successfully solved crossword puzzle")
            return cleaned_response
        else:
            logging.error("Empty response from LLM")
            return "Error: Empty response from solver"
            
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        # Fallback to partial solving if complete solving fails
        return fallback_solve(input_string)

def clean_response(response):
    """Clean up the LLM response to ensure proper formatting"""
    lines = response.strip().split('\n')
    cleaned_lines = []
    
    for line in lines:
        line = line.strip()
        if line:
            # Ensure answers are in uppercase
            if line.startswith(('Across:', 'Down:')):
                cleaned_lines.append(line)
            elif re.match(r'\s*\d+\.\s*', line):
                # This is a clue answer line - uppercase the answer part
                match = re.match(r'(\s*\d+\.\s*)(.+)', line)
                if match:
                    prefix = match.group(1)
                    answer = match.group(2).strip().upper()
                    cleaned_lines.append(f"{prefix}{answer}")
                else:
                    cleaned_lines.append(line)
            else:
                # This might be a grid line - uppercase any letters
                cleaned_line = ' '.join(cell.upper() if cell.isalpha() else cell for cell in line.split())
                cleaned_lines.append(cleaned_line)
    
    return '\n'.join(cleaned_lines)

def fallback_solve(input_string):
    """Fallback method using the original approach but with improvements"""
    try:
        # Parse the input
        grid = parse_grid_structure(input_string)
        clue_positions = number_grid(grid) if grid else {}
        across_clues, down_clues = parse_clues(input_string)
        
        logging.info(f"Fallback: Found {len(across_clues)} across clues and {len(down_clues)} down clues")
        
        # Solve only the clues we're most confident about
        solved_across = solve_confident_clues(across_clues, "across", grid, clue_positions)
        solved_down = solve_confident_clues(down_clues, "down", grid, clue_positions)
        
        # Reconstruct and format output
        filled_grid = reconstruct_grid(grid, clue_positions, solved_across, solved_down)
        result = ""
        if filled_grid:
            result = format_grid(filled_grid) + "\n\n"
        
        result += "Across:\n"
        for clue_num in sorted(solved_across.keys()):
            result += f"  {clue_num}. {solved_across[clue_num]}\n"
        
        result += "\nDown:\n"
        for clue_num in sorted(solved_down.keys()):
            result += f"  {clue_num}. {solved_down[clue_num]}\n"
        
        return result
        
    except Exception as e:
        logging.error(f"Fallback solve failed: {e}")
        return "Error: Could not solve puzzle"

def solve_confident_clues(clues, direction, grid, clue_positions):
    """Solve only clues we're confident about"""
    solved = {}
    
    # Solve each clue individually with enhanced prompting
    for clue_num, clue_text in clues.items():
        length = get_answer_length(clue_num, direction, grid, clue_positions)
        
        if length:
            answer = solve_single_clue_carefully(clue_text, length)
            if answer and len(answer) == length:
                solved[clue_num] = answer
                logging.info(f"Confidently solved {direction} {clue_num}: {clue_text} = {answer}")
    
    return solved

def solve_single_clue_carefully(clue_text, expected_length):
    """Solve a single clue with very careful prompting"""
    prompt = f"""Solve this crossword clue. This is a standard crossword puzzle clue.

Clue: {clue_text}
Answer length: {expected_length} letters

Think step by step:
1. What type of clue is this? (definition, wordplay, etc.)
2. What are the key words in the clue?
3. What common crossword answers fit this pattern?

The answer must be exactly {expected_length} letters long.
Common crossword conventions apply.

Respond with ONLY the answer in capital letters, no other text."""
    
    try:
        response = execute_llm(prompt)
        answer = response.strip().upper()
        # Remove any non-letter characters
        answer = re.sub(r'[^A-Z]', '', answer)
        
        if len(answer) == expected_length:
            return answer
        else:
            logging.warning(f"Length mismatch for clue '{clue_text}': expected {expected_length}, got {len(answer)}")
            return None
            
    except Exception as e:
        logging.error(f"Error solving clue '{clue_text}': {e}")
        return None

# Include the necessary parsing functions from the original code
def parse_grid_structure(input_string):
    """Parse the grid layout from the input"""
    lines = input_string.strip().split('\n')
    grid = []
    
    for line in lines:
        line = line.strip()
        if line.startswith("Across:") or line.startswith("Down:"):
            break
        if line and ('-' in line or '.' in line):
            grid.append(line.split())
    
    return grid

def number_grid(grid):
    """Number the grid squares according to crossword rules"""
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0
    
    clue_positions = {}
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
                clue_positions[current_num] = (row, col)
                current_num += 1
    
    return clue_positions

def get_answer_length(clue_num, direction, grid, clue_positions):
    """Determine the expected length of an answer based on grid structure"""
    if not grid or clue_num not in clue_positions:
        return None
    
    start_row, start_col = clue_positions[clue_num]
    length = 0
    
    if direction == "across":
        col = start_col
        while col < len(grid[0]) and grid[start_row][col] != ".":
            length += 1
            col += 1
    else:  # down
        row = start_row
        while row < len(grid) and grid[row][start_col] != ".":
            length += 1
            row += 1
    
    return length if length > 1 else None

def parse_clues(input_string):
    """Parse across and down clues from input"""
    lines = input_string.strip().split('\n')
    
    across_start = None
    down_start = None
    
    for i, line in enumerate(lines):
        if line.strip().startswith("Across:"):
            across_start = i
        elif line.strip().startswith("Down:"):
            down_start = i
    
    if across_start is None or down_start is None:
        raise ValueError("Could not find clues sections")
    
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
    
    return across_clues, down_clues

def reconstruct_grid(grid, clue_positions, solved_across, solved_down):
    """Reconstruct the filled grid from solved clues"""
    if not grid:
        return []
    
    filled_grid = [row[:] for row in grid]  # Deep copy
    
    # Fill in across answers
    for clue_num, answer in solved_across.items():
        if clue_num in clue_positions:
            row, col = clue_positions[clue_num]
            for i, letter in enumerate(answer):
                if (col + i < len(filled_grid[0]) and 
                    filled_grid[row][col + i] != "."):
                    filled_grid[row][col + i] = letter
    
    # Fill in down answers
    for clue_num, answer in solved_down.items():
        if clue_num in clue_positions:
            row, col = clue_positions[clue_num]
            for i, letter in enumerate(answer):
                if (row + i < len(filled_grid) and 
                    filled_grid[row + i][col] != "."):
                    if filled_grid[row + i][col] == "-" or filled_grid[row + i][col] == letter:
                        filled_grid[row + i][col] = letter
    
    return filled_grid

def format_grid(grid):
    """Format grid for output"""
    if not grid:
        return ""
    return "\n".join(" ".join(row) for row in grid)