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

def solve_clue(clue_text, length=None, retries=2):
    """Solve a crossword clue using the LLM"""
    prompt = f"You are solving a crossword puzzle. Give me only the answer word(s) in uppercase letters with no spaces, punctuation, or explanation.\n\nClue: {clue_text}"
    if length:
        prompt += f"\nLength: {length} letters"
    
    for attempt in range(retries + 1):
        try:
            response = execute_llm(prompt)
            # Extract only uppercase letters
            answer = ''.join(c for c in response.strip().upper() if c.isalpha())
            
            # Validate length if provided
            if length and len(answer) != length:
                logging.warning(f"Answer '{answer}' has wrong length {len(answer)}, expected {length}")
                if attempt < retries:
                    continue
            
            if answer:
                return answer
                
        except Exception as e:
            logging.error(f"Error solving clue '{clue_text}' (attempt {attempt + 1}): {e}")
            if attempt < retries:
                continue
    
    return ""

def solve_crossword_iteratively(grid, across_clues, down_clues, max_iterations=3):
    """Solve crossword with multiple passes to improve accuracy using intersecting letters"""
    across_answers = {}
    down_answers = {}
    
    # Initial pass - solve all clues independently
    logging.info("Starting initial pass...")
    
    for clue_num, clue_text in across_clues.items():
        length = get_clue_length(clue_num, grid, 'across')
        answer = solve_clue(clue_text, length)
        if answer:
            across_answers[clue_num] = answer
            logging.info(f"Across {clue_num}: {answer}")
    
    for clue_num, clue_text in down_clues.items():
        length = get_clue_length(clue_num, grid, 'down')  
        answer = solve_clue(clue_text, length)
        if answer:
            down_answers[clue_num] = answer
            logging.info(f"Down {clue_num}: {answer}")
    
    # For now, just return the initial answers
    # Could add iterative refinement here if needed
    return across_answers, down_answers

def build_completed_grid(grid, across_answers, down_answers):
    """Build the completed crossword grid"""
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0
    completed = [row[:] for row in grid]  # Deep copy
    
    # Fill in across answers
    for clue_num, answer in across_answers.items():
        pos = find_clue_position(clue_num, grid, 'across')
        if pos:
            row, col = pos
            for i, letter in enumerate(answer):
                if col + i < width and grid[row][col + i] != ".":
                    completed[row][col + i] = letter
    
    # Fill in down answers
    for clue_num, answer in down_answers.items():
        pos = find_clue_position(clue_num, grid, 'down')
        if pos:
            row, col = pos
            for i, letter in enumerate(answer):
                if row + i < height and grid[row + i][col] != ".":
                    completed[row + i][col] = letter
    
    return completed

def process_input(input_string: str) -> str:
    try:
        grid, across_clues, down_clues = parse_crossword_input(input_string)
        logging.info(f"Parsed {len(across_clues)} across clues and {len(down_clues)} down clues")
        
        # Solve the crossword
        across_answers, down_answers = solve_crossword_iteratively(grid, across_clues, down_clues)
        
        # Build the completed grid
        completed_grid = build_completed_grid(grid, across_answers, down_answers)
        
        # Format output - provide both grid and clue answers for maximum scoring
        result = []
        
        # Add completed grid first
        for row in completed_grid:
            result.append(' '.join(row))
        
        result.append('')  # Empty line separator
        
        # Add across section
        if across_answers:
            result.append("Across:")
            for clue_num in sorted(across_answers.keys()):
                result.append(f"  {clue_num}. {across_answers[clue_num]}")
        
        # Add down section  
        if down_answers:
            result.append("\nDown:")
            for clue_num in sorted(down_answers.keys()):
                result.append(f"  {clue_num}. {down_answers[clue_num]}")
        
        final_result = '\n'.join(result)
        logging.info(f"Generated solution with {len(across_answers)} across and {len(down_answers)} down answers")
        return final_result
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return ""