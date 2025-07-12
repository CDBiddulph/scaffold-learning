import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    try:
        # First, let's try to get the LLM to solve the entire crossword at once
        # This gives it much better context than solving clues individually
        
        logging.info("Attempting to solve entire crossword with LLM")
        
        prompt = f"""You are an expert crossword solver. Below is a crossword puzzle with a grid and clues.

The grid uses '-' for empty squares that need to be filled and '.' for black squares.
Your task is to fill in ALL the empty squares with the correct letters.

Important instructions:
1. Solve the clues using the intersecting letters to help you
2. Make sure intersecting across and down answers share the same letters
3. Return the solution in the EXACT same format as the input
4. Use CAPITAL LETTERS for all filled squares
5. Keep the black squares as '.'
6. Make sure each across and down answer matches its clue exactly

Here is the crossword puzzle:

{input_string}

Please solve this crossword puzzle completely and return the solution in the exact same format."""

        response = execute_llm(prompt)
        
        # Try to clean up the response
        response = response.strip()
        
        # If the response looks reasonable, return it
        if validate_response(response, input_string):
            logging.info("LLM solved crossword successfully")
            return response
        else:
            logging.warning("LLM response doesn't look valid, trying alternative approach")
            return solve_iteratively(input_string)
            
    except Exception as e:
        logging.error(f"Error in process_input: {e}")
        return solve_iteratively(input_string)

def validate_response(response, input_string):
    """Basic validation to see if the response looks reasonable"""
    try:
        # Check if response has the expected sections
        if 'Across:' not in response or 'Down:' not in response:
            return False
        
        # Check if response has roughly the right number of lines
        input_lines = len(input_string.strip().split('\n'))
        response_lines = len(response.strip().split('\n'))
        
        # Should be roughly the same number of lines
        if abs(input_lines - response_lines) > 10:
            return False
        
        return True
    except:
        return False

def solve_iteratively(input_string: str) -> str:
    """Fallback method using iterative solving"""
    try:
        logging.info("Using iterative solving approach")
        
        # Parse input
        lines = input_string.strip().split('\n')
        
        # Find sections
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
        
        # Parse grid
        grid = [line.split() for line in grid_lines if line.strip()]
        
        # Parse clues
        clue_lines = lines[clue_start:]
        across_clues, down_clues = parse_clues(clue_lines)
        
        # Solve with better prompting
        solved_across = solve_clues_better(across_clues, grid, 'across')
        solved_down = solve_clues_better(down_clues, grid, 'down')
        
        # Fill grid
        filled_grid = fill_grid_safe(grid, solved_across, solved_down)
        
        # Format output
        return format_output(filled_grid, solved_across, solved_down)
        
    except Exception as e:
        logging.error(f"Error in iterative solving: {e}")
        return input_string

def parse_clues(clue_lines):
    """Parse clues from the input lines"""
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

def solve_clues_better(clues, grid, direction):
    """Solve clues with better prompting"""
    solved = {}
    
    for clue_num, clue_text in clues.items():
        try:
            length = get_clue_length_safe(clue_num, grid, direction)
            if length <= 0:
                continue
            
            # Use better prompting
            answer = solve_single_clue_better(clue_text, length, clue_num, direction)
            if answer:
                solved[clue_num] = answer
                
        except Exception as e:
            logging.error(f"Failed to solve {direction} clue {clue_num}: {e}")
            continue
    
    return solved

def solve_single_clue_better(clue_text, length, clue_num, direction):
    """Solve a single clue with better prompting"""
    try:
        prompt = f"""You are solving a crossword puzzle. 

Clue #{clue_num} {direction}: {clue_text}
Answer length: {length} letters

This is a standard crossword clue. Think about:
- Common crossword answer patterns
- Wordplay, puns, or abbreviations that might be involved
- Whether this might be a proper noun, acronym, or common word

Respond with ONLY the answer in capital letters, nothing else.
The answer must be exactly {length} letters long."""

        response = execute_llm(prompt).strip().upper()
        
        # Extract the best answer
        words = re.findall(r'[A-Z]+', response)
        
        # Find word of correct length
        for word in words:
            if len(word) == length and word.isalpha():
                return word
        
        # If no exact match, try to fix length
        if words:
            best_word = words[0]
            if len(best_word) > length:
                return best_word[:length]
            elif len(best_word) < length:
                # Try to expand (though this is risky)
                return best_word
        
        return None
        
    except Exception as e:
        logging.error(f"Error solving clue '{clue_text}': {e}")
        return None

def get_clue_length_safe(clue_num, grid, direction):
    """Safely get clue length with bounds checking"""
    try:
        pos = find_clue_position_safe(clue_num, grid)
        if pos is None:
            return 0
        
        row, col = pos
        height = len(grid)
        width = len(grid[0]) if height > 0 else 0
        
        if direction == 'across':
            length = 0
            for c in range(col, width):
                if grid[row][c] == '.':
                    break
                length += 1
            return length
        else:  # down
            length = 0
            for r in range(row, height):
                if grid[r][col] == '.':
                    break
                length += 1
            return length
    except Exception as e:
        logging.error(f"Error getting clue length for {clue_num}: {e}")
        return 0

def find_clue_position_safe(clue_num, grid):
    """Safely find clue position with bounds checking"""
    try:
        height = len(grid)
        width = len(grid[0]) if height > 0 else 0
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
                    if current_num == clue_num:
                        return (row, col)
                    current_num += 1
        
        return None
    except Exception as e:
        logging.error(f"Error finding clue position for {clue_num}: {e}")
        return None

def fill_grid_safe(grid, solved_across, solved_down):
    """Safely fill grid with solved answers"""
    try:
        height = len(grid)
        width = len(grid[0]) if height > 0 else 0
        
        # Create filled grid
        filled = [row[:] for row in grid]
        
        # Fill across answers
        for clue_num, answer in solved_across.items():
            pos = find_clue_position_safe(clue_num, grid)
            if pos is None:
                continue
            
            row, col = pos
            for i, letter in enumerate(answer):
                if col + i < width and grid[row][col + i] != '.':
                    filled[row][col + i] = letter
        
        # Fill down answers
        for clue_num, answer in solved_down.items():
            pos = find_clue_position_safe(clue_num, grid)
            if pos is None:
                continue
            
            row, col = pos
            for i, letter in enumerate(answer):
                if row + i < height and grid[row + i][col] != '.':
                    filled[row + i][col] = letter
        
        return filled
    except Exception as e:
        logging.error(f"Error filling grid: {e}")
        return grid

def format_output(grid, solved_across, solved_down):
    """Format the output in the expected format"""
    try:
        result = []
        
        # Add grid
        for row in grid:
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
        logging.error(f"Error formatting output: {e}")
        return ""