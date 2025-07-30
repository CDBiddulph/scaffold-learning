import logging
import re
from llm_executor import execute_llm

def parse_input(input_string: str):
    """Parse the input to extract grid and clues"""
    lines = input_string.strip().split('\n')
    
    # Find where the grid ends and clues begin
    grid_lines = []
    clues_start = 0
    
    for i, line in enumerate(lines):
        if line.strip().startswith('Across:'):
            clues_start = i
            break
        grid_lines.append(line)
    
    # Parse grid
    grid = []
    for line in grid_lines:
        if line.strip():
            grid.append(line.strip().split())
    
    # Parse clues
    across_clues = {}
    down_clues = {}
    
    current_section = None
    for i in range(clues_start, len(lines)):
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
    
    return grid, across_clues, down_clues

def solve_clue_with_llm(clue_text, length, intersecting_letters=None, attempts=3):
    """Solve a clue using the LLM with multiple attempts and better prompting"""
    
    # Build pattern string
    pattern = ['_'] * length
    if intersecting_letters:
        for pos, letter in intersecting_letters.items():
            if 0 <= pos < length:
                pattern[pos] = letter
    pattern_str = ''.join(pattern)
    
    # Try multiple prompting strategies
    prompts = [
        f"""Solve this crossword clue.

Clue: {clue_text}
Length: {length} letters
Pattern: {pattern_str}

Think step by step:
1. Consider the literal meaning
2. Look for wordplay, puns, abbreviations
3. Check if it fits the pattern
4. Prefer common crossword answers

Answer (uppercase letters only):""",
        
        f"""Crossword clue: "{clue_text}"
Answer length: {length}
Known letters: {pattern_str}

This is a standard crossword puzzle. Give only the answer in uppercase letters.""",
        
        f"""Fill in the crossword answer:
Clue: {clue_text}
Pattern: {pattern_str} ({length} letters)

Answer:"""
    ]
    
    for attempt in range(attempts):
        prompt = prompts[attempt % len(prompts)]
        
        try:
            response = execute_llm(prompt)
            # Extract the answer from the response
            words = response.upper().split()
            for word in words:
                clean_word = ''.join(c for c in word if c.isalpha())
                if len(clean_word) == length:
                    # Validate against known intersecting letters
                    if intersecting_letters:
                        valid = True
                        for pos, letter in intersecting_letters.items():
                            if 0 <= pos < len(clean_word) and clean_word[pos] != letter:
                                valid = False
                                break
                        if valid:
                            return clean_word
                    else:
                        return clean_word
        except Exception as e:
            logging.error(f"Error solving clue '{clue_text}': {e}")
    
    return None

def get_word_positions(grid):
    """Get all word positions and their clue numbers"""
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0
    
    positions = {}  # clue_num -> {'across': (row, col, length), 'down': (row, col, length)}
    current_num = 1
    
    for row in range(height):
        for col in range(width):
            if grid[row][col] == '.':
                continue
            
            # Check if this position starts a word
            starts_across = (
                (col == 0 or grid[row][col - 1] == '.')
                and col + 1 < width
                and grid[row][col + 1] != '.'
            )
            starts_down = (
                (row == 0 or grid[row - 1][col] == '.')
                and row + 1 < height
                and grid[row + 1][col] != '.'
            )
            
            if starts_across or starts_down:
                positions[current_num] = {}
                
                if starts_across:
                    length = 0
                    for c in range(col, width):
                        if grid[row][c] == '.':
                            break
                        length += 1
                    positions[current_num]['across'] = (row, col, length)
                
                if starts_down:
                    length = 0
                    for r in range(row, height):
                        if grid[r][col] == '.':
                            break
                        length += 1
                    positions[current_num]['down'] = (row, col, length)
                
                current_num += 1
    
    return positions

def prioritize_clues(across_clues, down_clues, positions):
    """Prioritize clues by difficulty/obviousness"""
    easy_patterns = [
        r'___ \(.*\)',  # Fill in the blank
        r'Random ___ of',
        r'"What\'s more',
        r'Future fungus',
        r'Eating plan',
        r'Slightest little sound'
    ]
    
    priority_across = []
    priority_down = []
    
    for clue_num, clue_text in across_clues.items():
        priority = 1  # default priority
        for pattern in easy_patterns:
            if re.search(pattern, clue_text, re.IGNORECASE):
                priority = 0  # high priority
                break
        # Shorter answers are often easier
        if clue_num in positions and 'across' in positions[clue_num]:
            length = positions[clue_num]['across'][2]
            if length <= 4:
                priority = 0
        priority_across.append((priority, clue_num, clue_text))
    
    for clue_num, clue_text in down_clues.items():
        priority = 1  # default priority
        for pattern in easy_patterns:
            if re.search(pattern, clue_text, re.IGNORECASE):
                priority = 0  # high priority
                break
        # Shorter answers are often easier
        if clue_num in positions and 'down' in positions[clue_num]:
            length = positions[clue_num]['down'][2]
            if length <= 4:
                priority = 0
        priority_down.append((priority, clue_num, clue_text))
    
    priority_across.sort()
    priority_down.sort()
    
    return priority_across, priority_down

