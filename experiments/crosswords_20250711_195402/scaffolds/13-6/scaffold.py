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

def get_word_info(grid, positions, clue_num, direction):
    """Get word length and positions for a clue"""
    if clue_num not in positions:
        return None, []
    
    row, col = positions[clue_num]
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0
    
    word_positions = []
    
    if direction == 'across':
        c = col
        while c < width and grid[row][c] != '.':
            word_positions.append((row, c))
            c += 1
    else:  # down
        r = row
        while r < height and grid[r][col] != '.':
            word_positions.append((r, col))
            r += 1
    
    return len(word_positions), word_positions

def solve_clue_smart(clue, length, pattern=None, retries=3):
    """Solve a crossword clue with better prompting"""
    logging.info(f"Solving clue: {clue} (length: {length}, pattern: {pattern})")
    
    # Build constraint text
    constraint_text = f"The answer must be exactly {length} letters long."
    if pattern and pattern.count('_') < length:
        constraint_text += f" Known letters: {pattern} (where _ means unknown)"
    
    prompt = f"""This is a crossword puzzle clue. Give me the most likely crossword answer.

Clue: {clue}
{constraint_text}

Important: Crossword answers are typically:
- Common words or phrases
- Proper nouns (names, places)
- Wordplay or puns
- Abbreviations or acronyms

Respond with ONLY the answer in capital letters, no spaces, no explanation.
Example: For "Capital of France (5 letters)", respond: PARIS"""
    
    best_answer = None
    
    for attempt in range(retries + 1):
        try:
            response = execute_llm(prompt)
            answer = ''.join(c for c in response.strip().upper() if c.isalpha())
            
            if len(answer) == length:
                # Check pattern match if provided
                if pattern:
                    matches = True
                    for i, (a, p) in enumerate(zip(answer, pattern)):
                        if p != '_' and p != a:
                            matches = False
                            break
                    if matches:
                        logging.info(f"Solved: '{clue}' -> '{answer}'")
                        return answer
                else:
                    logging.info(f"Solved: '{clue}' -> '{answer}'")
                    return answer
                    
                # If no pattern, keep this as best answer
                if not best_answer:
                    best_answer = answer
                    
        except Exception as e:
            logging.error(f"Error solving clue '{clue}': {e}")
    
    # Return best answer or fallback
    if best_answer:
        return best_answer
    
    # Fallback: try to use common crossword words
    if length <= 4:
        common_short = {3: ['THE', 'AND', 'ARE', 'ERA', 'EAR', 'EEL'], 
                       4: ['AREA', 'ARIA', 'EARL', 'ELSE']}
        if length in common_short:
            return common_short[length][0]
    
    return 'A' * length

def get_pattern_from_grid(grid, positions):
    """Extract current pattern from filled grid"""
    pattern = ""
    for row, col in positions:
        cell = grid[row][col]
        if cell.isalpha():
            pattern += cell
        else:
            pattern += '_'
    return pattern

def calculate_priority(clue_num, across_clues, down_clues, filled_grid, positions):
    """Calculate priority for solving a clue based on constraints"""
    if clue_num in across_clues:
        clue = across_clues[clue_num]
        direction = 'across'
    else:
        clue = down_clues[clue_num]
        direction = 'down'
    
    # Get word positions
    _, word_positions = get_word_info(filled_grid, positions, clue_num, direction)
    
    # Count known letters
    known_letters = sum(1 for row, col in word_positions if filled_grid[row][col].isalpha())
    
    # Prioritize clues with more known letters and shorter length
    length = len(word_positions)
    priority = known_letters * 10 - length
    
    # Boost priority for certain clue types
    clue_lower = clue.lower()
    if any(word in clue_lower for word in ['abbr', 'acronym', 'initials']):
        priority += 5
    if length <= 4:
        priority += 2
    
    return priority

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
        
        # Solve clues in priority order
        max_iterations = 5
        for iteration in range(max_iterations):
            logging.info(f"Starting iteration {iteration + 1}")
            
            # Get all unsolved clues with priorities
            unsolved = []
            
            for clue_num in across_clues:
                if clue_num in positions:
                    _, word_positions = get_word_info(filled_grid, positions, clue_num, 'across')
                    pattern = get_pattern_from_grid(filled_grid, word_positions)
                    if '_' in pattern:
                        priority = calculate_priority(clue_num, across_clues, down_clues, filled_grid, positions)
                        unsolved.append((priority, clue_num, 'across', word_positions))
            
            for clue_num in down_clues:
                if clue_num in positions:
                    _, word_positions = get_word_info(filled_grid, positions, clue_num, 'down')
                    pattern = get_pattern_from_grid(filled_grid, word_positions)
                    if '_' in pattern:
                        priority = calculate_priority(clue_num, across_clues, down_clues, filled_grid, positions)
                        unsolved.append((priority, clue_num, 'down', word_positions))
            
            if not unsolved:
                logging.info("All clues solved!")
                break
            
            # Sort by priority (highest first)
            unsolved.sort(reverse=True)
            
            # Solve top priority clues
            changes_made = 0
            for priority, clue_num, direction, word_positions in unsolved[:10]:  # Top 10
                clue = across_clues[clue_num] if direction == 'across' else down_clues[clue_num]
                length = len(word_positions)
                pattern = get_pattern_from_grid(filled_grid, word_positions)
                
                if '_' in pattern:
                    answer = solve_clue_smart(clue, length, pattern)
                    
                    # Place answer in grid
                    for i, (row, col) in enumerate(word_positions):
                        if i < len(answer):
                            old_cell = filled_grid[row][col]
                            filled_grid[row][col] = answer[i]
                            if old_cell != answer[i]:
                                changes_made += 1
            
            logging.info(f"Iteration {iteration + 1}: {changes_made} changes made")
            if changes_made == 0:
                break
        
        # Build final answers
        across_answers = {}
        for clue_num in across_clues:
            if clue_num in positions:
                _, word_positions = get_word_info(filled_grid, positions, clue_num, 'across')
                answer = ''.join(filled_grid[row][col] for row, col in word_positions)
                across_answers[clue_num] = answer
        
        down_answers = {}
        for clue_num in down_clues:
            if clue_num in positions:
                _, word_positions = get_word_info(filled_grid, positions, clue_num, 'down')
                answer = ''.join(filled_grid[row][col] for row, col in word_positions)
                down_answers[clue_num] = answer
        
        # Format output
        result = []
        
        # Add filled grid
        for row in filled_grid:
            result.append(' '.join(row))
        
        result.append('')
        
        # Add across answers
        result.append('Across:')
        for clue_num in sorted(across_answers.keys()):
            result.append(f'  {clue_num}. {across_answers[clue_num]}')
        
        result.append('')
        
        # Add down answers
        result.append('Down:')
        for clue_num in sorted(down_answers.keys()):
            result.append(f'  {clue_num}. {down_answers[clue_num]}')
        
        return '\n'.join(result)
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return f"Error: {str(e)}"