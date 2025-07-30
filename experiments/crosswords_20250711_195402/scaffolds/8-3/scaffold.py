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
        
        # Solve clues using LLM with length constraints
        solved_across = solve_clues_with_lengths(across_clues, across_lengths, "across")
        solved_down = solve_clues_with_lengths(down_clues, down_lengths, "down")
        
        logging.info(f"Solved {len(solved_across)} across and {len(solved_down)} down clues")
        
        # Format output (clues only to avoid grid/clue conflicts)
        result = "Across:\n"
        for clue_num in sorted(solved_across.keys()):
            result += f"{clue_num}. {solved_across[clue_num]}\n"
        
        result += "\nDown:\n"
        for clue_num in sorted(solved_down.keys()):
            result += f"{clue_num}. {solved_down[clue_num]}\n"
        
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

def solve_clues_with_lengths(clues, lengths, direction):
    solved = {}
    
    for clue_num, clue_text in clues.items():
        length = lengths.get(clue_num)
        if length:
            answer = solve_single_clue_with_length(clue_text, clue_num, length)
            if answer:
                solved[clue_num] = answer
                logging.info(f"Solved {direction} {clue_num}: {clue_text} ({length} letters) = {answer}")
            else:
                logging.warning(f"Could not solve {direction} {clue_num}: {clue_text} ({length} letters)")
        else:
            logging.warning(f"No length found for {direction} {clue_num}: {clue_text}")
    
    return solved

def solve_single_clue_with_length(clue_text, clue_num, length):
    """Solve a single crossword clue with known length"""
    
    prompt = f"""You are solving a crossword puzzle clue. The answer must be exactly {length} letters long.

Clue {clue_num}: {clue_text}

The answer must be:
- Exactly {length} letters
- All capital letters
- A single word or phrase (no spaces)
- A common crossword answer

Think about:
- Wordplay, puns, abbreviations
- Pop culture references  
- Multiple meanings of words
- Common crossword conventions

Respond with ONLY the {length}-letter answer in capital letters:"""
    
    try:
        response = execute_llm(prompt)
        answer = response.strip().upper()
        
        # Clean up the response
        answer = answer.strip('"').strip("'").strip()
        
        # Take the first word if multiple words
        words = answer.split()
        if words:
            answer = words[0]
        
        # Remove any non-letter characters for crosswords
        answer = ''.join(c for c in answer if c.isalpha())
        
        # Validate length and format
        if len(answer) == length and answer.isalpha():
            return answer
        else:
            logging.warning(f"Invalid answer length or format: '{answer}' (expected {length} letters) for clue: {clue_text}")
            
            # Try a more specific prompt if first attempt failed
            return solve_with_retry(clue_text, clue_num, length)
            
    except Exception as e:
        logging.error(f"Error solving clue '{clue_text}': {e}")
        return None

def solve_with_retry(clue_text, clue_num, length):
    """Retry solving with more specific instructions"""
    
    prompt = f"""CROSSWORD CLUE - EXACTLY {length} LETTERS REQUIRED

Clue: {clue_text}

This is a crossword puzzle. The answer is exactly {length} letters long.

Examples of {length}-letter crossword answers:
{'- ' + 'A' * length}

Your answer must be:
1. Exactly {length} letters
2. All uppercase letters  
3. No spaces or punctuation
4. A real word or common phrase

Answer ({length} letters):"""
    
    try:
        response = execute_llm(prompt)
        answer = response.strip().upper()
        
        # More aggressive cleaning
        answer = ''.join(c for c in answer if c.isalpha())
        
        if len(answer) == length:
            return answer
        else:
            logging.warning(f"Retry failed: '{answer}' is {len(answer)} letters, need {length}")
            return None
            
    except Exception as e:
        logging.error(f"Error in retry for clue '{clue_text}': {e}")
        return None