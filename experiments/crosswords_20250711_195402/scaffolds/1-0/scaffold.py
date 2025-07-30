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

def get_word_length(grid, row, col, direction):
    """Get the length of a word starting at (row, col) in the given direction"""
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0
    
    length = 0
    if direction == 'across':
        for c in range(col, width):
            if grid[row][c] == '.':
                break
            length += 1
    else:  # down
        for r in range(row, height):
            if grid[r][col] == '.':
                break
            length += 1
    
    return length

def solve_clue_with_context(clue_text, length, intersecting_letters=None):
    """Solve a clue with improved prompting and multiple attempts"""
    
    # Build constraint description
    constraints = f"The answer must be exactly {length} letters."
    if intersecting_letters:
        letter_info = []
        for pos, letter in intersecting_letters.items():
            letter_info.append(f"position {pos+1} is '{letter}'")
        if letter_info:
            constraints += f" Known letters: {', '.join(letter_info)}"
    
    # Try multiple prompting strategies
    strategies = [
        # Strategy 1: Multiple candidates
        f"""Solve this crossword clue and provide 3 possible answers.

Clue: "{clue_text}"
{constraints}

Consider: definitions, wordplay, abbreviations, slang, puns, anagrams.
Provide each answer on a separate line, using only uppercase letters A-Z.""",
        
        # Strategy 2: Step-by-step reasoning
        f"""Solve this crossword clue step by step.

Clue: "{clue_text}"
{constraints}

1. What type of clue is this? (definition, wordplay, abbreviation, etc.)
2. What are some possible meanings?
3. What words fit the length and letter constraints?

Final answer (uppercase letters only):""",
        
        # Strategy 3: Direct approach
        f"""Crossword clue: "{clue_text}"
{constraints}

Answer (exactly {length} uppercase letters):"""
    ]
    
    for strategy in strategies:
        try:
            response = execute_llm(strategy)
            # Try to extract valid answers
            answers = []
            for line in response.strip().split('\n'):
                candidate = line.strip().upper()
                candidate = ''.join(c for c in candidate if c.isalpha())
                if len(candidate) == length:
                    # Check letter constraints
                    if intersecting_letters:
                        valid = True
                        for pos, letter in intersecting_letters.items():
                            if pos < len(candidate) and candidate[pos] != letter:
                                valid = False
                                break
                        if valid:
                            answers.append(candidate)
                    else:
                        answers.append(candidate)
            
            if answers:
                return answers[0]  # Return first valid answer
                
        except Exception as e:
            logging.error(f"Error with strategy for clue '{clue_text}': {e}")
            continue
    
    return None

def solve_crossword_advanced(grid, across_clues, down_clues):
    """Advanced crossword solver with better intersection handling"""
    
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0
    
    # Find clue positions and lengths
    across_info = {}  # clue_num -> (row, col, length)
    down_info = {}    # clue_num -> (row, col, length)
    current_num = 1
    
    for row in range(height):
        for col in range(width):
            if grid[row][col] == '.':
                continue
            
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
                if starts_across:
                    length = get_word_length(grid, row, col, 'across')
                    across_info[current_num] = (row, col, length)
                if starts_down:
                    length = get_word_length(grid, row, col, 'down')
                    down_info[current_num] = (row, col, length)
                current_num += 1
    
    # Initialize grid
    filled_grid = [row[:] for row in grid]
    for row in range(height):
        for col in range(width):
            if filled_grid[row][col] == '-':
                filled_grid[row][col] = ' '
    
    solved_across = {}
    solved_down = {}
    
    # Multiple solving passes
    for iteration in range(8):  # More iterations
        logging.info(f"Iteration {iteration + 1}")
        prev_count = len(solved_across) + len(solved_down)
        
        # Solve across clues
        for clue_num, clue_text in across_clues.items():
            if clue_num in across_info and clue_num not in solved_across:
                row, col, length = across_info[clue_num]
                
                # Get intersecting letters
                intersecting_letters = {}
                for i in range(length):
                    if col + i < width and filled_grid[row][col + i] != ' ':
                        intersecting_letters[i] = filled_grid[row][col + i]
                
                answer = solve_clue_with_context(clue_text, length, intersecting_letters)
                if answer:
                    # Validate answer doesn't conflict
                    valid = True
                    for i, letter in enumerate(answer):
                        if col + i < width:
                            existing = filled_grid[row][col + i]
                            if existing != ' ' and existing != letter:
                                valid = False
                                break
                    
                    if valid:
                        solved_across[clue_num] = answer
                        # Fill grid
                        for i, letter in enumerate(answer):
                            if col + i < width:
                                filled_grid[row][col + i] = letter
                        logging.info(f"Solved across {clue_num}: {answer}")
        
        # Solve down clues
        for clue_num, clue_text in down_clues.items():
            if clue_num in down_info and clue_num not in solved_down:
                row, col, length = down_info[clue_num]
                
                # Get intersecting letters
                intersecting_letters = {}
                for i in range(length):
                    if row + i < height and filled_grid[row + i][col] != ' ':
                        intersecting_letters[i] = filled_grid[row + i][col]
                
                answer = solve_clue_with_context(clue_text, length, intersecting_letters)
                if answer:
                    # Validate answer doesn't conflict
                    valid = True
                    for i, letter in enumerate(answer):
                        if row + i < height:
                            existing = filled_grid[row + i][col]
                            if existing != ' ' and existing != letter:
                                valid = False
                                break
                    
                    if valid:
                        solved_down[clue_num] = answer
                        # Fill grid
                        for i, letter in enumerate(answer):
                            if row + i < height:
                                filled_grid[row + i][col] = letter
                        logging.info(f"Solved down {clue_num}: {answer}")
        
        # Check progress
        current_count = len(solved_across) + len(solved_down)
        if current_count == prev_count:
            logging.info(f"No progress in iteration {iteration + 1}, stopping")
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
        logging.info("Starting advanced crossword solver")
        grid, across_clues, down_clues = parse_input(input_string)
        logging.info(f"Grid: {len(grid)}x{len(grid[0]) if grid else 0}")
        logging.info(f"Clues: {len(across_clues)} across, {len(down_clues)} down")
        
        filled_grid, solved_across, solved_down = solve_crossword_advanced(grid, across_clues, down_clues)
        logging.info(f"Final: {len(solved_across)} across, {len(solved_down)} down")
        
        result = format_output(filled_grid, solved_across, solved_down)
        return result
        
    except Exception as e:
        logging.error(f"Error in process_input: {e}")
        return ""