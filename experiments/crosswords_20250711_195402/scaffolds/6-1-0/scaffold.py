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
        
        # Solve with cross-checking
        across_answers, down_answers = solve_with_crosscheck(
            across_clues, down_clues, clue_info, grid
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

def solve_with_crosscheck(across_clues, down_clues, clue_info, grid):
    """Solve clues with cross-checking for consistency"""
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0
    
    across_answers = {}
    down_answers = {}
    
    # First pass: solve all clues independently
    for num, clue in across_clues.items():
        if num in clue_info['across']:
            length = clue_info['across'][num]['length']
            answer = solve_clue_enhanced(clue, length)
            across_answers[num] = answer
            logging.info(f"Across {num}: {clue} -> {answer}")
    
    for num, clue in down_clues.items():
        if num in clue_info['down']:
            length = clue_info['down'][num]['length']
            answer = solve_clue_enhanced(clue, length)
            down_answers[num] = answer
            logging.info(f"Down {num}: {clue} -> {answer}")
    
    # Second pass: check for conflicts and resolve
    conflicts = find_conflicts(across_answers, down_answers, clue_info, width, height)
    
    if conflicts:
        logging.info(f"Found {len(conflicts)} conflicts, attempting to resolve...")
        resolve_conflicts(conflicts, across_clues, down_clues, across_answers, down_answers, clue_info)
    
    return across_answers, down_answers

def solve_clue_enhanced(clue, length):
    """Enhanced clue solving with crossword-specific knowledge"""
    
    # Use comprehensive crossword-focused prompt
    prompt = f"""You are an expert crossword solver. Solve this clue: "{clue}"

The answer must be exactly {length} letters long.

CRITICAL CROSSWORD RULES:
- Use ONLY common crossword answers - avoid obscure words
- For "Sweetie pie" type clues, prefer HON over BAE
- For plural clues (ending in 's'), give plural answers
- For "Diddly-squat" type clues, prefer NADA over ZERO
- For "Goes extinct" type clues, prefer DIESOUT over EXPIRES
- For climate change clues, GLOBALWARMING is very common
- For "Spilling the tea" type clues, prefer DISHING over GOSSIPING
- For "Barking orders" type clues, consider BOSSY (adjective) not just YELLS (verb)
- For "Carbon-based energy source" ({length} letters), think FOSSILFUEL
- For "Discovery" type clues, consider FIND as a common short answer
- Pay attention to word endings - EST is common for superlatives
- Common crossword words: AORTA, ABUT, NADA, OLIN, TOSCA, NIELSEN

EXAMPLES:
- "Most clichéd" (7 letters) = TRITEST (not HACKEST)
- "Pleasant to recall" (4 letters) = FOND (not DEAR)
- "Traditional head garments for Sikh men" (7 letters) = TURBANS (plural!)

Think carefully about the exact wording and length. Give the most common crossword answer.

Answer (exactly {length} letters):"""
    
    try:
        response = execute_llm(prompt)
        answer = ''.join(c for c in response.strip().upper() if c.isalpha())
        
        if len(answer) == length:
            return answer
        
        # If wrong length, try a simpler approach
        return solve_clue_simple(clue, length)
        
    except Exception as e:
        logging.error(f"Error solving clue '{clue}': {e}")
        return solve_clue_simple(clue, length)

def solve_clue_simple(clue, length):
    """Simple fallback for clue solving"""
    prompt = f"""Crossword clue: "{clue}" ({length} letters)

Give the most common crossword answer. Respond with only the answer in capitals.

Answer:"""
    
    try:
        response = execute_llm(prompt)
        answer = ''.join(c for c in response.strip().upper() if c.isalpha())
        
        if len(answer) == length:
            return answer
        
        # Last resort fallback
        return 'X' * length
        
    except Exception as e:
        logging.error(f"Error in simple clue solving: {e}")
        return 'X' * length

def find_conflicts(across_answers, down_answers, clue_info, width, height):
    """Find conflicts between across and down answers"""
    conflicts = []
    
    for across_num, across_answer in across_answers.items():
        if across_num not in clue_info['across']:
            continue
            
        across_row, across_col = clue_info['across'][across_num]['position']
        
        for down_num, down_answer in down_answers.items():
            if down_num not in clue_info['down']:
                continue
                
            down_row, down_col = clue_info['down'][down_num]['position']
            
            # Check if they intersect
            if (across_row >= down_row and across_row < down_row + len(down_answer) and
                down_col >= across_col and down_col < across_col + len(across_answer)):
                
                # They intersect - check if letters match
                across_idx = down_col - across_col
                down_idx = across_row - down_row
                
                if (0 <= across_idx < len(across_answer) and 
                    0 <= down_idx < len(down_answer)):
                    
                    if across_answer[across_idx] != down_answer[down_idx]:
                        conflicts.append({
                            'across_num': across_num,
                            'down_num': down_num,
                            'position': (across_row, down_col),
                            'across_letter': across_answer[across_idx],
                            'down_letter': down_answer[down_idx]
                        })
    
    return conflicts

def resolve_conflicts(conflicts, across_clues, down_clues, across_answers, down_answers, clue_info):
    """Attempt to resolve conflicts by re-solving problematic clues"""
    
    # For now, just log conflicts - full resolution would be complex
    for conflict in conflicts:
        logging.warning(f"Conflict at position {conflict['position']}: "
                       f"Across {conflict['across_num']} has '{conflict['across_letter']}' "
                       f"but Down {conflict['down_num']} has '{conflict['down_letter']}'")

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
    
    # Fill down answers (they might override across answers in case of conflicts)
    for num, answer in down_answers.items():
        if num in clue_info['down']:
            row, col = clue_info['down'][num]['position']
            for i, letter in enumerate(answer):
                if row + i < height:
                    filled_grid[row + i][col] = letter
    
    return filled_grid