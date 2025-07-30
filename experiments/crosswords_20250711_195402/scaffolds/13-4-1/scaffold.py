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

def solve_crossword_clue(clue, length, pattern=None):
    """Solve a crossword clue with specialized prompting"""
    logging.info(f"Solving clue: {clue} (length: {length}, pattern: {pattern})")
    
    # Build a comprehensive prompt that covers crossword conventions
    prompt = f"""You are a crossword puzzle expert. Solve this clue:

CLUE: {clue}
LENGTH: {length} letters
{f"PATTERN: {pattern} (where _ = unknown letter)" if pattern else ""}

CROSSWORD SOLVING TIPS:
- Look for wordplay, puns, double meanings
- "Abbr." means abbreviation
- Fill-in-the-blank clues (with "___") often reference common phrases
- Years often indicate when something was introduced/created
- Consider pop culture references, brand names, proper nouns
- Remove all spaces and punctuation from multi-word answers
- Use only capital letters

Think step by step:
1. What type of clue is this?
2. What could the answer be?
3. Does it fit the length and pattern?

ANSWER (exactly {length} letters):"""

    try:
        response = execute_llm(prompt)
        
        # Extract the answer - look for the right length word
        words = re.findall(r'[A-Z]+', response.upper())
        
        for word in words:
            if len(word) == length:
                if pattern is None or matches_pattern(word, pattern):
                    logging.info(f"Solved: {clue} -> {word}")
                    return word
        
        # If no exact match, try to extract from the end of the response
        lines = response.strip().split('\n')
        for line in reversed(lines):
            clean_line = ''.join(c for c in line.upper() if c.isalpha())
            if len(clean_line) == length:
                if pattern is None or matches_pattern(clean_line, pattern):
                    logging.info(f"Solved: {clue} -> {clean_line}")
                    return clean_line
                    
    except Exception as e:
        logging.error(f"Error solving clue '{clue}': {e}")
    
    # Better fallback - try common crossword letters
    if pattern:
        # Use pattern as much as possible
        fallback = pattern.replace('_', 'E')
    else:
        fallback = 'E' * length
    
    logging.warning(f"Failed to solve clue '{clue}', using fallback: {fallback}")
    return fallback

def matches_pattern(word, pattern):
    """Check if word matches pattern"""
    if len(word) != len(pattern):
        return False
    
    for w, p in zip(word, pattern):
        if p != '_' and p != w:
            return False
    return True

def get_current_pattern(grid, row, col, length, direction):
    """Get current pattern for a word position"""
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0
    
    pattern = ""
    if direction == 'across':
        for i in range(length):
            if col + i < width:
                cell = grid[row][col + i]
                pattern += cell if cell != '-' else '_'
            else:
                pattern += '_'
    else:  # down
        for i in range(length):
            if row + i < height:
                cell = grid[row + i][col]
                pattern += cell if cell != '-' else '_'
            else:
                pattern += '_'
    
    return pattern

def fill_answer(grid, row, col, length, direction, answer):
    """Fill answer into grid"""
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0
    
    if direction == 'across':
        for i, letter in enumerate(answer):
            if col + i < width and i < len(answer):
                grid[row][col + i] = letter
    else:  # down
        for i, letter in enumerate(answer):
            if row + i < height and i < len(answer):
                grid[row + i][col] = letter

def process_input(input_string: str) -> str:
    try:
        grid, across_clues, down_clues = parse_input(input_string)
        
        if not grid:
            return "Error: No grid found"
        
        height = len(grid)
        width = len(grid[0]) if height > 0 else 0
        
        # Create filled grid
        filled_grid = [row[:] for row in grid]
        
        # Get clue positions
        positions = get_clue_positions(grid)
        
        # Create list of all clues with metadata
        all_clues = []
        for num, clue in across_clues.items():
            if num in positions:
                row, col = positions[num]
                length = get_word_length(grid, row, col, 'across')
                all_clues.append((num, clue, row, col, length, 'across'))
        
        for num, clue in down_clues.items():
            if num in positions:
                row, col = positions[num]
                length = get_word_length(grid, row, col, 'down')
                all_clues.append((num, clue, row, col, length, 'down'))
        
        # Solve with constraint propagation - multiple passes
        max_iterations = 6
        for iteration in range(max_iterations):
            logging.info(f"Iteration {iteration + 1}")
            
            changes_made = False
            
            # Sort clues by constraint level (most constrained first)
            def constraint_score(clue_info):
                num, clue, row, col, length, direction = clue_info
                pattern = get_current_pattern(filled_grid, row, col, length, direction)
                unknown_count = pattern.count('_')
                # Prefer shorter words and more constrained words
                return (unknown_count, length)
            
            all_clues.sort(key=constraint_score)
            
            for num, clue, row, col, length, direction in all_clues:
                pattern = get_current_pattern(filled_grid, row, col, length, direction)
                
                # Only solve if there are still unknowns
                if '_' in pattern:
                    old_pattern = pattern
                    answer = solve_crossword_clue(clue, length, pattern)
                    
                    # Validate the answer fits the pattern
                    if matches_pattern(answer, pattern):
                        # Check if this is actually a change
                        current_filled = pattern.replace('_', '?')
                        if answer != current_filled:
                            changes_made = True
                            fill_answer(filled_grid, row, col, length, direction, answer)
                            logging.info(f"Filled {direction} {num}: {answer}")
            
            if not changes_made:
                logging.info("No changes made, stopping early")
                break
        
        # Build final answers
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
        
        result.append('')
        
        # Add across answers
        result.append('Across:')
        for num in sorted(across_answers.keys()):
            result.append(f'  {num}. {across_answers[num]}')
        
        result.append('')
        
        # Add down answers
        result.append('Down:')
        for num in sorted(down_answers.keys()):
            result.append(f'  {num}. {down_answers[num]}')
        
        return '\n'.join(result)
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return f"Error: {str(e)}"