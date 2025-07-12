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

def solve_clue_robust(clue, length, attempt_count=3):
    """Solve a crossword clue with multiple attempts and better prompting"""
    logging.info(f"Solving clue: {clue} (length: {length})")
    
    # Try multiple prompt variations
    prompts = [
        f"Crossword clue: {clue}\nAnswer length: {length} letters\nAnswer (capital letters only):",
        f"What {length}-letter word fits this crossword clue: {clue}\nAnswer:",
        f"Solve: {clue}\nLength: {length} letters\nProvide only the answer in capitals:",
    ]
    
    candidates = []
    
    for prompt in prompts:
        for attempt in range(attempt_count):
            try:
                response = execute_llm(prompt)
                answer = ''.join(c for c in response.strip().upper() if c.isalpha())
                
                # Find the best substring of the correct length
                if len(answer) >= length:
                    for i in range(len(answer) - length + 1):
                        candidate = answer[i:i+length]
                        if len(candidate) == length:
                            candidates.append(candidate)
                            break
                    
            except Exception as e:
                logging.error(f"Error solving clue '{clue}': {e}")
    
    # Return most common answer or fallback
    if candidates:
        from collections import Counter
        counter = Counter(candidates)
        best_answer = counter.most_common(1)[0][0]
        logging.info(f"Solved clue '{clue}' -> '{best_answer}'")
        return best_answer
    
    # Fallback
    logging.warning(f"Failed to solve clue '{clue}', using fallback")
    return 'A' * length

def solve_meta_clue(clue, length, referenced_answers):
    """Solve meta-clues that reference other clues"""
    logging.info(f"Solving meta-clue: {clue}")
    
    # Build context with referenced answers
    context = f"Crossword clue: {clue}\nAnswer length: {length} letters\n"
    if referenced_answers:
        context += "Referenced answers: " + ", ".join(referenced_answers) + "\n"
    context += "Answer (capital letters only):"
    
    try:
        response = execute_llm(context)
        answer = ''.join(c for c in response.strip().upper() if c.isalpha())
        
        if len(answer) >= length:
            for i in range(len(answer) - length + 1):
                candidate = answer[i:i+length]
                if len(candidate) == length:
                    return candidate
    except Exception as e:
        logging.error(f"Error solving meta-clue '{clue}': {e}")
    
    return 'A' * length

def detect_meta_clues(clue_text):
    """Detect if a clue references other clues"""
    # Look for patterns like "17-, 23-, 31-" in the clue text
    pattern = r'(\d+)-(?:,?\s*\d+-)*'
    matches = re.findall(pattern, clue_text)
    if matches:
        # Extract all referenced clue numbers
        all_nums = re.findall(r'\d+', clue_text)
        return [int(num) for num in all_nums if num.isdigit()]
    return []

def solve_with_light_constraints(clue, length, filled_grid, row, col, direction):
    """Solve clue with light constraint checking"""
    # Build a partial pattern from high-confidence letters only
    pattern = '_' * length
    
    if direction == 'across':
        for i in range(length):
            if col + i < len(filled_grid[0]):
                cell = filled_grid[row][col + i]
                if cell != '-' and cell.isalpha():
                    pattern = pattern[:i] + cell + pattern[i+1:]
    else:  # down
        for i in range(length):
            if row + i < len(filled_grid):
                cell = filled_grid[row + i][col]
                if cell != '-' and cell.isalpha():
                    pattern = pattern[:i] + cell + pattern[i+1:]
    
    # Only use pattern if it has some constraints
    if pattern.count('_') < length:
        logging.info(f"Using pattern constraint: {pattern}")
        prompt = f"Crossword clue: {clue}\nPattern: {pattern} (use _ for unknown)\nAnswer:"
        
        try:
            response = execute_llm(prompt)
            answer = ''.join(c for c in response.strip().upper() if c.isalpha())
            
            if len(answer) == length:
                # Check if it matches the pattern
                matches = True
                for i, (a, p) in enumerate(zip(answer, pattern)):
                    if p != '_' and p != a:
                        matches = False
                        break
                if matches:
                    return answer
        except Exception as e:
            logging.error(f"Error with constrained solving: {e}")
    
    # Fall back to unconstrained solving
    return solve_clue_robust(clue, length)

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
        
        # First pass: solve all clues independently
        across_answers = {}
        down_answers = {}
        
        # Solve regular across clues first
        for num, clue in across_clues.items():
            if num in positions:
                row, col = positions[num]
                length = get_word_length(grid, row, col, 'across')
                
                # Check if this is a meta-clue
                referenced_clues = detect_meta_clues(clue)
                if referenced_clues:
                    # Solve referenced clues first if possible
                    referenced_answers = []
                    for ref_num in referenced_clues:
                        if ref_num in across_answers:
                            referenced_answers.append(across_answers[ref_num])
                    
                    answer = solve_meta_clue(clue, length, referenced_answers)
                else:
                    answer = solve_clue_robust(clue, length)
                
                across_answers[num] = answer
                
                # Place the answer in the grid
                for i, letter in enumerate(answer):
                    if col + i < width:
                        filled_grid[row][col + i] = letter
        
        # Solve down clues with light constraints
        for num, clue in down_clues.items():
            if num in positions:
                row, col = positions[num]
                length = get_word_length(grid, row, col, 'down')
                
                answer = solve_with_light_constraints(clue, length, filled_grid, row, col, 'down')
                down_answers[num] = answer
                
                # Place the answer in the grid
                for i, letter in enumerate(answer):
                    if row + i < height:
                        filled_grid[row + i][col] = letter
        
        # Second pass: solve meta-clues now that we have more answers
        for num, clue in across_clues.items():
            if num in positions:
                referenced_clues = detect_meta_clues(clue)
                if referenced_clues:
                    # Get the last words of referenced answers
                    referenced_answers = []
                    for ref_num in referenced_clues:
                        if ref_num in across_answers:
                            answer = across_answers[ref_num]
                            # This is a simplification - in practice, we'd need to parse the clue better
                            referenced_answers.append(answer)
                    
                    row, col = positions[num]
                    length = get_word_length(grid, row, col, 'across')
                    answer = solve_meta_clue(clue, length, referenced_answers)
                    
                    across_answers[num] = answer
                    
                    # Update the grid
                    for i, letter in enumerate(answer):
                        if col + i < width:
                            filled_grid[row][col + i] = letter
        
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