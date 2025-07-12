import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    try:
        # Parse the input to extract grid and clues
        grid, across_clues, down_clues = parse_input(input_string)
        
        logging.info(f"Found {len(across_clues)} across clues and {len(down_clues)} down clues")
        
        # Solve the entire crossword at once
        solved_grid, solved_across, solved_down = solve_crossword_complete(
            grid, across_clues, down_clues
        )
        
        # Format the output
        result = format_output(solved_grid, solved_across, solved_down)
        
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

def solve_crossword_complete(grid, across_clues, down_clues):
    """Solve the entire crossword puzzle at once using the LLM"""
    
    # Format the puzzle for the LLM
    puzzle_text = format_puzzle_for_llm(grid, across_clues, down_clues)
    
    prompt = f"""You are a crossword puzzle solver. I will give you a crossword puzzle with a grid structure and clues. Please solve the entire puzzle.

{puzzle_text}

Please provide your solution in the following format:

SOLVED GRID:
[Each row of the grid with letters filled in, separated by spaces]

ACROSS ANSWERS:
1. [ANSWER]
6. [ANSWER]
[etc.]

DOWN ANSWERS:
1. [ANSWER]
2. [ANSWER]
[etc.]

Important rules:
- Fill in all empty squares (marked with -) with letters
- Keep black squares as dots (.)
- Provide all answers in CAPITAL LETTERS
- Make sure answers fit the grid structure and intersect correctly
- Consider crossword conventions, wordplay, and abbreviations
"""
    
    try:
        response = execute_llm(prompt)
        logging.info("Got response from LLM for complete puzzle")
        
        # Parse the LLM response
        solved_grid, solved_across, solved_down = parse_llm_response(response, grid)
        
        return solved_grid, solved_across, solved_down
        
    except Exception as e:
        logging.error(f"Error solving complete crossword: {e}")
        # Fall back to empty solution
        return grid, {}, {}

def format_puzzle_for_llm(grid, across_clues, down_clues):
    """Format the puzzle in a clear way for the LLM"""
    result = "PUZZLE GRID:\n"
    for row in grid:
        result += " ".join(row) + "\n"
    
    result += "\nACROSS CLUES:\n"
    for num in sorted(across_clues.keys()):
        result += f"{num}. {across_clues[num]}\n"
    
    result += "\nDOWN CLUES:\n"
    for num in sorted(down_clues.keys()):
        result += f"{num}. {down_clues[num]}\n"
    
    return result

def parse_llm_response(response, original_grid):
    """Parse the LLM's response to extract the solved grid and answers"""
    lines = response.strip().split('\n')
    
    solved_grid = []
    solved_across = {}
    solved_down = {}
    
    current_section = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if "SOLVED GRID:" in line.upper() or "GRID:" in line.upper():
            current_section = "grid"
            continue
        elif "ACROSS" in line.upper():
            current_section = "across"
            continue
        elif "DOWN" in line.upper():
            current_section = "down"
            continue
        
        if current_section == "grid":
            # Parse grid row
            cells = line.split()
            if cells and len(cells) > 0:
                # Clean up cells
                cleaned_cells = []
                for cell in cells:
                    cell = cell.strip().upper()
                    if cell and cell != '':
                        cleaned_cells.append(cell)
                if cleaned_cells:
                    solved_grid.append(cleaned_cells)
        
        elif current_section == "across":
            # Parse across clue
            match = re.match(r'\s*(\d+)\.\s*(.+)', line)
            if match:
                clue_num = int(match.group(1))
                answer = match.group(2).strip().upper()
                # Remove any extra words or explanations
                answer = answer.split()[0] if answer.split() else answer
                # Remove non-letter characters
                answer = ''.join(c for c in answer if c.isalpha())
                solved_across[clue_num] = answer
        
        elif current_section == "down":
            # Parse down clue
            match = re.match(r'\s*(\d+)\.\s*(.+)', line)
            if match:
                clue_num = int(match.group(1))
                answer = match.group(2).strip().upper()
                # Remove any extra words or explanations
                answer = answer.split()[0] if answer.split() else answer
                # Remove non-letter characters
                answer = ''.join(c for c in answer if c.isalpha())
                solved_down[clue_num] = answer
    
    # If we didn't get a proper grid, use the original
    if not solved_grid:
        solved_grid = [row[:] for row in original_grid]
    
    # Make sure grid dimensions match
    if len(solved_grid) != len(original_grid):
        solved_grid = [row[:] for row in original_grid]
    else:
        for i in range(len(solved_grid)):
            if len(solved_grid[i]) != len(original_grid[i]):
                solved_grid[i] = original_grid[i][:]
    
    logging.info(f"Parsed {len(solved_across)} across answers and {len(solved_down)} down answers")
    
    return solved_grid, solved_across, solved_down

def format_output(grid, solved_across, solved_down):
    """Format output with grid and answers"""
    result = ""
    
    # Add grid
    for row in grid:
        result += " ".join(row) + "\n"
    
    result += "\n"
    
    # Add across answers
    result += "Across:\n"
    for clue_num in sorted(solved_across.keys()):
        result += f"  {clue_num}. {solved_across[clue_num]}\n"
    
    result += "\n"
    
    # Add down answers
    result += "Down:\n"
    for clue_num in sorted(solved_down.keys()):
        result += f"  {clue_num}. {solved_down[clue_num]}\n"
    
    return result