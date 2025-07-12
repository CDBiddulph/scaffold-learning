import logging
import re
from llm_executor import execute_llm

def parse_input(input_string):
    """Parse input to extract grid structure and clues"""
    lines = input_string.strip().split('\n')
    
    # Find where clues start
    across_start = None
    down_start = None
    
    for i, line in enumerate(lines):
        if line.strip().startswith('Across:'):
            across_start = i
        elif line.strip().startswith('Down:'):
            down_start = i
    
    # Extract grid (everything before clues)
    grid_end = across_start if across_start else len(lines)
    grid = []
    for i in range(grid_end):
        line = lines[i].strip()
        if line:
            grid.append(line.split())
    
    # Extract across clues
    across_clues = {}
    if across_start is not None:
        end_idx = down_start if down_start else len(lines)
        for i in range(across_start + 1, end_idx):
            line = lines[i].strip()
            if line:
                match = re.match(r'\s*(\d+)\.\s*(.+)', line)
                if match:
                    num = int(match.group(1))
                    clue = match.group(2)
                    across_clues[num] = clue
    
    # Extract down clues
    down_clues = {}
    if down_start is not None:
        for i in range(down_start + 1, len(lines)):
            line = lines[i].strip()
            if line:
                match = re.match(r'\s*(\d+)\.\s*(.+)', line)
                if match:
                    num = int(match.group(1))
                    clue = match.group(2)
                    down_clues[num] = clue
    
    return grid, across_clues, down_clues

def get_clue_positions(grid):
    """Determine numbered positions in crossword grid"""
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0
    
    positions = {}
    current_num = 1
    
    for row in range(height):
        for col in range(width):
            if grid[row][col] != '.':
                # Check if this starts an across word
                starts_across = (col == 0 or grid[row][col-1] == '.') and \
                               (col + 1 < width and grid[row][col+1] != '.')
                
                # Check if this starts a down word
                starts_down = (row == 0 or grid[row-1][col] == '.') and \
                             (row + 1 < height and grid[row+1][col] != '.')
                
                if starts_across or starts_down:
                    positions[current_num] = (row, col)
                    current_num += 1
    
    return positions

def get_word_length(grid, row, col, direction):
    """Get the length of a word starting at given position"""
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0
    
    length = 0
    if direction == 'across':
        while col + length < width and grid[row][col + length] != '.':
            length += 1
    else:  # down
        while row + length < height and grid[row + length][col] != '.':
            length += 1
    
    return length

def solve_clue(clue, length, retries=2):
    """Solve a crossword clue using LLM"""
    logging.info(f"Solving clue: {clue} (length: {length})")
    
    prompt = f"""Solve this crossword clue:
Clue: {clue}
Answer length: {length} letters

Respond with ONLY the answer in capital letters, no spaces, no punctuation, no explanation.
Example: If the answer is "HELLO WORLD", respond with: HELLOWORLD"""
    
    for attempt in range(retries + 1):
        try:
            response = execute_llm(prompt)
            # Extract the answer from response
            answer = ''.join(c for c in response.strip().upper() if c.isalpha())
            
            if len(answer) == length:
                logging.info(f"Solved clue '{clue}' -> '{answer}'")
                return answer
            else:
                logging.warning(f"Answer length mismatch: expected {length}, got {len(answer)} for '{answer}'")
                # Try to get a better answer with more specific prompt
                if attempt < retries:
                    prompt = f"""This crossword clue needs exactly {length} letters:
Clue: {clue}

The answer must be exactly {length} letters long. Respond with ONLY the answer in capital letters."""
        except Exception as e:
            logging.error(f"Error solving clue '{clue}': {e}")
    
    # Fallback: return placeholder
    return 'A' * length

