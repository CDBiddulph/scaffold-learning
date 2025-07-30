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
        
        # Solve all clues individually with better prompting
        solved_across = solve_all_clues_individually(across_clues, "across", grid, clue_positions)
        solved_down = solve_all_clues_individually(down_clues, "down", grid, clue_positions)
        
        logging.info(f"Solved {len(solved_across)} across and {len(solved_down)} down clues")
        
        # Use iterative solving to improve answers using constraints
        solved_across, solved_down = iterative_constraint_solving(
            grid, clue_positions, across_clues, down_clues, solved_across, solved_down
        )
        
        # Reconstruct grid with better conflict resolution
        filled_grid = reconstruct_grid_smart(grid, clue_positions, solved_across, solved_down)
        
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

def solve_all_clues_individually(clues, direction, grid, clue_positions):
    """Solve all clues individually with improved prompting"""
    solved = {}
    
    for clue_num, clue_text in clues.items():
        answer = solve_single_clue_improved(clue_text, clue_num, grid, clue_positions, direction)
        if answer:
            solved[clue_num] = answer
            logging.info(f"Solved {direction} {clue_num}: {clue_text} = {answer}")
    
    return solved

def solve_single_clue_improved(clue_text, clue_num, grid, clue_positions, direction):
    """Solve a single clue with enhanced prompting and flexible length validation"""
    length = get_answer_length(clue_num, direction, grid, clue_positions)
    
    # Build a comprehensive prompt
    prompt = f"""Solve this crossword clue step by step:

Clue: {clue_text}
"""
    
    if length:
        prompt += f"Answer length: {length} letters\n"
    
    prompt += """
Think about:
1. Wordplay (anagrams, puns, abbreviations)
2. Multiple meanings of words
3. Common crossword answers
4. The answer should be a single word or phrase

Provide only the final answer in CAPITAL LETTERS with no extra text."""
    
    try:
        response = execute_llm(prompt)
        
        # Extract the answer from the response
        answer = extract_answer_from_response(response)
        
        if not answer:
            return None
            
        # Flexible length validation - allow some variation
        if length:
            if len(answer) == length:
                return answer
            elif abs(len(answer) - length) <= 1:
                # Try to adjust answer to correct length
                if len(answer) > length:
                    # Truncate if too long
                    adjusted = answer[:length]
                    logging.info(f"Truncated answer from {answer} to {adjusted}")
                    return adjusted
                else:
                    # If too short, try alternative parsing
                    alternative = try_alternative_parsing(response, length)
                    if alternative:
                        return alternative
            else:
                logging.warning(f"Length mismatch for {direction} {clue_num}: expected {length}, got {len(answer)}")
                return None
        
        return answer if answer.isalpha() else None
            
    except Exception as e:
        logging.error(f"Error solving clue '{clue_text}': {e}")
        return None

def extract_answer_from_response(response):
    """Extract the answer from LLM response"""
    # Remove common prefixes and suffixes
    response = response.strip()
    
    # Look for all-caps words
    caps_words = re.findall(r'\b[A-Z]{3,}\b', response)
    if caps_words:
        return caps_words[0]
    
    # Look for words in quotes
    quoted = re.findall(r'"([^"]+)"', response)
    if quoted:
        return quoted[0].upper()
    
    # Take the last word if it looks like an answer
    words = response.split()
    if words:
        last_word = words[-1].strip('.,!?').upper()
        if last_word.isalpha() and len(last_word) > 2:
            return last_word
    
    return None

def try_alternative_parsing(response, target_length):
    """Try alternative ways to parse the response for the correct length"""
    # Look for words of the target length
    words = re.findall(r'\b[A-Z]{' + str(target_length) + r'}\b', response)
    if words:
        return words[0]
    
    # Look for phrases without spaces
    no_space_words = re.findall(r'\b[A-Z]+\b', response)
    for word in no_space_words:
        if len(word) == target_length:
            return word
    
    return None

