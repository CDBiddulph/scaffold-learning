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

def solve_clue_improved(clue, length, pattern=None, retries=3):
    """Solve crossword clue with improved prompting strategies"""
    logging.info(f"Solving clue: {clue} (length: {length}, pattern: {pattern})")
    
    # Different prompting strategies
    prompts = []
    
    # Strategy 1: Direct crossword prompt
    base_prompt = f"""This is a crossword puzzle clue. Give me the exact answer.

Clue: {clue}
Answer length: {length} letters
{f"Pattern: {pattern} (where _ = unknown letter)" if pattern else ""}

Important:
- Answer must be exactly {length} letters
- Remove all spaces and punctuation from multi-word answers
- Use only capital letters
- Think about crossword conventions, wordplay, abbreviations

Answer:"""
    prompts.append(base_prompt)
    
    # Strategy 2: Fill-in-the-blank specific
    if "___" in clue:
        fill_prompt = f"""Complete this phrase for a crossword:
{clue}
The blank needs a {length}-letter word/phrase (remove spaces).

Answer:"""
        prompts.append(fill_prompt)
    
    # Strategy 3: Song/entertainment specific
    if any(word in clue.lower() for word in ['hit', 'song', 'album', 'movie', 'film']):
        song_prompt = f"""This crossword clue is about entertainment:
{clue}
Length: {length} letters
{f"Pattern: {pattern}" if pattern else ""}

For titles, remove all spaces and punctuation.
Answer:"""
        prompts.append(song_prompt)
    
    # Strategy 4: Simple and direct
    simple_prompt = f"""Crossword: {clue} ({length} letters)
{f"Pattern: {pattern}" if pattern else ""}
Answer:"""
    prompts.append(simple_prompt)
    
    for attempt in range(retries):
        try:
            prompt = prompts[attempt % len(prompts)]
            response = execute_llm(prompt)
            
            # Extract potential answers
            import re
            # Look for sequences of letters
            words = re.findall(r'[A-Z]+', response.upper())
            
            # Try each word that matches the length
            for word in words:
                if len(word) == length:
                    if pattern:
                        # Check if it matches the pattern
                        matches = True
                        for i, (w, p) in enumerate(zip(word, pattern)):
                            if p != '_' and p != w:
                                matches = False
                                break
                        if matches:
                            logging.info(f"Solved: {clue} -> {word}")
                            return word
                    else:
                        logging.info(f"Solved: {clue} -> {word}")
                        return word
            
            # If no exact match, try extracting from full response
            clean_response = ''.join(c for c in response.upper() if c.isalpha())
            if len(clean_response) == length:
                if pattern:
                    matches = True
                    for i, (c, p) in enumerate(zip(clean_response, pattern)):
                        if p != '_' and p != c:
                            matches = False
                            break
                    if matches:
                        logging.info(f"Solved: {clue} -> {clean_response}")
                        return clean_response
                else:
                    logging.info(f"Solved: {clue} -> {clean_response}")
                    return clean_response
                    
        except Exception as e:
            logging.error(f"Error solving clue '{clue}': {e}")
    
    # Better fallback - use common letters
    common_letters = 'ETAOINSHRDLCUMWFGYPBVKJXQZ'
    fallback = ''.join(common_letters[i % len(common_letters)] for i in range(length))
    logging.warning(f"Failed to solve clue '{clue}', using fallback: {fallback}")
    return fallback

def solve_multiple_candidates(clue, length, pattern=None):
    """Get multiple candidate answers for a clue"""
    logging.info(f"Getting candidates for: {clue} (length: {length})")
    
    prompt = f"""This is a crossword clue. Give me 3-5 possible answers.

Clue: {clue}
Length: {length} letters
{f"Pattern: {pattern}" if pattern else ""}

List possible answers, one per line:
1. 
2. 
3. 
4. 
5. """
    
    try:
        response = execute_llm(prompt)
        candidates = []
        
        # Extract candidates
        import re
        words = re.findall(r'[A-Z]+', response.upper())
        
        for word in words:
            if len(word) == length:
                if pattern:
                    matches = True
                    for i, (w, p) in enumerate(zip(word, pattern)):
                        if p != '_' and p != w:
                            matches = False
                            break
                    if matches:
                        candidates.append(word)
                else:
                    candidates.append(word)
        
        return candidates[:3]  # Return top 3
        
    except Exception as e:
        logging.error(f"Error getting candidates for '{clue}': {e}")
        return []

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
        
        # Solve with multiple iterations and better constraint propagation
        max_iterations = 4
        for iteration in range(max_iterations):
            logging.info(f"Iteration {iteration + 1}")
            
            # Track changes to see if we're making progress
            changes_made = False
            
            # Solve across clues
            for num, clue in across_clues.items():
                if num in positions:
                    row, col = positions[num]
                    length = get_word_length(grid, row, col, 'across')
                    
                    # Build pattern
                    pattern = ""
                    for i in range(length):
                        if col + i < width:
                            cell = filled_grid[row][col + i]
                            pattern += cell if cell != '-' else '_'
                        else:
                            pattern += '_'
                    
                    # Only solve if incomplete
                    if '_' in pattern or '-' in pattern:
                        answer = solve_clue_improved(clue, length, pattern)
                        
                        # Check if this is actually an improvement
                        current_answer = ''.join(filled_grid[row][col + i] for i in range(length) if col + i < width)
                        if answer != current_answer:
                            changes_made = True
                            
                            # Place the answer
                            for i, letter in enumerate(answer):
                                if col + i < width:
                                    filled_grid[row][col + i] = letter
            
            # Solve down clues
            for num, clue in down_clues.items():
                if num in positions:
                    row, col = positions[num]
                    length = get_word_length(grid, row, col, 'down')
                    
                    # Build pattern
                    pattern = ""
                    for i in range(length):
                        if row + i < height:
                            cell = filled_grid[row + i][col]
                            pattern += cell if cell != '-' else '_'
                        else:
                            pattern += '_'
                    
                    # Only solve if incomplete
                    if '_' in pattern or '-' in pattern:
                        answer = solve_clue_improved(clue, length, pattern)
                        
                        # Check if this is actually an improvement
                        current_answer = ''.join(filled_grid[row + i][col] for i in range(length) if row + i < height)
                        if answer != current_answer:
                            changes_made = True
                            
                            # Place the answer
                            for i, letter in enumerate(answer):
                                if row + i < height:
                                    filled_grid[row + i][col] = letter
            
            # If no changes made, break early
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