def solve_crossword(grid, across_clues, down_clues):
    """Solve the crossword puzzle with improved strategy"""
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0
    
    # Initialize filled grid
    filled_grid = [row[:] for row in grid]
    for row in range(height):
        for col in range(width):
            if filled_grid[row][col] == '-':
                filled_grid[row][col] = ' '
    
    # Get word positions
    positions = get_word_positions(grid)
    
    # Prioritize clues
    priority_across, priority_down = prioritize_clues(across_clues, down_clues, positions)
    
    # Track solved answers
    solved_across = {}
    solved_down = {}
    
    # Multiple solving passes with increasing constraints
    for pass_num in range(4):
        logging.info(f"Solving pass {pass_num + 1}")
        made_progress = False
        
        # Solve across clues in priority order
        for priority, clue_num, clue_text in priority_across:
            if clue_num in solved_across:
                continue
            
            if clue_num in positions and 'across' in positions[clue_num]:
                row, col, length = positions[clue_num]['across']
                
                # Get intersecting letters
                intersecting_letters = {}
                for i in range(length):
                    if col + i < width and filled_grid[row][col + i] != ' ':
                        intersecting_letters[i] = filled_grid[row][col + i]
                
                # Only try to solve if we have enough constraints in later passes
                if pass_num == 0 or len(intersecting_letters) >= max(1, length // 4):
                    answer = solve_clue_with_llm(clue_text, length, intersecting_letters)
                    if answer:
                        solved_across[clue_num] = answer
                        made_progress = True
                        # Fill in the grid
                        for i, letter in enumerate(answer):
                            if col + i < width:
                                filled_grid[row][col + i] = letter
        
        # Solve down clues in priority order
        for priority, clue_num, clue_text in priority_down:
            if clue_num in solved_down:
                continue
            
            if clue_num in positions and 'down' in positions[clue_num]:
                row, col, length = positions[clue_num]['down']
                
                # Get intersecting letters
                intersecting_letters = {}
                for i in range(length):
                    if row + i < height and filled_grid[row + i][col] != ' ':
                        intersecting_letters[i] = filled_grid[row + i][col]
                
                # Only try to solve if we have enough constraints in later passes
                if pass_num == 0 or len(intersecting_letters) >= max(1, length // 4):
                    answer = solve_clue_with_llm(clue_text, length, intersecting_letters)
                    if answer:
                        solved_down[clue_num] = answer
                        made_progress = True
                        # Fill in the grid
                        for i, letter in enumerate(answer):
                            if row + i < height:
                                filled_grid[row + i][col] = letter
        
        if not made_progress:
            break
    
    return filled_grid, solved_across, solved_down

def format_output(filled_grid, solved_across, solved_down):
    """Format the output"""
    result = []
    
    # Add grid
    for row in filled_grid:
        result.append(' '.join(row))
    
    result.append('')
    
    # Add across clues
    result.append('Across:')
    for clue_num in sorted(solved_across.keys()):
        result.append(f'  {clue_num}. {solved_across[clue_num]}')
    
    result.append('')
    
    # Add down clues
    result.append('Down:')
    for clue_num in sorted(solved_down.keys()):
        result.append(f'  {clue_num}. {solved_down[clue_num]}')
    
    return '\n'.join(result)

def process_input(input_string: str) -> str:
    try:
        logging.info("Starting crossword puzzle solution")
        grid, across_clues, down_clues = parse_input(input_string)
        logging.info(f"Parsed grid: {len(grid)}x{len(grid[0]) if grid else 0}")
        logging.info(f"Across clues: {len(across_clues)}, Down clues: {len(down_clues)}")
        
        filled_grid, solved_across, solved_down = solve_crossword(grid, across_clues, down_clues)
        logging.info(f"Solved {len(solved_across)} across clues and {len(solved_down)} down clues")
        
        result = format_output(filled_grid, solved_across, solved_down)
        return result
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return ""