def iterative_constraint_solving(grid, clue_positions, across_clues, down_clues, solved_across, solved_down):
    """Use grid constraints to solve additional clues"""
    # Create a working grid
    working_grid = [row[:] for row in grid]
    
    # Fill in known answers
    fill_grid_with_answers(working_grid, clue_positions, solved_across, solved_down)
    
    # Try to solve remaining clues using partial constraints
    for clue_num, clue_text in across_clues.items():
        if clue_num not in solved_across:
            answer = solve_with_constraints(clue_text, clue_num, working_grid, clue_positions, "across")
            if answer:
                solved_across[clue_num] = answer
                logging.info(f"Constraint-solved across {clue_num}: {answer}")
    
    for clue_num, clue_text in down_clues.items():
        if clue_num not in solved_down:
            answer = solve_with_constraints(clue_text, clue_num, working_grid, clue_positions, "down")
            if answer:
                solved_down[clue_num] = answer
                logging.info(f"Constraint-solved down {clue_num}: {answer}")
    
    return solved_across, solved_down

def fill_grid_with_answers(grid, clue_positions, solved_across, solved_down):
    """Fill grid with known answers"""
    for clue_num, answer in solved_across.items():
        if clue_num in clue_positions:
            row, col = clue_positions[clue_num]
            for i, letter in enumerate(answer):
                if col + i < len(grid[0]) and grid[row][col + i] != ".":
                    grid[row][col + i] = letter
    
    for clue_num, answer in solved_down.items():
        if clue_num in clue_positions:
            row, col = clue_positions[clue_num]
            for i, letter in enumerate(answer):
                if row + i < len(grid) and grid[row + i][col] != ".":
                    grid[row + i][col] = letter

def solve_with_constraints(clue_text, clue_num, grid, clue_positions, direction):
    """Solve a clue using existing grid constraints"""
    if clue_num not in clue_positions:
        return None
    
    row, col = clue_positions[clue_num]
    length = get_answer_length(clue_num, direction, grid, clue_positions)
    
    if not length:
        return None
    
    # Get the pattern from the grid
    pattern = ""
    for i in range(length):
        if direction == "across":
            if col + i < len(grid[0]):
                cell = grid[row][col + i]
                pattern += cell if cell != "-" else "_"
        else:  # down
            if row + i < len(grid):
                cell = grid[row + i][col]
                pattern += cell if cell != "-" else "_"
    
    # Only use constraints if we have some letters
    if pattern.count("_") == len(pattern):
        return None
    
    prompt = f"""Solve this crossword clue using the given letter pattern:

Clue: {clue_text}
Pattern: {pattern} (where _ = unknown letter)
Length: {length} letters

What word fits this pattern? Provide only the word in CAPITAL LETTERS."""
    
    try:
        response = execute_llm(prompt)
        answer = extract_answer_from_response(response)
        
        if answer and len(answer) == length:
            return answer
        
        return None
        
    except Exception as e:
        logging.error(f"Error solving with constraints: {e}")
        return None

def reconstruct_grid_smart(grid, clue_positions, solved_across, solved_down):
    """Reconstruct grid with smart conflict resolution"""
    if not grid:
        return []
    
    filled_grid = [row[:] for row in grid]
    conflicts = []
    
    # Fill across answers
    for clue_num, answer in solved_across.items():
        if clue_num in clue_positions:
            row, col = clue_positions[clue_num]
            for i, letter in enumerate(answer):
                if col + i < len(filled_grid[0]) and filled_grid[row][col + i] != ".":
                    filled_grid[row][col + i] = letter
    
    # Fill down answers and track conflicts
    for clue_num, answer in solved_down.items():
        if clue_num in clue_positions:
            row, col = clue_positions[clue_num]
            for i, letter in enumerate(answer):
                if row + i < len(filled_grid) and filled_grid[row + i][col] != ".":
                    current = filled_grid[row + i][col]
                    if current == "-" or current == letter:
                        filled_grid[row + i][col] = letter
                    else:
                        conflicts.append((row + i, col, current, letter))
    
    # Resolve conflicts by prioritizing more confident answers
    for row, col, across_letter, down_letter in conflicts:
        # Simple heuristic: prefer the letter that appears more frequently in the grid
        across_count = sum(1 for r in filled_grid for c in r if c == across_letter)
        down_count = sum(1 for r in filled_grid for c in r if c == down_letter)
        
        if down_count > across_count:
            filled_grid[row][col] = down_letter
        # else keep the across letter
    
    return filled_grid

def format_grid(grid):
    """Format grid for output"""
    if not grid:
        return ""
    return "\n".join(" ".join(row) for row in grid)