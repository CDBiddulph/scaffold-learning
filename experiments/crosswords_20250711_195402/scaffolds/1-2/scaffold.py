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

def find_clue_positions(grid):
    """Find the starting positions of all clues in the grid"""
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0
    
    positions = {}  # clue_num -> [(row, col, direction, length)]
    current_num = 1
    
    for row in range(height):
        for col in range(width):
            # Skip black squares
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
                if current_num not in positions:
                    positions[current_num] = []
                    
                if starts_across:
                    # Calculate length
                    length = 0
                    for c in range(col, width):
                        if grid[row][c] == '.':
                            break
                        length += 1
                    positions[current_num].append((row, col, 'across', length))
                    
                if starts_down:
                    # Calculate length
                    length = 0
                    for r in range(row, height):
                        if grid[r][col] == '.':
                            break
                        length += 1
                    positions[current_num].append((row, col, 'down', length))
                    
                current_num += 1
    
    return positions

def solve_clue_with_llm(clue_text, length, constraints=None, attempts=3):
    """Solve a clue with multiple attempts for better accuracy"""
    
    context = f"Length: {length} letters"
    if constraints:
        constraint_info = []
        for pos, letter in constraints.items():
            constraint_info.append(f"position {pos+1}: '{letter}'")
        if constraint_info:
            context += f". Known letters: {', '.join(constraint_info)}"
    
    prompt = f"""Solve this crossword clue carefully. {context}

Clue: "{clue_text}"

Important crossword solving tips:
- Look for wordplay, anagrams, abbreviations, and double meanings
- Consider common crossword answers
- The answer must be exactly {length} letters
- Think step by step about what the clue could mean

Respond with ONLY the answer in uppercase letters, nothing else."""
    
    best_answer = None
    
    for attempt in range(attempts):
        try:
            response = execute_llm(prompt)
            answer = response.strip().upper()
            # Remove any non-letter characters
            answer = ''.join(c for c in answer if c.isalpha())
            
            if len(answer) == length:
                # Check if it fits constraints
                if constraints:
                    fits = True
                    for pos, letter in constraints.items():
                        if pos < len(answer) and answer[pos] != letter:
                            fits = False
                            break
                    if fits:
                        return answer
                    else:
                        # Try a more specific prompt
                        if attempt < attempts - 1:
                            pattern = ['_'] * length
                            for pos, letter in constraints.items():
                                if pos < length:
                                    pattern[pos] = letter
                            pattern_str = ''.join(pattern)
                            prompt = f"""Solve this crossword clue. The answer fits the pattern: {pattern_str}

Clue: "{clue_text}"

Each '_' represents an unknown letter. The answer must fit this exact pattern.
Respond with ONLY the answer in uppercase letters."""
                            continue
                else:
                    return answer
                    
            # If wrong length, try again with emphasis
            if attempt < attempts - 1:
                prompt = f"""Solve this crossword clue. The answer must be EXACTLY {length} letters long.

Clue: "{clue_text}"

Think carefully about the length requirement. Count the letters in your answer.
Respond with ONLY the answer in uppercase letters."""
        
        except Exception as e:
            logging.error(f"Error solving clue '{clue_text}': {e}")
            continue
    
    return best_answer

def solve_crossword_iteratively(grid, across_clues, down_clues, max_iterations=5):
    """Solve the crossword puzzle iteratively with constraint propagation"""
    
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0
    
    # Find all clue positions
    positions = find_clue_positions(grid)
    
    # Initialize grid with blanks
    filled_grid = [row[:] for row in grid]
    for row in range(height):
        for col in range(width):
            if filled_grid[row][col] == '-':
                filled_grid[row][col] = ' '
    
    # Track solved clues
    solved_across = {}
    solved_down = {}
    
    # Map clue numbers to their positions
    across_positions = {}
    down_positions = {}
    
    for clue_num, pos_list in positions.items():
        for row, col, direction, length in pos_list:
            if direction == 'across':
                across_positions[clue_num] = (row, col, length)
            else:
                down_positions[clue_num] = (row, col, length)
    
    # Iterative solving
    for iteration in range(max_iterations):
        logging.info(f"Iteration {iteration + 1}")
        made_progress = False
        
        # Solve across clues
        for clue_num, clue_text in across_clues.items():
            if clue_num in solved_across or clue_num not in across_positions:
                continue
                
            row, col, length = across_positions[clue_num]
            
            # Get constraints from intersecting letters
            constraints = {}
            for i in range(length):
                if col + i < width and filled_grid[row][col + i] != ' ':
                    constraints[i] = filled_grid[row][col + i]
            
            answer = solve_clue_with_llm(clue_text, length, constraints)
            if answer:
                solved_across[clue_num] = answer
                # Fill in the grid
                for i, letter in enumerate(answer):
                    if col + i < width:
                        filled_grid[row][col + i] = letter
                made_progress = True
                logging.info(f"Solved {clue_num} across: {answer}")
        
        # Solve down clues
        for clue_num, clue_text in down_clues.items():
            if clue_num in solved_down or clue_num not in down_positions:
                continue
                
            row, col, length = down_positions[clue_num]
            
            # Get constraints from intersecting letters
            constraints = {}
            for i in range(length):
                if row + i < height and filled_grid[row + i][col] != ' ':
                    constraints[i] = filled_grid[row + i][col]
            
            answer = solve_clue_with_llm(clue_text, length, constraints)
            if answer:
                solved_down[clue_num] = answer
                # Fill in the grid
                for i, letter in enumerate(answer):
                    if row + i < height:
                        filled_grid[row + i][col] = letter
                made_progress = True
                logging.info(f"Solved {clue_num} down: {answer}")
        
        if not made_progress:
            break
    
    logging.info(f"Solved {len(solved_across)} across and {len(solved_down)} down clues")
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
        logging.info("Starting crossword puzzle solution")
        grid, across_clues, down_clues = parse_input(input_string)
        logging.info(f"Parsed grid: {len(grid)}x{len(grid[0]) if grid else 0}")
        logging.info(f"Across clues: {len(across_clues)}, Down clues: {len(down_clues)}")
        
        filled_grid, solved_across, solved_down = solve_crossword_iteratively(
            grid, across_clues, down_clues
        )
        
        result = format_output(filled_grid, solved_across, solved_down)
        return result
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return ""