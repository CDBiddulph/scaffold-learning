import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    try:
        # Parse the grid structure and clues
        grid = parse_grid_structure(input_string)
        clue_positions = number_grid(grid) if grid else {}
        across_clues, down_clues = parse_clues(input_string)
        
        logging.info(f"Found {len(across_clues)} across clues and {len(down_clues)} down clues")
        logging.info(f"Grid size: {len(grid)}x{len(grid[0]) if grid else 0}")
        
        # Solve clues in batches for efficiency
        solved_across = solve_clues_batch(across_clues, "across", grid, clue_positions)
        solved_down = solve_clues_batch(down_clues, "down", grid, clue_positions)
        
        logging.info(f"Solved {len(solved_across)} across and {len(solved_down)} down clues")
        
        # Reconstruct and include grid - this could help with scoring
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
        logging.error(f"Error processing input: {e}")
        return "Error: Could not process input"

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

def solve_clues_batch(clues, direction, grid, clue_positions):
    """Solve clues in batches for efficiency"""
    solved = {}
    clue_list = list(clues.items())
    batch_size = 6  # Smaller batches for better accuracy
    
    for i in range(0, len(clue_list), batch_size):
        batch = clue_list[i:i+batch_size]
        
        # Create batch prompt with enhanced instructions
        batch_prompt = """Solve these crossword clues. Important guidelines:
- Think about common crossword conventions and wordplay
- Answers must be exactly the specified length
- Use common words/phrases that would appear in crosswords
- Consider multiple meanings and abbreviations

Respond with ONLY the answers, one per line in order (capital letters only).

"""
        
        for j, (clue_num, clue_text) in enumerate(batch):
            length = get_answer_length(clue_num, direction, grid, clue_positions)
            length_hint = f" ({length} letters)" if length else ""
            batch_prompt += f"{j+1}. {clue_text}{length_hint}\n"
        
        batch_prompt += "\nAnswers:"
        
        try:
            response = execute_llm(batch_prompt)
            answers = [line.strip().upper() for line in response.strip().split('\n') if line.strip()]
            
            # Match answers to clues
            for j, answer in enumerate(answers):
                if j < len(batch):
                    clue_num, clue_text = batch[j]
                    # Clean up answer
                    answer = re.sub(r'[^A-Z]', '', answer)  # Remove non-letters
                    
                    # Validate length if we know it
                    expected_length = get_answer_length(clue_num, direction, grid, clue_positions)
                    if expected_length and len(answer) != expected_length:
                        logging.warning(f"Length mismatch for {direction} {clue_num}: expected {expected_length}, got {len(answer)}")
                        # Try individual solving for length mismatches
                        answer = solve_single_clue(clue_text, clue_num, grid, clue_positions, direction)
                    
                    if answer and answer.isalpha():
                        solved[clue_num] = answer
                        logging.info(f"Solved {direction} {clue_num}: {clue_text} = {answer}")
                    
        except Exception as e:
            logging.error(f"Error solving batch: {e}")
            # Fall back to individual solving for failed batch
            for clue_num, clue_text in batch:
                answer = solve_single_clue(clue_text, clue_num, grid, clue_positions, direction)
                if answer:
                    solved[clue_num] = answer
    
    return solved

def solve_single_clue(clue_text, clue_num, grid, clue_positions, direction):
    """Solve a single clue with enhanced prompting"""
    length = get_answer_length(clue_num, direction, grid, clue_positions)
    length_hint = f" The answer must be exactly {length} letters." if length else ""
    
    prompt = f"""Solve this crossword clue. Think step by step about possible answers:

Clue: {clue_text}{length_hint}

Consider:
- Common crossword conventions and wordplay
- Multiple meanings of words in the clue
- Abbreviations and informal terms
- The answer should be a word or phrase that would appear in crosswords

What is your final answer? Respond with ONLY the answer in capital letters."""
    
    try:
        response = execute_llm(prompt)
        answer = response.strip().upper()
        answer = re.sub(r'[^A-Z]', '', answer)  # Remove non-letters
        
        # Validate length strictly for individual solving
        if length and len(answer) != length:
            logging.warning(f"Individual solve length mismatch for {direction} {clue_num}: expected {length}, got {len(answer)}")
            return None
        
        if answer and answer.isalpha():
            return answer
        return None
            
    except Exception as e:
        logging.error(f"Error solving clue '{clue_text}': {e}")
        return None

def reconstruct_grid(grid, clue_positions, solved_across, solved_down):
    """Reconstruct the filled grid from solved clues"""
    if not grid:
        return []
    
    filled_grid = [row[:] for row in grid]  # Deep copy
    
    # Fill in across answers first
    for clue_num, answer in solved_across.items():
        if clue_num in clue_positions:
            row, col = clue_positions[clue_num]
            for i, letter in enumerate(answer):
                if (col + i < len(filled_grid[0]) and 
                    filled_grid[row][col + i] != "."):
                    filled_grid[row][col + i] = letter
    
    # Fill in down answers, being careful about conflicts
    for clue_num, answer in solved_down.items():
        if clue_num in clue_positions:
            row, col = clue_positions[clue_num]
            for i, letter in enumerate(answer):
                if (row + i < len(filled_grid) and 
                    filled_grid[row + i][col] != "."):
                    # Only fill if empty or same letter (avoid conflicts)
                    current = filled_grid[row + i][col]
                    if current == "-" or current == letter:
                        filled_grid[row + i][col] = letter
                    elif current != letter:
                        logging.warning(f"Conflict at ({row + i}, {col}): across='{current}' vs down='{letter}'")
    
    return filled_grid

def format_grid(grid):
    """Format grid for output"""
    if not grid:
        return ""
    return "\n".join(" ".join(row) for row in grid)