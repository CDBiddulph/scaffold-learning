import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    try:
        # Parse the input to extract grid and clues
        grid, across_clues, down_clues = parse_input(input_string)
        logging.info(f"Found {len(across_clues)} across clues and {len(down_clues)} down clues")
        
        # Determine clue lengths and positions from grid structure
        across_info = determine_across_info(grid)
        down_info = determine_down_info(grid)
        
        logging.info(f"Determined info for {len(across_info)} across and {len(down_info)} down clues")
        
        # Solve clues using improved LLM prompting
        solved_across = solve_clues_improved(across_clues, across_info, "across")
        solved_down = solve_clues_improved(down_clues, down_info, "down")
        
        logging.info(f"Solved {len(solved_across)} across and {len(solved_down)} down clues")
        
        # Construct the filled grid
        filled_grid = construct_filled_grid(grid, solved_across, solved_down, across_info, down_info)
        
        # Format output with both grid and clues
        result = format_output(filled_grid, solved_across, solved_down)
        
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

def determine_across_info(grid):
    """Determine the length and position of each across clue"""
    if not grid:
        return {}
    
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0
    info = {}
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
                    info[current_num] = {'length': length, 'row': row, 'col': col}
                current_num += 1
    
    return info

def determine_down_info(grid):
    """Determine the length and position of each down clue"""
    if not grid:
        return {}
    
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0
    info = {}
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
                    info[current_num] = {'length': length, 'row': row, 'col': col}
                current_num += 1
    
    return info

def solve_clues_improved(clues, clue_info, direction):
    """Solve clues with improved prompting"""
    solved = {}
    
    for clue_num, clue_text in clues.items():
        if clue_num in clue_info:
            length = clue_info[clue_num]['length']
            answer = solve_single_clue_improved(clue_text, clue_num, length)
            if answer:
                solved[clue_num] = answer
                logging.info(f"Solved {direction} {clue_num}: {clue_text} ({length} letters) = {answer}")
            else:
                logging.warning(f"Could not solve {direction} {clue_num}: {clue_text} ({length} letters)")
        else:
            logging.warning(f"No info found for {direction} {clue_num}: {clue_text}")
    
    return solved

def solve_single_clue_improved(clue_text, clue_num, length):
    """Solve a single crossword clue with improved prompting"""
    
    # Try multiple prompting strategies
    strategies = [
        # Strategy 1: Direct and concise
        f"Crossword clue: {clue_text}\nLength: {length} letters\nAnswer:",
        
        # Strategy 2: With examples
        f"Solve this crossword clue. Answer with exactly {length} letters, no spaces.\nClue: {clue_text}\nAnswer:",
        
        # Strategy 3: With context about crossword conventions
        f"Crossword puzzle clue: {clue_text}\nThe answer is {length} letters long. In crosswords, answers can be compound words (like HOTDOG), phrases without spaces (like NEWYORK), or abbreviations.\nAnswer:",
    ]
    
    for strategy in strategies:
        try:
            response = execute_llm(strategy)
            answer = extract_answer(response, length)
            if answer:
                return answer
        except Exception as e:
            logging.error(f"Error with strategy for clue '{clue_text}': {e}")
            continue
    
    return None

def extract_answer(response, target_length):
    """Extract a valid answer from LLM response"""
    # Remove common prefixes and clean up
    response = response.strip()
    if response.startswith("Answer:"):
        response = response[7:].strip()
    
    # Find all sequences of letters
    import re
    letter_sequences = re.findall(r'[A-Z]+', response.upper())
    
    # Return the first sequence that matches the target length
    for seq in letter_sequences:
        if len(seq) == target_length:
            return seq
    
    # If no exact match, try to find compound words or phrases
    words = re.findall(r'[A-Z]+', response.upper())
    
    # Try combining words to reach target length
    for i in range(len(words)):
        combined = ""
        for j in range(i, len(words)):
            combined += words[j]
            if len(combined) == target_length:
                return combined
            if len(combined) > target_length:
                break
    
    return None

def construct_filled_grid(grid, solved_across, solved_down, across_info, down_info):
    """Construct the filled grid from solved clues"""
    if not grid:
        return []
    
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0
    
    # Initialize filled grid with original structure
    filled = [[cell for cell in row] for row in grid]
    
    # Place across answers
    for clue_num, answer in solved_across.items():
        if clue_num in across_info:
            info = across_info[clue_num]
            row, col = info['row'], info['col']
            for i, letter in enumerate(answer):
                if col + i < width:
                    filled[row][col + i] = letter
    
    # Place down answers
    for clue_num, answer in solved_down.items():
        if clue_num in down_info:
            info = down_info[clue_num]
            row, col = info['row'], info['col']
            for i, letter in enumerate(answer):
                if row + i < height:
                    filled[row + i][col] = letter
    
    return filled

def format_output(filled_grid, solved_across, solved_down):
    """Format the final output with grid and clues"""
    result = ""
    
    # Add the filled grid
    for row in filled_grid:
        result += " ".join(row) + "\n"
    
    # Add across clues
    result += "\nAcross:\n"
    for clue_num in sorted(solved_across.keys()):
        result += f"  {clue_num}. {solved_across[clue_num]}\n"
    
    # Add down clues
    result += "\nDown:\n"
    for clue_num in sorted(solved_down.keys()):
        result += f"  {clue_num}. {solved_down[clue_num]}\n"
    
    return result.strip()