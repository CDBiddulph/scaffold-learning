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
        
        height = len(grid)
        width = len(grid[0]) if height > 0 else 0
        
        # Analyze grid to find clue positions and lengths
        clue_info = analyze_grid(grid)
        
        # Solve clues with improved strategies
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

def solve_clue_improved(clue, length):
    """Solve a crossword clue with improved strategies"""
    
    # Strategy 1: Expert crossword solving with conventions
    answer = try_expert_crossword_prompt(clue, length)
    if answer and len(answer) == length:
        return answer
    
    # Strategy 2: Multiple options approach
    answer = try_multiple_options_prompt(clue, length)
    if answer and len(answer) == length:
        return answer
    
    # Strategy 3: Reasoning approach
    answer = try_reasoning_prompt(clue, length)
    if answer and len(answer) == length:
        return answer
    
    # Strategy 4: Simple direct approach
    answer = try_simple_prompt(clue, length)
    if answer and len(answer) == length:
        return answer
    
    # Fallback: return placeholder
    logging.warning(f"Could not solve clue '{clue}' with length {length}")
    return 'X' * length

def try_expert_crossword_prompt(clue, length):
    """Try expert crossword solving with conventions"""
    prompt = f"""You are a crossword expert. Solve this clue: "{clue}"

The answer is exactly {length} letters long.

KEY CROSSWORD CONVENTIONS:
- "Informally" or "for short" = use abbreviations or nicknames
- Foreign language clues use foreign words (e.g., "Capital of Italia" = ROMA)
- Two-word phrases often become one word (e.g., "spa day" = SPADAY)
- "Group of" clues often want compound words
- Consider multiple meanings and wordplay
- Think about common crossword answers

Respond with ONLY the answer in capital letters, nothing else.

Answer:"""
    
    try:
        response = execute_llm(prompt)
        answer = ''.join(c for c in response.strip().upper() if c.isalpha())
        return answer
    except Exception as e:
        logging.error(f"Error in expert crossword prompt: {e}")
        return None

def try_multiple_options_prompt(clue, length):
    """Generate multiple options and pick the best"""
    prompt = f"""For the crossword clue "{clue}" ({length} letters), provide 3 different possible answers.

Consider:
- Different interpretations of the clue
- Crossword conventions and common answers
- Wordplay possibilities

Format:
1. ANSWER1
2. ANSWER2  
3. ANSWER3

Provide only the numbered list."""
    
    try:
        response = execute_llm(prompt)
        lines = response.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if line and line[0].isdigit() and '.' in line:
                parts = line.split('.', 1)
                if len(parts) > 1:
                    answer = ''.join(c for c in parts[1].strip().upper() if c.isalpha())
                    if len(answer) == length:
                        return answer
        
    except Exception as e:
        logging.error(f"Error in multiple options prompt: {e}")
    
    return None

def try_reasoning_prompt(clue, length):
    """Use step-by-step reasoning"""
    prompt = f"""Think step by step about this crossword clue: "{clue}"
Length: {length} letters

1. What are the key words?
2. What could this clue mean?
3. Any wordplay or tricks?
4. What {length}-letter words fit?

End with just the answer in capitals on the last line."""
    
    try:
        response = execute_llm(prompt)
        lines = response.strip().split('\n')
        
        # Look for the last line with only letters of the right length
        for line in reversed(lines):
            candidate = ''.join(c for c in line.strip().upper() if c.isalpha())
            if len(candidate) == length:
                return candidate
        
    except Exception as e:
        logging.error(f"Error in reasoning prompt: {e}")
    
    return None

def try_simple_prompt(clue, length):
    """Simple, direct approach"""
    prompt = f"""Crossword clue: {clue}
Length: {length} letters
Answer:"""
    
    try:
        response = execute_llm(prompt)
        answer = ''.join(c for c in response.strip().upper() if c.isalpha())
        return answer
    except Exception as e:
        logging.error(f"Error in simple prompt: {e}")
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