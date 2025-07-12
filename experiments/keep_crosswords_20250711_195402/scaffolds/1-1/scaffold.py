import logging
import re
from llm_executor import execute_llm
import random

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

def solve_clue_multiple_attempts(clue_text, length, intersecting_letters=None, max_attempts=3):
    """Solve a clue with multiple attempts and different prompting strategies"""
    
    # Build context
    context = f"The answer has exactly {length} letters."
    if intersecting_letters:
        letter_info = []
        for pos, letter in intersecting_letters.items():
            letter_info.append(f"position {pos+1}: {letter}")
        if letter_info:
            context += f" Known letters: {', '.join(letter_info)}"
    
    # Try different prompting strategies
    strategies = [
        # Strategy 1: Direct approach with examples
        f"""You are a crossword puzzle expert. Solve this clue. {context}

Clue: {clue_text}

Think about:
- Wordplay and puns
- Abbreviations (e.g., "doctor" might be "DR")
- Double meanings
- Anagrams
- Common crossword answers

Respond with ONLY the answer in uppercase letters, no explanation.""",
        
        # Strategy 2: Step-by-step reasoning
        f"""Solve this crossword clue step by step. {context}

Clue: {clue_text}

1. First, identify the type of clue (definition, wordplay, abbreviation, etc.)
2. Consider all possible meanings
3. Think about common crossword conventions
4. Give your final answer

Respond with ONLY the final answer in uppercase letters.""",
        
        # Strategy 3: Pattern matching
        f"""This is a crossword clue. {context}

Clue: {clue_text}

Think about what word fits this pattern and meaning. Consider:
- Is this a straightforward definition?
- Could this be slang or an abbreviation?
- Are there any puns or wordplay?
- What are common crossword answers for this type of clue?

Answer with ONLY the word in uppercase letters."""
    ]
    
    candidates = []
    
    for attempt in range(max_attempts):
        try:
            strategy = strategies[attempt % len(strategies)]
            response = execute_llm(strategy)
            
            # Clean up response
            answer = response.strip().upper()
            # Remove any non-letter characters and explanations
            lines = answer.split('\n')
            for line in lines:
                clean_line = ''.join(c for c in line if c.isalpha())
                if len(clean_line) == length:
                    candidates.append(clean_line)
                    break
            
            # Also try the full response cleaned up
            full_clean = ''.join(c for c in answer if c.isalpha())
            if len(full_clean) == length:
                candidates.append(full_clean)
                
        except Exception as e:
            logging.error(f"Error in attempt {attempt+1} for clue '{clue_text}': {e}")
    
    # Return the most frequent candidate, or first valid one
    if candidates:
        from collections import Counter
        counter = Counter(candidates)
        return counter.most_common(1)[0][0]
    
    return None

def solve_crossword_advanced(grid, across_clues, down_clues, max_iterations=5):
    """Advanced crossword solver with multiple iterations and constraint propagation"""
    
    # Find clue positions and lengths
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0
    
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
    
    # Initialize grid with blanks
    filled_grid = [row[:] for row in grid]
    for row in range(height):
        for col in range(width):
            if filled_grid[row][col] == '-':
                filled_grid[row][col] = ' '
    
    # Track solved clues
    solved_across = {}
    solved_down = {}
    
    # Iterative solving
    for iteration in range(max_iterations):
        logging.info(f"Starting iteration {iteration + 1}")
        progress_made = False
        
        # Try to solve remaining across clues
        for clue_num, clue_text in across_clues.items():
            if clue_num in solved_across or clue_num not in across_info:
                continue
                
            row, col, length = across_info[clue_num]
            
            # Get intersecting letters
            intersecting_letters = {}
            for i in range(length):
                if col + i < width and filled_grid[row][col + i] not in [' ', '-']:
                    intersecting_letters[i] = filled_grid[row][col + i]
            
            # Try to solve the clue
            answer = solve_clue_multiple_attempts(clue_text, length, intersecting_letters)
            
            if answer:
                # Validate against existing letters
                valid = True
                for i, letter in enumerate(answer):
                    if col + i < width:
                        existing = filled_grid[row][col + i]
                        if existing not in [' ', '-'] and existing != letter:
                            valid = False
                            break
                
                if valid:
                    solved_across[clue_num] = answer
                    # Fill in the grid
                    for i, letter in enumerate(answer):
                        if col + i < width:
                            filled_grid[row][col + i] = letter
                    progress_made = True
                    logging.info(f"Solved across {clue_num}: {answer}")
        
        # Try to solve remaining down clues
        for clue_num, clue_text in down_clues.items():
            if clue_num in solved_down or clue_num not in down_info:
                continue
                
            row, col, length = down_info[clue_num]
            
            # Get intersecting letters
            intersecting_letters = {}
            for i in range(length):
                if row + i < height and filled_grid[row + i][col] not in [' ', '-']:
                    intersecting_letters[i] = filled_grid[row + i][col]
            
            # Try to solve the clue
            answer = solve_clue_multiple_attempts(clue_text, length, intersecting_letters)
            
            if answer:
                # Validate against existing letters
                valid = True
                for i, letter in enumerate(answer):
                    if row + i < height:
                        existing = filled_grid[row + i][col]
                        if existing not in [' ', '-'] and existing != letter:
                            valid = False
                            break
                
                if valid:
                    solved_down[clue_num] = answer
                    # Fill in the grid
                    for i, letter in enumerate(answer):
                        if row + i < height:
                            filled_grid[row + i][col] = letter
                    progress_made = True
                    logging.info(f"Solved down {clue_num}: {answer}")
        
        if not progress_made:
            logging.info(f"No progress in iteration {iteration + 1}, stopping")
            break
    
    return filled_grid, solved_across, solved_down

def format_output(filled_grid, solved_across, solved_down):
    """Format the output as expected"""
    result = []
    
    # Add grid
    for row in filled_grid:
        result.append(' '.join(row))
    
    result.append('')  # Empty line
    
    # Add across clues
    result.append('Across:')
    for clue_num in sorted(solved_across.keys()):
        result.append(f'  {clue_num}. {solved_across[clue_num]}')
    
    result.append('')  # Empty line
    
    # Add down clues
    result.append('Down:')
    for clue_num in sorted(solved_down.keys()):
        result.append(f'  {clue_num}. {solved_down[clue_num]}')
    
    return '\n'.join(result)

def process_input(input_string: str) -> str:
    try:
        logging.info("Starting advanced crossword puzzle solution")
        grid, across_clues, down_clues = parse_input(input_string)
        logging.info(f"Parsed grid: {len(grid)}x{len(grid[0]) if grid else 0}")
        logging.info(f"Across clues: {len(across_clues)}, Down clues: {len(down_clues)}")
        
        filled_grid, solved_across, solved_down = solve_crossword_advanced(
            grid, across_clues, down_clues
        )
        logging.info(f"Solved {len(solved_across)} across clues and {len(solved_down)} down clues")
        
        result = format_output(filled_grid, solved_across, solved_down)
        return result
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return ""