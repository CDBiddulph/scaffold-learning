import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    try:
        # Parse the input crossword
        lines = input_string.strip().split('\n')
        
        # Find where grid ends and clues begin
        grid_lines = []
        clue_start = -1
        
        for i, line in enumerate(lines):
            if line.strip().startswith('Across:'):
                clue_start = i
                break
            grid_lines.append(line)
        
        if clue_start == -1:
            logging.error("Could not find 'Across:' section")
            return input_string
        
        # Parse the grid - handle dashes as empty squares
        grid = []
        for line in grid_lines:
            if line.strip():
                grid.append(line.split())
        
        if not grid:
            logging.error("Empty grid")
            return input_string
            
        height = len(grid)
        width = len(grid[0]) if height > 0 else 0
        
        # Validate grid dimensions
        for row in grid:
            if len(row) != width:
                logging.error(f"Inconsistent grid width: expected {width}, got {len(row)}")
                return input_string
        
        # Parse clues
        clue_lines = lines[clue_start:]
        across_clues, down_clues = parse_clues(clue_lines)
        
        logging.info(f"Found {len(across_clues)} across clues and {len(down_clues)} down clues")
        
        # Create clue position mapping
        clue_positions = create_clue_position_mapping(grid)
        
        # Solve clues using improved LLM prompting
        solved_across = solve_clues_improved(across_clues, grid, clue_positions, 'across')
        solved_down = solve_clues_improved(down_clues, grid, clue_positions, 'down')
        
        # Fill the grid with solutions
        filled_grid = fill_grid_improved(grid, solved_across, solved_down, clue_positions)
        
        # Format output
        result = []
        for row in filled_grid:
            result.append(' '.join(row))
        
        result.append('')
        result.append('Across:')
        for clue_num in sorted(solved_across.keys()):
            result.append(f'  {clue_num}. {solved_across[clue_num]}')
        
        result.append('')
        result.append('Down:')
        for clue_num in sorted(solved_down.keys()):
            result.append(f'  {clue_num}. {solved_down[clue_num]}')
        
        return '\n'.join(result)
        
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

def create_clue_position_mapping(grid):
    """Create a mapping from clue numbers to positions and lengths."""
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0
    
    clue_positions = {}
    current_num = 1
    
    for row in range(height):
        for col in range(width):
            if grid[row][col] == '.':
                continue
            
            # Check if this position starts a word
            starts_across = (
                (col == 0 or grid[row][col - 1] == '.')
                and col + 1 < width
                and grid[row][col + 1] != '.'
            )
            starts_down = (
                (row == 0 or grid[row - 1][col] == '.')
                and row + 1 < height
                and grid[row + 1][col] != '.'
            )
            
            if starts_across or starts_down:
                clue_info = {'row': row, 'col': col}
                
                if starts_across:
                    length = 0
                    for c in range(col, width):
                        if grid[row][c] == '.':
                            break
                        length += 1
                    clue_info['across_length'] = length
                
                if starts_down:
                    length = 0
                    for r in range(row, height):
                        if grid[r][col] == '.':
                            break
                        length += 1
                    clue_info['down_length'] = length
                
                clue_positions[current_num] = clue_info
                current_num += 1
    
    return clue_positions

def solve_clues_improved(clues, grid, clue_positions, direction):
    solved = {}
    
    for clue_num, clue_text in clues.items():
        try:
            if clue_num not in clue_positions:
                logging.warning(f"Clue {clue_num} not found in grid positions")
                continue
                
            clue_info = clue_positions[clue_num]
            length_key = f'{direction}_length'
            
            if length_key not in clue_info:
                logging.warning(f"Clue {clue_num} does not have {direction} length")
                continue
                
            length = clue_info[length_key]
            if length == 0:
                continue
                
            # Solve the clue with improved prompting
            answer = solve_single_clue_improved(clue_text, length, clue_num, direction)
            if answer:
                solved[clue_num] = answer
                logging.info(f"Solved {direction} clue {clue_num}: {answer}")
                
        except Exception as e:
            logging.error(f"Failed to solve {direction} clue {clue_num}: {e}")
            continue
    
    return solved

def solve_single_clue_improved(clue_text, length, clue_num, direction):
    # First try: direct clue solving
    prompt = f"""You are solving a crossword puzzle. Solve this clue and respond with ONLY the answer word in capital letters.

Clue: {clue_text}
Answer length: {length} letters
Direction: {direction}

Important: The answer must be exactly {length} letters long. Common crossword answers are often:
- Proper nouns (names, places)
- Common English words
- Abbreviations
- Song titles, movie titles, etc.

Answer:"""
    
    try:
        response = execute_llm(prompt).strip().upper()
        
        # Extract the most likely answer
        words = re.findall(r'[A-Z]+', response)
        
        # Find word of exactly the right length
        for word in words:
            if len(word) == length and word.isalpha():
                return word
        
        # If no exact match, try alternative approach
        return solve_clue_with_context(clue_text, length, clue_num, direction)
        
    except Exception as e:
        logging.error(f"Error solving clue '{clue_text}': {e}")
        return None

def solve_clue_with_context(clue_text, length, clue_num, direction):
    """Try solving with more context about crossword conventions."""
    prompt = f"""This is a crossword puzzle clue. Think step by step:

1. What type of clue is this? (definition, wordplay, abbreviation, etc.)
2. What are some possible answers that fit the clue?
3. Which answer is exactly {length} letters long?

Clue: {clue_text}
Required length: {length} letters

Think through this carefully, then give your final answer as a single word in capital letters."""
    
    try:
        response = execute_llm(prompt).strip().upper()
        
        # Look for the final answer
        words = re.findall(r'[A-Z]+', response)
        
        # Find word of exactly the right length
        for word in words:
            if len(word) == length and word.isalpha():
                return word
        
        # If still no match, try to extract from the end of the response
        lines = response.split('\n')
        for line in reversed(lines):
            words = re.findall(r'[A-Z]+', line.strip())
            for word in words:
                if len(word) == length and word.isalpha():
                    return word
        
        return None
        
    except Exception as e:
        logging.error(f"Error solving clue with context '{clue_text}': {e}")
        return None

def fill_grid_improved(grid, solved_across, solved_down, clue_positions):
    """Fill the grid with solved answers, using position mapping."""
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0
    
    # Create filled grid
    filled = [row[:] for row in grid]
    
    # Fill across answers
    for clue_num, answer in solved_across.items():
        if clue_num not in clue_positions:
            continue
            
        clue_info = clue_positions[clue_num]
        if 'across_length' not in clue_info:
            continue
            
        row, col = clue_info['row'], clue_info['col']
        
        for i, letter in enumerate(answer):
            if col + i < width and row < height:
                if grid[row][col + i] != '.':
                    filled[row][col + i] = letter
    
    # Fill down answers
    for clue_num, answer in solved_down.items():
        if clue_num not in clue_positions:
            continue
            
        clue_info = clue_positions[clue_num]
        if 'down_length' not in clue_info:
            continue
            
        row, col = clue_info['row'], clue_info['col']
        
        for i, letter in enumerate(answer):
            if row + i < height and col < width:
                if grid[row + i][col] != '.':
                    filled[row + i][col] = letter
    
    return filled