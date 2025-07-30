import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    try:
        # Parse the input to extract grid and clues
        grid, across_clues, down_clues = parse_input(input_string)
        logging.info(f"Found {len(across_clues)} across clues and {len(down_clues)} down clues")
        
        # Determine clue lengths from grid structure
        across_lengths = determine_across_lengths(grid)
        down_lengths = determine_down_lengths(grid)
        
        logging.info(f"Determined lengths for {len(across_lengths)} across and {len(down_lengths)} down clues")
        
        # Solve clues using improved LLM approach
        solved_across = solve_clues_improved(across_clues, across_lengths, "across")
        solved_down = solve_clues_improved(down_clues, down_lengths, "down")
        
        logging.info(f"Solved {len(solved_across)} across and {len(solved_down)} down clues")
        
        # Fill in the grid with solved answers
        filled_grid = fill_grid_with_answers(grid, solved_across, solved_down)
        
        # Format output with grid first, then clues (matching expected format)
        result = format_complete_output(filled_grid, solved_across, solved_down)
        
        return result
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "Error: Could not process input"

def parse_input(input_string):
    lines = input_string.strip().split('\n')
    
    # Find where the grid ends and clues start
    grid_end = 0
    for i, line in enumerate(lines):
        line = line.strip()
        if line.startswith("Across:"):
            grid_end = i
            break
        if line and not any(c in line for c in ['-', '.']):
            grid_end = i
            break
    
    # Parse grid
    grid = []
    for i in range(grid_end):
        line = lines[i].strip()
        if line:
            grid.append(line.split())
    
    # Find clue sections
    across_start = None
    down_start = None
    
    for i, line in enumerate(lines):
        if line.strip().startswith("Across:"):
            across_start = i
        elif line.strip().startswith("Down:"):
            down_start = i
    
    if across_start is None or down_start is None:
        raise ValueError("Could not find clues sections")
    
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
    
    return grid, across_clues, down_clues

def determine_across_lengths(grid):
    """Determine the length of each across clue from the grid structure"""
    if not grid:
        return {}
    
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0
    lengths = {}
    current_num = 1
    
    for row in range(height):
        for col in range(width):
            if grid[row][col] == ".":
                continue
                
            # Check if this position starts an across word
            starts_across = (
                (col == 0 or grid[row][col - 1] == ".")
                and col + 1 < width
                and grid[row][col + 1] != "."
            )
            
            # Check if this position starts a down word
            starts_down = (
                (row == 0 or grid[row - 1][col] == ".")
                and row + 1 < height
                and grid[row + 1][col] != "."
            )
            
            if starts_across or starts_down:
                if starts_across:
                    # Calculate length of across word
                    length = 0
                    for c in range(col, width):
                        if grid[row][c] == ".":
                            break
                        length += 1
                    lengths[current_num] = length
                current_num += 1
    
    return lengths

def determine_down_lengths(grid):
    """Determine the length of each down clue from the grid structure"""
    if not grid:
        return {}
    
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0
    lengths = {}
    current_num = 1
    
    for row in range(height):
        for col in range(width):
            if grid[row][col] == ".":
                continue
                
            # Check if this position starts an across word
            starts_across = (
                (col == 0 or grid[row][col - 1] == ".")
                and col + 1 < width
                and grid[row][col + 1] != "."
            )
            
            # Check if this position starts a down word
            starts_down = (
                (row == 0 or grid[row - 1][col] == ".")
                and row + 1 < height
                and grid[row + 1][col] != "."
            )
            
            if starts_across or starts_down:
                if starts_down:
                    # Calculate length of down word
                    length = 0
                    for r in range(row, height):
                        if grid[r][col] == ".":
                            break
                        length += 1
                    lengths[current_num] = length
                current_num += 1
    
    return lengths

def solve_clues_improved(clues, lengths, direction):
    """Solve clues using improved approach with multiple strategies"""
    solved = {}
    
    # First pass: solve regular clues
    for clue_num, clue_text in clues.items():
        if not references_other_clue(clue_text):
            length = lengths.get(clue_num)
            if length:
                answer = solve_single_clue_improved(clue_text, clue_num, length)
                if answer:
                    solved[clue_num] = answer
                    logging.info(f"Solved {direction} {clue_num}: {clue_text} ({length} letters) = {answer}")
                else:
                    logging.warning(f"Could not solve {direction} {clue_num}: {clue_text} ({length} letters)")
    
    # Second pass: solve clues that reference other clues
    for clue_num, clue_text in clues.items():
        if references_other_clue(clue_text) and clue_num not in solved:
            length = lengths.get(clue_num)
            if length:
                answer = solve_clue_with_reference(clue_text, clue_num, length, solved)
                if answer:
                    solved[clue_num] = answer
                    logging.info(f"Solved {direction} {clue_num}: {clue_text} ({length} letters) = {answer}")
                else:
                    logging.warning(f"Could not solve {direction} {clue_num}: {clue_text} ({length} letters)")
    
    return solved

