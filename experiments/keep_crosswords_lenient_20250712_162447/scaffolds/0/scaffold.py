import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Parse the input
        lines = input_string.strip().split('\n')
        
        # Find where grid ends and clues begin
        grid_lines = []
        clue_start = 0
        
        for i, line in enumerate(lines):
            if line.strip().startswith('Across:') or line.strip().startswith('Down:'):
                clue_start = i
                break
            if line.strip():
                grid_lines.append(line.strip())
        
        # Parse grid structure
        grid = []
        for line in grid_lines:
            row = line.split()
            grid.append(row)
        
        height = len(grid)
        width = len(grid[0]) if height > 0 else 0
        
        logging.info(f"Parsed grid: {height}x{width}")
        
        # Parse clues
        across_clues = {}
        down_clues = {}
        
        current_section = None
        for i in range(clue_start, len(lines)):
            line = lines[i].strip()
            if line.startswith('Across:'):
                current_section = 'across'
            elif line.startswith('Down:'):
                current_section = 'down'
            elif line and current_section:
                # Parse clue
                match = re.match(r'\s*(\d+)\.\s*(.+)', line)
                if match:
                    clue_num = int(match.group(1))
                    clue_text = match.group(2).strip()
                    if current_section == 'across':
                        across_clues[clue_num] = clue_text
                    else:
                        down_clues[clue_num] = clue_text
        
        logging.info(f"Found {len(across_clues)} across clues and {len(down_clues)} down clues")
        
        # Create numbering system and find clue positions
        clue_positions = {}
        current_num = 1
        
        for row in range(height):
            for col in range(width):
                if grid[row][col] == '.':
                    continue
                
                starts_across = (
                    (col == 0 or grid[row][col - 1] == '.') and
                    col + 1 < width and grid[row][col + 1] != '.'
                )
                starts_down = (
                    (row == 0 or grid[row - 1][col] == '.') and
                    row + 1 < height and grid[row + 1][col] != '.'
                )
                
                if starts_across or starts_down:
                    clue_positions[current_num] = (row, col)
                    current_num += 1
        
        # Initialize solved grid
        solved_grid = [[cell for cell in row] for row in grid]
        solved_across = {}
        solved_down = {}
        
        # Solve across clues
        for clue_num, clue_text in across_clues.items():
            if time.time() - start_time > 100:  # Leave buffer for timeout
                logging.warning("Approaching timeout, stopping across clue solving")
                break
                
            if clue_num in clue_positions:
                row, col = clue_positions[clue_num]
                
                # Find length of across word
                length = 0
                for c in range(col, width):
                    if grid[row][c] == '.':
                        break
                    length += 1
                
                # Solve the clue
                answer = solve_clue(clue_text, length)
                if answer and len(answer) == length:
                    solved_across[clue_num] = answer
                    # Fill in the grid
                    for i, letter in enumerate(answer):
                        if col + i < width:
                            solved_grid[row][col + i] = letter
                    logging.info(f"Solved across {clue_num}: {answer}")
                else:
                    logging.warning(f"Failed to solve across {clue_num}: {clue_text}")
        
        # Solve down clues
        for clue_num, clue_text in down_clues.items():
            if time.time() - start_time > 100:  # Leave buffer for timeout
                logging.warning("Approaching timeout, stopping down clue solving")
                break
                
            if clue_num in clue_positions:
                row, col = clue_positions[clue_num]
                
                # Find length of down word
                length = 0
                for r in range(row, height):
                    if grid[r][col] == '.':
                        break
                    length += 1
                
                # Solve the clue
                answer = solve_clue(clue_text, length)
                if answer and len(answer) == length:
                    solved_down[clue_num] = answer
                    # Fill in the grid
                    for i, letter in enumerate(answer):
                        if row + i < height:
                            solved_grid[row + i][col] = letter
                    logging.info(f"Solved down {clue_num}: {answer}")
                else:
                    logging.warning(f"Failed to solve down {clue_num}: {clue_text}")
        
        # Format output
        result = []
        
        # Add grid
        for row in solved_grid:
            result.append(' '.join(row))
        
        result.append('')  # Empty line
        
        # Add across section
        result.append('Across:')
        for clue_num in sorted(solved_across.keys()):
            result.append(f'  {clue_num}. {solved_across[clue_num]}')
        
        result.append('')  # Empty line
        
        # Add down section  
        result.append('Down:')
        for clue_num in sorted(solved_down.keys()):
            result.append(f'  {clue_num}. {solved_down[clue_num]}')
        
        return '\n'.join(result)
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return f"Error: {e}"

def solve_clue(clue_text, length):
    """Solve a crossword clue using the LLM"""
    try:
        # First attempt with basic prompt
        prompt = f"""You are solving a crossword clue. Respond with ONLY the answer word/phrase in ALL CAPS, no explanations.

Clue: {clue_text}
Length: {length} letters

Answer:"""
        
        response = execute_llm(prompt)
        
        # Extract the answer
        answer = response.strip().upper()
        
        # Remove any non-letter characters
        answer = ''.join(c for c in answer if c.isalpha())
        
        if len(answer) == length:
            return answer
        
        # If length doesn't match, try more specific prompt
        prompt = f"""You are solving a crossword clue. The answer must be exactly {length} letters long.
Respond with ONLY the answer in ALL CAPS, no spaces, no explanations.

Clue: {clue_text}
Required length: {length} letters

Example response format: EXAMPLE

Answer:"""
        
        response = execute_llm(prompt)
        answer = ''.join(c for c in response.strip().upper() if c.isalpha())
        
        if len(answer) == length:
            return answer
        
        # Third attempt with even more specific guidance
        prompt = f"""Solve this crossword clue. Your answer must be exactly {length} letters.
Remove all spaces and punctuation. Only letters allowed.

Clue: {clue_text}
Length needed: {length}

Just the answer word in capital letters:"""
        
        response = execute_llm(prompt)
        answer = ''.join(c for c in response.strip().upper() if c.isalpha())
        
        if len(answer) == length:
            return answer
            
        return None
        
    except Exception as e:
        logging.error(f"Error solving clue '{clue_text}': {e}")
        return None