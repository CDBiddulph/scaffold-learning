import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    try:
        # First, try to solve the entire puzzle at once
        logging.info("Attempting to solve entire puzzle at once")
        
        prompt = f"""Solve this crossword puzzle completely. You need to:

1. Fill in the grid with the correct letters (replace dashes with letters, keep dots as black squares)
2. Replace each clue text with its answer in CAPITAL LETTERS
3. Keep the exact same format

Here's the puzzle:
{input_string}

Please solve it and return the complete solution in the exact same format:"""
        
        response = execute_llm(prompt)
        
        # Validate the response has the right structure
        if validate_response(response, input_string):
            logging.info("Successfully solved puzzle with single LLM call")
            return response.strip()
        else:
            logging.warning("Single LLM call failed, trying fallback approach")
            return solve_with_fallback(input_string)
        
    except Exception as e:
        logging.error(f"Error in main approach: {e}")
        return solve_with_fallback(input_string)

def validate_response(response, original_input):
    """Basic validation that the response has the right structure"""
    try:
        lines = response.strip().split('\n')
        
        # Check if it has both Across: and Down: sections
        has_across = any("Across:" in line for line in lines)
        has_down = any("Down:" in line for line in lines)
        
        if not (has_across and has_down):
            return False
        
        # Check if it has a grid (multiple lines with spaces)
        grid_lines = 0
        for line in lines:
            if line.strip() and not line.startswith("Across:") and not line.startswith("Down:") and not re.match(r'\s*\d+\.', line):
                if ' ' in line:
                    grid_lines += 1
        
        return grid_lines >= 5  # Reasonable minimum for a crossword grid
    except:
        return False

def solve_with_fallback(input_string):
    """Fallback approach: parse and solve clues individually"""
    try:
        logging.info("Using fallback approach")
        
        # Parse input
        grid, across_clues, down_clues = parse_input(input_string)
        answer_info = extract_answer_info(grid)
        
        logging.info(f"Found {len(across_clues)} across clues and {len(down_clues)} down clues")
        
        # Solve clues with better prompts
        solved_across = {}
        solved_down = {}
        
        # Solve across clues
        for clue_num, clue_text in across_clues.items():
            if clue_num in answer_info and 'across' in answer_info[clue_num]:
                length = answer_info[clue_num]['across']['length']
                answer = solve_single_clue(clue_text, length, clue_num)
                if answer:
                    solved_across[clue_num] = answer
                    logging.info(f"Solved across {clue_num}: {answer}")
        
        # Solve down clues
        for clue_num, clue_text in down_clues.items():
            if clue_num in answer_info and 'down' in answer_info[clue_num]:
                length = answer_info[clue_num]['down']['length']
                answer = solve_single_clue(clue_text, length, clue_num)
                if answer:
                    solved_down[clue_num] = answer
                    logging.info(f"Solved down {clue_num}: {answer}")
        
        # Format output
        return format_output(grid, solved_across, solved_down, answer_info)
        
    except Exception as e:
        logging.error(f"Error in fallback approach: {e}")
        return ""

def parse_input(input_string):
    """Parse input to extract grid and clues"""
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
    
    # Extract grid
    grid_lines = []
    for i in range(across_start):
        line = lines[i].strip()
        if line:
            grid_lines.append(line.split())
    
    # Extract clues
    across_clues = {}
    down_clues = {}
    
    for i in range(across_start + 1, down_start):
        line = lines[i].strip()
        if line:
            match = re.match(r'\s*(\d+)\.\s*(.+)', line)
            if match:
                clue_num = int(match.group(1))
                clue_text = match.group(2).strip()
                across_clues[clue_num] = clue_text
    
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
            if grid[row][col] == '.':
                continue
            
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
                    length = 0
                    for c in range(col, width):
                        if grid[row][c] == '.':
                            break
                        length += 1
                    answer_info[current_num] = answer_info.get(current_num, {})
                    answer_info[current_num]['across'] = {
                        'length': length,
                        'row': row,
                        'col': col
                    }
                
                if starts_down:
                    length = 0
                    for r in range(row, height):
                        if grid[r][col] == '.':
                            break
                        length += 1
                    answer_info[current_num] = answer_info.get(current_num, {})
                    answer_info[current_num]['down'] = {
                        'length': length,
                        'row': row,
                        'col': col
                    }
                
                current_num += 1
    
    return answer_info

def solve_single_clue(clue_text, length, clue_num):
    """Solve a single clue with a simple, effective prompt"""
    prompt = f"""Solve this crossword clue:

Clue {clue_num}: {clue_text}
Answer length: {length} letters

This is a crossword puzzle clue. Think about common crossword patterns, abbreviations, wordplay, and general knowledge.

Respond with ONLY the answer in capital letters, no explanations:"""
    
    try:
        response = execute_llm(prompt)
        answer = ''.join(c for c in response.strip().upper() if c.isalpha())
        
        if len(answer) == length:
            return answer
        else:
            logging.warning(f"Wrong length for clue {clue_num} '{clue_text}': got '{answer}' (len {len(answer)}), expected {length}")
            return None
            
    except Exception as e:
        logging.error(f"Error solving clue {clue_num} '{clue_text}': {e}")
        return None

def format_output(grid, solved_across, solved_down, answer_info):
    """Format the output with filled grid and answers"""
    # Create solution grid
    solution_grid = [row[:] for row in grid]
    
    # Fill in answers
    for clue_num, answer in solved_across.items():
        if clue_num in answer_info and 'across' in answer_info[clue_num]:
            info = answer_info[clue_num]['across']
            row, col = info['row'], info['col']
            for i, letter in enumerate(answer):
                if col + i < len(solution_grid[0]):
                    solution_grid[row][col + i] = letter
    
    for clue_num, answer in solved_down.items():
        if clue_num in answer_info and 'down' in answer_info[clue_num]:
            info = answer_info[clue_num]['down']
            row, col = info['row'], info['col']
            for i, letter in enumerate(answer):
                if row + i < len(solution_grid):
                    solution_grid[row + i][col] = letter
    
    # Format output
    result = ""
    
    # Add grid
    for row in solution_grid:
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