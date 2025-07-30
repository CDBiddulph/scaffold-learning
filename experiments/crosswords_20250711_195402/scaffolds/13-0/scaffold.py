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

def solve_clue(clue, length, retries=3):
    """Solve a crossword clue using LLM with improved prompting"""
    logging.info(f"Solving clue: {clue} (length: {length})")
    
    prompt = f"""You are solving a crossword puzzle. Here is the clue:

Clue: {clue}
Answer length: {length} letters

Think step by step:
1. What type of clue is this? (definition, wordplay, abbreviation, etc.)
2. What are the key words or hints?
3. What {length}-letter word or phrase fits?

Common crossword patterns:
- Abbreviations (e.g., "Street" = ST, "Doctor" = DR)
- Wordplay and puns
- Common crossword answers
- Proper nouns (names, places, brands)

Respond with ONLY the {length}-letter answer in capital letters, no spaces or punctuation.
"""
    
    for attempt in range(retries + 1):
        try:
            response = execute_llm(prompt)
            # Extract the answer from response
            lines = response.strip().split('\n')
            for line in lines:
                answer = ''.join(c for c in line.strip().upper() if c.isalpha())
                if len(answer) == length:
                    logging.info(f"Solved clue '{clue}' -> '{answer}'")
                    return answer
            
            # Try a more direct approach
            if attempt < retries:
                prompt = f"""Crossword clue: {clue}

Give me a {length}-letter answer in capital letters only:"""
                
        except Exception as e:
            logging.error(f"Error solving clue '{clue}': {e}")
    
    # Return None instead of placeholder to avoid polluting the grid
    logging.warning(f"Could not solve clue '{clue}'")
    return None

def solve_clue_with_constraints(clue, length, pattern, retries=3):
    """Solve clue with additional constraints from intersecting words"""
    logging.info(f"Solving clue with constraints: {clue} (length: {length}, pattern: {pattern})")
    
    if not pattern or '_' not in pattern:
        return solve_clue(clue, length, retries)
    
    constraint_text = f"\nKnown letters: {pattern} (where _ = unknown letter)"
    
    prompt = f"""Solve this crossword clue with constraints:

Clue: {clue}
Answer length: {length} letters{constraint_text}

The answer must match the pattern exactly. Each letter position is fixed where shown.

Respond with ONLY the {length}-letter answer in capital letters, no spaces or punctuation.
"""
    
    for attempt in range(retries + 1):
        try:
            response = execute_llm(prompt)
            lines = response.strip().split('\n')
            for line in lines:
                answer = ''.join(c for c in line.strip().upper() if c.isalpha())
                
                if len(answer) == length:
                    # Check if it matches the pattern
                    matches = True
                    for i, (a, p) in enumerate(zip(answer, pattern)):
                        if p != '_' and p != a:
                            matches = False
                            break
                    if matches:
                        logging.info(f"Solved constrained clue '{clue}' -> '{answer}'")
                        return answer
                    else:
                        logging.warning(f"Answer '{answer}' doesn't match pattern '{pattern}'")
                        
        except Exception as e:
            logging.error(f"Error solving constrained clue '{clue}': {e}")
    
    logging.warning(f"Could not solve constrained clue '{clue}' with pattern '{pattern}'")
    return None

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
        
        # Store answers
        across_answers = {}
        down_answers = {}
        
        # Solve easier clues first (shorter ones tend to be easier)
        all_clues = []
        for num, clue in across_clues.items():
            if num in positions:
                row, col = positions[num]
                length = get_word_length(grid, row, col, 'across')
                all_clues.append((length, 'across', num, clue))
        
        for num, clue in down_clues.items():
            if num in positions:
                row, col = positions[num]
                length = get_word_length(grid, row, col, 'down')
                all_clues.append((length, 'down', num, clue))
        
        # Sort by length (easier first)
        all_clues.sort(key=lambda x: x[0])
        
        # Solve clues iteratively with constraint propagation
        max_iterations = 4
        for iteration in range(max_iterations):
            logging.info(f"Iteration {iteration + 1}")
            improved = False
            
            for length, direction, num, clue in all_clues:
                if num in positions:
                    row, col = positions[num]
                    
                    # Build pattern from current state
                    pattern = ""
                    if direction == 'across':
                        for i in range(length):
                            if col + i < width:
                                cell = filled_grid[row][col + i]
                                pattern += cell if cell != '-' else '_'
                            else:
                                pattern += '_'
                    else:  # down
                        for i in range(length):
                            if row + i < height:
                                cell = filled_grid[row + i][col]
                                pattern += cell if cell != '-' else '_'
                            else:
                                pattern += '_'
                    
                    # Skip if already completely solved
                    if '_' not in pattern and '-' not in pattern:
                        continue
                    
                    # Solve the clue
                    if iteration == 0 or '_' in pattern or '-' in pattern:
                        if iteration == 0:
                            answer = solve_clue(clue, length)
                        else:
                            answer = solve_clue_with_constraints(clue, length, pattern)
                        
                        if answer:
                            # Store the answer
                            if direction == 'across':
                                across_answers[num] = answer
                            else:
                                down_answers[num] = answer
                            
                            # Place the answer in the grid
                            for i, letter in enumerate(answer):
                                if direction == 'across':
                                    if col + i < width:
                                        old_cell = filled_grid[row][col + i]
                                        if old_cell != letter:
                                            filled_grid[row][col + i] = letter
                                            improved = True
                                else:  # down
                                    if row + i < height:
                                        old_cell = filled_grid[row + i][col]
                                        if old_cell != letter:
                                            filled_grid[row + i][col] = letter
                                            improved = True
            
            # If no improvement, break early
            if not improved:
                logging.info(f"No improvement in iteration {iteration + 1}, stopping")
                break
        
        # Fill in any remaining answers from the grid
        for num in across_clues.keys():
            if num not in across_answers and num in positions:
                row, col = positions[num]
                length = get_word_length(grid, row, col, 'across')
                answer = ""
                for i in range(length):
                    if col + i < width:
                        cell = filled_grid[row][col + i]
                        answer += cell if cell != '-' else '?'
                across_answers[num] = answer
        
        for num in down_clues.keys():
            if num not in down_answers and num in positions:
                row, col = positions[num]
                length = get_word_length(grid, row, col, 'down')
                answer = ""
                for i in range(length):
                    if row + i < height:
                        cell = filled_grid[row + i][col]
                        answer += cell if cell != '-' else '?'
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