def references_other_clue(clue_text):
    """Check if a clue references another clue"""
    return bool(re.search(r'\d+-Across|\d+-Down', clue_text))

def solve_single_clue_improved(clue_text, clue_num, length):
    """Solve a single crossword clue with multiple approaches"""
    
    # Try multiple prompting strategies
    strategies = [
        f"Crossword clue: {clue_text}\nAnswer ({length} letters):",
        f"What is the {length}-letter crossword answer to: {clue_text}",
        f"Clue: {clue_text}\nLength: {length}\nCrossword answer:",
        f"Solve: {clue_text} ({length} letters)",
    ]
    
    for strategy in strategies:
        try:
            response = execute_llm(strategy)
            answer = extract_answer(response, length)
            if answer:
                return answer
        except Exception as e:
            logging.warning(f"Strategy failed for clue '{clue_text}': {e}")
    
    return None

def solve_clue_with_reference(clue_text, clue_num, length, solved_clues):
    """Solve a clue that references another clue"""
    
    # Extract referenced clue number
    match = re.search(r'(\d+)-(Across|Down)', clue_text)
    if match:
        ref_num = int(match.group(1))
        if ref_num in solved_clues:
            ref_answer = solved_clues[ref_num]
            
            # Special handling for common reference patterns
            if "What the" in clue_text and "stands for" in clue_text:
                # This is asking for a letter from an acronym
                prompt = f"The clue '{clue_text}' refers to the answer '{ref_answer}'. What {length}-letter word does this clue want?"
            else:
                prompt = f"Clue: {clue_text}\nNote: The referenced answer is '{ref_answer}'\nWhat is the {length}-letter answer?"
            
            try:
                response = execute_llm(prompt)
                answer = extract_answer(response, length)
                if answer:
                    return answer
            except Exception as e:
                logging.warning(f"Failed to solve referenced clue '{clue_text}': {e}")
    
    # Fall back to regular solving
    return solve_single_clue_improved(clue_text, clue_num, length)

def extract_answer(response, length):
    """Extract and validate an answer from LLM response"""
    response = response.strip().upper()
    
    # Try to find a word of the right length
    words = response.split()
    for word in words:
        clean_word = ''.join(c for c in word if c.isalpha())
        if len(clean_word) == length:
            return clean_word
    
    # Try the whole response cleaned up
    clean_response = ''.join(c for c in response if c.isalpha())
    if len(clean_response) == length:
        return clean_response
    
    # Try taking the first N letters
    if len(clean_response) >= length:
        return clean_response[:length]
    
    return None

def fill_grid_with_answers(grid, solved_across, solved_down):
    """Fill the grid with solved answers"""
    
    # Create a copy of the grid
    filled_grid = [row[:] for row in grid]
    height = len(filled_grid)
    width = len(filled_grid[0]) if height > 0 else 0
    
    # Map clue numbers to positions
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
    
    # Fill in across answers
    for clue_num, answer in solved_across.items():
        if clue_num in clue_positions:
            row, col = clue_positions[clue_num]
            for i, letter in enumerate(answer):
                if col + i < width and filled_grid[row][col + i] != ".":
                    filled_grid[row][col + i] = letter
    
    # Fill in down answers
    for clue_num, answer in solved_down.items():
        if clue_num in clue_positions:
            row, col = clue_positions[clue_num]
            for i, letter in enumerate(answer):
                if row + i < height and filled_grid[row + i][col] != ".":
                    filled_grid[row + i][col] = letter
    
    return filled_grid

def format_complete_output(grid, solved_across, solved_down):
    """Format the output with grid first, then clues"""
    
    result = ""
    
    # Add the filled grid
    for row in grid:
        result += " ".join(row) + "\n"
    
    result += "\nAcross:\n"
    for clue_num in sorted(solved_across.keys()):
        result += f"  {clue_num}. {solved_across[clue_num]}\n"
    
    result += "\nDown:\n"
    for clue_num in sorted(solved_down.keys()):
        result += f"  {clue_num}. {solved_down[clue_num]}\n"
    
    return result