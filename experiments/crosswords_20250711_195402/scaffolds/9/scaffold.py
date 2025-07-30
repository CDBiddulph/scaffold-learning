import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    try:
        # Parse input
        lines = input_string.strip().split('\n')
        
        # Find where grid ends and clues begin
        grid_lines = []
        line_idx = 0
        while line_idx < len(lines):
            line = lines[line_idx].strip()
            if line.startswith("Across:") or line.startswith("Down:"):
                break
            grid_lines.append(line.split())
            line_idx += 1
        
        # Parse clues
        across_clues = {}
        down_clues = {}
        
        current_section = None
        for i in range(line_idx, len(lines)):
            line = lines[i].strip()
            if line.startswith("Across:"):
                current_section = "across"
            elif line.startswith("Down:"):
                current_section = "down"
            elif line and current_section:
                # Parse clue line
                match = re.match(r"\s*(\d+)\.\s*(.+)", line)
                if match:
                    clue_num = int(match.group(1))
                    clue_text = match.group(2).strip()
                    if current_section == "across":
                        across_clues[clue_num] = clue_text
                    else:
                        down_clues[clue_num] = clue_text
        
        logging.info(f"Parsed {len(across_clues)} across clues and {len(down_clues)} down clues")
        
        # Create grid structure and find clue positions
        height = len(grid_lines)
        width = len(grid_lines[0]) if height > 0 else 0
        
        # Find clue positions and lengths
        clue_positions = find_clue_positions(grid_lines)
        
        # Initialize solution grid
        solution_grid = [row[:] for row in grid_lines]
        
        # Try to solve clues using LLM with length constraints
        solved_across = {}
        solved_down = {}
        
        # Solve across clues
        for clue_num, clue_text in across_clues.items():
            if clue_num in clue_positions:
                length = clue_positions[clue_num].get('across_length', 0)
                if length > 0:
                    try:
                        answer = solve_clue(clue_text, length)
                        if answer and len(answer) == length:
                            solved_across[clue_num] = answer
                            logging.info(f"Solved across {clue_num}: {answer}")
                    except Exception as e:
                        logging.warning(f"Failed to solve across {clue_num}: {e}")
        
        # Solve down clues
        for clue_num, clue_text in down_clues.items():
            if clue_num in clue_positions:
                length = clue_positions[clue_num].get('down_length', 0)
                if length > 0:
                    try:
                        answer = solve_clue(clue_text, length)
                        if answer and len(answer) == length:
                            solved_down[clue_num] = answer
                            logging.info(f"Solved down {clue_num}: {answer}")
                    except Exception as e:
                        logging.warning(f"Failed to solve down {clue_num}: {e}")
        
        # Place answers in grid
        place_answers_in_grid(solution_grid, solved_across, solved_down, clue_positions)
        
        # Format output
        result = []
        
        # Add solved grid
        for row in solution_grid:
            result.append(" ".join(row))
        
        result.append("")  # Empty line
        
        # Add across clues
        result.append("Across:")
        for clue_num in sorted(solved_across.keys()):
            result.append(f"  {clue_num}. {solved_across[clue_num]}")
        
        result.append("")  # Empty line
        
        # Add down clues
        result.append("Down:")
        for clue_num in sorted(solved_down.keys()):
            result.append(f"  {clue_num}. {solved_down[clue_num]}")
        
        return "\n".join(result)
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return ""

def find_clue_positions(grid_lines):
    """Find where each clue starts and its length"""
    height = len(grid_lines)
    width = len(grid_lines[0]) if height > 0 else 0
    
    clue_positions = {}
    current_num = 1
    
    for row in range(height):
        for col in range(width):
            # Skip black squares
            if grid_lines[row][col] == ".":
                continue
            
            # Check if this position starts a word
            starts_across = (
                (col == 0 or grid_lines[row][col - 1] == ".")
                and col + 1 < width
                and grid_lines[row][col + 1] != "."
            )
            starts_down = (
                (row == 0 or grid_lines[row - 1][col] == ".")
                and row + 1 < height
                and grid_lines[row + 1][col] != "."
            )
            
            if starts_across or starts_down:
                clue_positions[current_num] = {
                    'row': row,
                    'col': col
                }
                
                # Calculate across length
                if starts_across:
                    across_length = 0
                    for c in range(col, width):
                        if grid_lines[row][c] == ".":
                            break
                        across_length += 1
                    clue_positions[current_num]['across_length'] = across_length
                
                # Calculate down length
                if starts_down:
                    down_length = 0
                    for r in range(row, height):
                        if grid_lines[r][col] == ".":
                            break
                        down_length += 1
                    clue_positions[current_num]['down_length'] = down_length
                
                current_num += 1
    
    return clue_positions

def solve_clue(clue_text, length):
    """Use LLM to solve a single crossword clue"""
    prompt = f"""Solve this crossword clue. The answer is {length} letters long.
Respond with ONLY the answer word, no explanation or extra text.

Clue: {clue_text}
Length: {length} letters

Answer:"""
    
    try:
        response = execute_llm(prompt)
        answer = response.strip().upper()
        # Remove any punctuation or spaces
        answer = re.sub(r'[^A-Z]', '', answer)
        
        # Basic validation
        if answer and len(answer) == length:
            return answer
    except Exception as e:
        logging.warning(f"LLM error for clue '{clue_text}': {e}")
    
    return None

def place_answers_in_grid(grid, across_answers, down_answers, clue_positions):
    """Place solved answers into the grid"""
    
    # Place across answers
    for clue_num, answer in across_answers.items():
        if clue_num in clue_positions:
            row = clue_positions[clue_num]['row']
            col = clue_positions[clue_num]['col']
            
            for i, letter in enumerate(answer):
                if col + i < len(grid[0]):
                    grid[row][col + i] = letter
    
    # Place down answers
    for clue_num, answer in down_answers.items():
        if clue_num in clue_positions:
            row = clue_positions[clue_num]['row']
            col = clue_positions[clue_num]['col']
            
            for i, letter in enumerate(answer):
                if row + i < len(grid):
                    grid[row + i][col] = letter