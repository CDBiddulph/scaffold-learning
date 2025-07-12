import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    try:
        # Parse the input
        lines = input_string.strip().split('\n')
        
        # Extract grid
        grid_lines = []
        i = 0
        while i < len(lines) and not lines[i].strip().startswith('Across:'):
            if lines[i].strip():
                grid_lines.append(lines[i].strip())
            i += 1
        
        # Parse clues
        across_clues = {}
        down_clues = {}
        
        current_section = None
        for line in lines[i:]:
            line = line.strip()
            if line.startswith('Across:'):
                current_section = 'across'
            elif line.startswith('Down:'):
                current_section = 'down'
            elif line and current_section:
                match = re.match(r'\s*(\d+)\.\s*(.+)', line)
                if match:
                    num = int(match.group(1))
                    clue = match.group(2).strip()
                    if current_section == 'across':
                        across_clues[num] = clue
                    else:
                        down_clues[num] = clue
        
        # Create grid structure
        grid = []
        for line in grid_lines:
            grid.append(line.split())
        
        # Analyze grid to find clue positions and lengths
        clue_info = analyze_grid(grid)
        
        # Solve clues with improved strategies and cross-checking
        across_answers, down_answers = solve_with_cross_checking(
            clue_info, across_clues, down_clues
        )
        
        # Fill the grid
        filled_grid = fill_grid(grid, clue_info, across_answers, down_answers)
        
        # Format output
        output_lines = []
        
        # Grid section
        for row in filled_grid:
            output_lines.append(' '.join(row))
        
        output_lines.append('')
        output_lines.append('Across:')
        for num in sorted(across_answers.keys()):
            output_lines.append(f'  {num}. {across_answers[num]}')
        
        output_lines.append('')
        output_lines.append('Down:')
        for num in sorted(down_answers.keys()):
            output_lines.append(f'  {num}. {down_answers[num]}')
        
        return '\n'.join(output_lines)
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return ""

def analyze_grid(grid):
    """Analyze the grid to find clue positions and lengths"""
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0
    
    clue_info = {'across': {}, 'down': {}}
    current_num = 1
    
    for row in range(height):
        for col in range(width):
            # Skip black squares
            if grid[row][col] == ".":
                continue
            
            # Check if this position starts a word
            starts_across = (
                (col == 0 or grid[row][col - 1] == ".")
                and col + 1 < width
                and grid[row][col + 1] != "."
            )
            starts_down = (
                (row == 0 or grid[row - 1][col] == ".")
                and row + 1 < height
                and grid[row + 1][col] != "."
            )
            
            if starts_across or starts_down:
                if starts_across:
                    # Calculate length of across word
                    length = 0
                    for c in range(col, width):
                        if grid[row][c] == ".":
                            break
                        length += 1
                    clue_info['across'][current_num] = {
                        'position': (row, col),
                        'length': length
                    }
                
                if starts_down:
                    # Calculate length of down word
                    length = 0
                    for r in range(row, height):
                        if grid[r][col] == ".":
                            break
                        length += 1
                    clue_info['down'][current_num] = {
                        'position': (row, col),
                        'length': length
                    }
                
                current_num += 1
    
    return clue_info

def solve_with_cross_checking(clue_info, across_clues, down_clues):
    """Solve clues with cross-checking for consistency"""
    
    # First pass: solve all clues independently
    across_answers = {}
    down_answers = {}
    
    for num, clue in across_clues.items():
        if num in clue_info['across']:
            length = clue_info['across'][num]['length']
            answer = solve_clue_improved(clue, length)
            across_answers[num] = answer
            logging.info(f"Across {num}: {clue} -> {answer} (length {length})")
    
    for num, clue in down_clues.items():
        if num in clue_info['down']:
            length = clue_info['down'][num]['length']
            answer = solve_clue_improved(clue, length)
            down_answers[num] = answer
            logging.info(f"Down {num}: {clue} -> {answer} (length {length})")
    
    # Second pass: check for conflicts and resolve
    conflicts = find_conflicts(clue_info, across_answers, down_answers)
    
    # Resolve conflicts by re-solving clues with constraints
    for conflict in conflicts:
        logging.warning(f"Conflict found: {conflict}")
        # Try to resolve by re-solving one of the conflicting clues
        if resolve_conflict(conflict, clue_info, across_clues, down_clues, across_answers, down_answers):
            logging.info(f"Resolved conflict: {conflict}")
    
    return across_answers, down_answers

def solve_clue_improved(clue, length):
    """Solve a crossword clue with improved strategies"""
    
    # Try focused crossword solving approach
    answer = try_focused_crossword_solving(clue, length)
    if answer and len(answer) == length:
        return answer
    
    # Try reasoning approach
    answer = try_reasoning_approach(clue, length)
    if answer and len(answer) == length:
        return answer
    
    # Try multiple attempts with different prompts
    answer = try_multiple_attempts(clue, length)
    if answer and len(answer) == length:
        return answer
    
    # Fallback: return placeholder
    logging.warning(f"Could not solve clue '{clue}' with length {length}")
    return 'X' * length