def solve_clue_with_constraints(clue, length, pattern=None, retries=2):
    """Solve clue with additional constraints from intersecting words"""
    logging.info(f"Solving clue with constraints: {clue} (length: {length}, pattern: {pattern})")
    
    constraint_text = ""
    if pattern:
        constraint_text = f"\nKnown letters: {pattern} (use _ for unknown letters)"
    
    prompt = f"""Solve this crossword clue:
Clue: {clue}
Answer length: {length} letters{constraint_text}

Respond with ONLY the answer in capital letters, no spaces, no punctuation, no explanation."""
    
    for attempt in range(retries + 1):
        try:
            response = execute_llm(prompt)
            answer = ''.join(c for c in response.strip().upper() if c.isalpha())
            
            if len(answer) == length:
                # Check if it matches the pattern
                if pattern:
                    matches = True
                    for i, (a, p) in enumerate(zip(answer, pattern)):
                        if p != '_' and p != a:
                            matches = False
                            break
                    if matches:
                        return answer
                else:
                    return answer
        except Exception as e:
            logging.error(f"Error solving constrained clue '{clue}': {e}")
    
    # Fallback
    return 'A' * length

def process_input(input_string: str) -> str:
    try:
        grid, across_clues, down_clues = parse_input(input_string)
        
        if not grid:
            return "Error: No grid found"
        
        height = len(grid)
        width = len(grid[0]) if height > 0 else 0
        
        # Create filled grid (copy grid structure)
        filled_grid = [row[:] for row in grid]
        
        # Get clue positions
        positions = get_clue_positions(grid)
        
        # Solve clues iteratively with constraint propagation
        max_iterations = 3
        for iteration in range(max_iterations):
            logging.info(f"Iteration {iteration + 1}")
            
            # Solve across clues
            for num, clue in across_clues.items():
                if num in positions:
                    row, col = positions[num]
                    length = get_word_length(grid, row, col, 'across')
                    
                    # Build pattern from current state
                    pattern = ""
                    for i in range(length):
                        if col + i < width:
                            cell = filled_grid[row][col + i]
                            pattern += cell if cell != '-' else '_'
                        else:
                            pattern += '_'
                    
                    # Only solve if we don't have a complete answer
                    if '_' in pattern or '-' in pattern:
                        answer = solve_clue_with_constraints(clue, length, pattern)
                        
                        # Place the answer
                        for i, letter in enumerate(answer):
                            if col + i < width:
                                filled_grid[row][col + i] = letter
            
            # Solve down clues
            for num, clue in down_clues.items():
                if num in positions:
                    row, col = positions[num]
                    length = get_word_length(grid, row, col, 'down')
                    
                    # Build pattern from current state
                    pattern = ""
                    for i in range(length):
                        if row + i < height:
                            cell = filled_grid[row + i][col]
                            pattern += cell if cell != '-' else '_'
                        else:
                            pattern += '_'
                    
                    # Only solve if we don't have a complete answer
                    if '_' in pattern or '-' in pattern:
                        answer = solve_clue_with_constraints(clue, length, pattern)
                        
                        # Place the answer
                        for i, letter in enumerate(answer):
                            if row + i < height:
                                filled_grid[row + i][col] = letter
        
        # Build final answers dictionary
        across_answers = {}
        for num in across_clues.keys():
            if num in positions:
                row, col = positions[num]
                length = get_word_length(grid, row, col, 'across')
                answer = ""
                for i in range(length):
                    if col + i < width:
                        answer += filled_grid[row][col + i]
                across_answers[num] = answer
        
        down_answers = {}
        for num in down_clues.keys():
            if num in positions:
                row, col = positions[num]
                length = get_word_length(grid, row, col, 'down')
                answer = ""
                for i in range(length):
                    if row + i < height:
                        answer += filled_grid[row + i][col]
                down_answers[num] = answer
        
        # Format output
        result = []
        
        # Add filled grid
        for row in filled_grid:
            result.append(' '.join(row))
        
        result.append('')  # Empty line
        
        # Add across answers
        result.append('Across:')
        for num in sorted(across_answers.keys()):
            result.append(f'  {num}. {across_answers[num]}')
        
        result.append('')  # Empty line
        
        # Add down answers
        result.append('Down:')
        for num in sorted(down_answers.keys()):
            result.append(f'  {num}. {down_answers[num]}')
        
        return '\n'.join(result)
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return f"Error: {str(e)}"