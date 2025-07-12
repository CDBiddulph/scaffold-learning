import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    try:
        lines = input_string.strip().split('\n')
        
        # Find where clues start
        across_start = -1
        for i, line in enumerate(lines):
            if line.strip().startswith('Across:'):
                across_start = i
                break
        
        if across_start == -1:
            logging.error("Could not find 'Across:' section")
            return input_string
        
        # Parse grid
        grid_lines = lines[:across_start]
        grid = []
        for line in grid_lines:
            line = line.strip()
            if line:
                grid.append(line.split())
        
        if not grid:
            logging.error("Empty grid")
            return input_string
        
        logging.info(f"Parsed grid: {len(grid)}x{len(grid[0]) if grid else 0}")
        
        # Parse clues
        clue_lines = lines[across_start:]
        across_clues, down_clues = parse_clues(clue_lines)
        
        logging.info(f"Parsed {len(across_clues)} across clues and {len(down_clues)} down clues")
        
        # Find clue positions and lengths
        clue_positions = find_all_clue_positions(grid)
        
        logging.info(f"Found {len(clue_positions)} clue positions")
        
        # Solve clues with better prompting
        solved_across = solve_clues_with_context(across_clues, clue_positions, 'across')
        solved_down = solve_clues_with_context(down_clues, clue_positions, 'down')
        
        logging.info(f"Solved {len(solved_across)} across and {len(solved_down)} down clues")
        
        # Fill grid with solutions
        filled_grid = fill_grid_with_solutions(grid, clue_positions, solved_across, solved_down)
        
        # Format output
        return format_crossword_output(filled_grid, solved_across, solved_down)
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return input_string

def parse_clues(clue_lines):
    across_clues = {}
    down_clues = {}
    current_section = None
    
    for line in clue_lines:
        line = line.strip()
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
    
    return across_clues, down_clues

def find_all_clue_positions(grid):
    """Find all clue positions and their lengths using proper crossword numbering"""
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0
    
    clue_positions = {}
    current_num = 1
    
    for row in range(height):
        for col in range(width):
            if grid[row][col] == '.':
                continue
            
            # Check if this position starts an across word
            starts_across = (
                (col == 0 or grid[row][col - 1] == '.') and
                col + 1 < width and grid[row][col + 1] != '.'
            )
            
            # Check if this position starts a down word
            starts_down = (
                (row == 0 or grid[row - 1][col] == '.') and
                row + 1 < height and grid[row + 1][col] != '.'
            )
            
            if starts_across or starts_down:
                clue_positions[current_num] = {}
                
                if starts_across:
                    # Calculate across length
                    length = 0
                    for c in range(col, width):
                        if grid[row][c] == '.':
                            break
                        length += 1
                    clue_positions[current_num]['across'] = ((row, col), length)
                
                if starts_down:
                    # Calculate down length
                    length = 0
                    for r in range(row, height):
                        if grid[r][col] == '.':
                            break
                        length += 1
                    clue_positions[current_num]['down'] = ((row, col), length)
                
                current_num += 1
    
    return clue_positions

def solve_clues_with_context(clues, clue_positions, direction):
    solved = {}
    
    for clue_num, clue_text in clues.items():
        if clue_num in clue_positions and direction in clue_positions[clue_num]:
            pos, length = clue_positions[clue_num][direction]
            answer = solve_single_clue_improved(clue_text, length, clue_num, direction)
            if answer and len(answer) == length:
                solved[clue_num] = answer
                logging.info(f"Solved {direction} {clue_num}: {clue_text} = {answer}")
            else:
                logging.warning(f"Failed to solve {direction} {clue_num}: {clue_text}")
    
    return solved

def solve_single_clue_improved(clue_text, length, clue_num, direction):
    """Improved clue solving with better prompting"""
    prompt = f"""You are an expert crossword solver. Solve this crossword clue.

Clue: {clue_text}
Answer length: {length} letters
Direction: {direction}
Clue number: {clue_num}

Think about:
- What type of clue is this? (definition, wordplay, abbreviation, etc.)
- Are there any obvious indicators or wordplay?
- What are common crossword answers for this type of clue?

Respond with ONLY the answer in capital letters, no explanation."""
    
    try:
        response = execute_llm(prompt).strip().upper()
        
        # Extract the most likely answer
        words = re.findall(r'[A-Z]+', response)
        
        # Find word of correct length
        for word in words:
            if len(word) == length and word.isalpha():
                return word
        
        # If no exact match, try a simpler prompt
        simple_prompt = f"Crossword clue: {clue_text}\nLength: {length} letters\nAnswer:"
        simple_response = execute_llm(simple_prompt).strip().upper()
        simple_words = re.findall(r'[A-Z]+', simple_response)
        
        for word in simple_words:
            if len(word) == length and word.isalpha():
                return word
        
        return None
        
    except Exception as e:
        logging.error(f"Error solving clue '{clue_text}': {e}")
        return None

def fill_grid_with_solutions(grid, clue_positions, solved_across, solved_down):
    """Fill the grid with solved answers"""
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0
    
    # Create a copy of the grid
    filled = [row[:] for row in grid]
    
    # Fill across answers
    for clue_num, answer in solved_across.items():
        if clue_num in clue_positions and 'across' in clue_positions[clue_num]:
            (row, col), length = clue_positions[clue_num]['across']
            for i, letter in enumerate(answer):
                if i < length and col + i < width:
                    filled[row][col + i] = letter
    
    # Fill down answers
    for clue_num, answer in solved_down.items():
        if clue_num in clue_positions and 'down' in clue_positions[clue_num]:
            (row, col), length = clue_positions[clue_num]['down']
            for i, letter in enumerate(answer):
                if i < length and row + i < height:
                    filled[row + i][col] = letter
    
    return filled

def format_crossword_output(filled_grid, solved_across, solved_down):
    """Format the output to match expected format"""
    result = []
    
    # Add grid
    for row in filled_grid:
        result.append(' '.join(row))
    
    result.append('')
    
    # Add across clues
    result.append('Across:')
    for clue_num in sorted(solved_across.keys()):
        result.append(f'  {clue_num}. {solved_across[clue_num]}')
    
    result.append('')
    
    # Add down clues
    result.append('Down:')
    for clue_num in sorted(solved_down.keys()):
        result.append(f'  {clue_num}. {solved_down[clue_num]}')
    
    return '\n'.join(result)