def try_focused_crossword_solving(clue, length):
    """Try focused crossword solving with specific strategies"""
    prompt = f"""You are a crossword puzzle expert. Solve this clue carefully:

Clue: "{clue}"
Answer length: {length} letters

CROSSWORD SOLVING STRATEGY:
1. Look for the most direct, common meaning first
2. Consider crossword conventions:
   - "Informally" or "for short" = abbreviations
   - Question marks often indicate wordplay
   - Think about common crossword answers
3. For {length}-letter words, consider typical crossword vocabulary
4. Avoid overthinking - the simplest answer is often correct

What is the most likely crossword answer?

Respond with ONLY the answer in capital letters:"""
    
    try:
        response = execute_llm(prompt)
        answer = ''.join(c for c in response.strip().upper() if c.isalpha())
        return answer
    except Exception as e:
        logging.error(f"Error in focused crossword solving: {e}")
        return None

def try_reasoning_approach(clue, length):
    """Try step-by-step reasoning approach"""
    prompt = f"""Think step by step about this crossword clue:

Clue: "{clue}"
Length: {length} letters

Step 1: What are the key words in this clue?
Step 2: What is the most straightforward interpretation?
Step 3: Are there any wordplay elements or tricks?
Step 4: What {length}-letter words fit this meaning?
Step 5: Which answer is most likely in a crossword?

Final answer (capital letters only):"""
    
    try:
        response = execute_llm(prompt)
        # Extract the last line that looks like an answer
        lines = response.strip().split('\n')
        for line in reversed(lines):
            candidate = ''.join(c for c in line.strip().upper() if c.isalpha())
            if len(candidate) == length:
                return candidate
    except Exception as e:
        logging.error(f"Error in reasoning approach: {e}")
    
    return None

def try_multiple_attempts(clue, length):
    """Try multiple different approaches"""
    prompts = [
        f'Crossword clue: "{clue}" ({length} letters)\nMost common answer:',
        f'Complete this crossword: "{clue}" = _____ ({length} letters)',
        f'What {length}-letter word best fits: "{clue}"?'
    ]
    
    for prompt in prompts:
        try:
            response = execute_llm(prompt)
            answer = ''.join(c for c in response.strip().upper() if c.isalpha())
            if len(answer) == length:
                return answer
        except Exception as e:
            logging.error(f"Error in multiple attempts: {e}")
            continue
    
    return None

def find_conflicts(clue_info, across_answers, down_answers):
    """Find conflicts at intersections"""
    conflicts = []
    
    for across_num, across_answer in across_answers.items():
        if across_num not in clue_info['across']:
            continue
        
        across_pos = clue_info['across'][across_num]['position']
        across_row, across_col = across_pos
        
        for down_num, down_answer in down_answers.items():
            if down_num not in clue_info['down']:
                continue
            
            down_pos = clue_info['down'][down_num]['position']
            down_row, down_col = down_pos
            
            # Check if they intersect
            if (across_row >= down_row and 
                across_row < down_row + len(down_answer) and
                across_col <= down_col and 
                across_col + len(across_answer) > down_col):
                
                # They intersect - check if letters match
                across_idx = down_col - across_col
                down_idx = across_row - down_row
                
                if (0 <= across_idx < len(across_answer) and 
                    0 <= down_idx < len(down_answer)):
                    
                    across_letter = across_answer[across_idx]
                    down_letter = down_answer[down_idx]
                    
                    if across_letter != down_letter:
                        conflicts.append({
                            'across': (across_num, across_answer),
                            'down': (down_num, down_answer),
                            'intersection': (across_row, down_col),
                            'across_letter': across_letter,
                            'down_letter': down_letter
                        })
    
    return conflicts

def resolve_conflict(conflict, clue_info, across_clues, down_clues, across_answers, down_answers):
    """Try to resolve a conflict by re-solving one of the clues"""
    across_num, across_answer = conflict['across']
    down_num, down_answer = conflict['down']
    
    # Try re-solving the down clue with the constraint
    if down_num in down_clues:
        down_clue = down_clues[down_num]
        down_length = clue_info['down'][down_num]['length']
        
        # Try solving with intersection constraint
        new_answer = solve_clue_with_constraint(
            down_clue, down_length, conflict['across_letter'], 
            conflict['intersection'][0] - clue_info['down'][down_num]['position'][0]
        )
        
        if new_answer and len(new_answer) == down_length:
            down_answers[down_num] = new_answer
            return True
    
    return False

def solve_clue_with_constraint(clue, length, required_letter, position):
    """Solve clue with a required letter at a specific position"""
    prompt = f"""Solve this crossword clue with a constraint:

Clue: "{clue}"
Length: {length} letters
Constraint: The letter at position {position + 1} must be '{required_letter}'

What {length}-letter word fits this clue and has '{required_letter}' at position {position + 1}?

Answer (capital letters only):"""
    
    try:
        response = execute_llm(prompt)
        answer = ''.join(c for c in response.strip().upper() if c.isalpha())
        if len(answer) == length and answer[position] == required_letter:
            return answer
    except Exception as e:
        logging.error(f"Error solving clue with constraint: {e}")
    
    return None

def fill_grid(grid, clue_info, across_answers, down_answers):
    """Fill the grid with the solved answers"""
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0
    
    # Create filled grid
    filled_grid = [row[:] for row in grid]
    
    # Fill across answers
    for num, answer in across_answers.items():
        if num in clue_info['across']:
            row, col = clue_info['across'][num]['position']
            for i, letter in enumerate(answer):
                if col + i < width:
                    filled_grid[row][col + i] = letter
    
    # Fill down answers
    for num, answer in down_answers.items():
        if num in clue_info['down']:
            row, col = clue_info['down'][num]['position']
            for i, letter in enumerate(answer):
                if row + i < height:
                    filled_grid[row + i][col] = letter
    
    return filled_grid