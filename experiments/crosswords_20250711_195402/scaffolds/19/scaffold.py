import logging
import re
from llm_executor import execute_llm

def parse_input(input_string):
    """Parse the input to extract grid structure and clues"""
    lines = input_string.strip().split('\n')
    
    # Find where clues start
    grid_lines = []
    clue_start = len(lines)
    
    for i, line in enumerate(lines):
        if line.strip().startswith('Across:') or line.strip().startswith('Down:'):
            clue_start = i
            break
        if line.strip():
            grid_lines.append(line.strip())
    
    # Parse grid
    grid = []
    for line in grid_lines:
        grid.append(line.split())
    
    # Parse clues
    across_clues = {}
    down_clues = {}
    current_section = None
    
    for i in range(clue_start, len(lines)):
        line = lines[i].strip()
        if line.startswith('Across:'):
            current_section = 'across'
        elif line.startswith('Down:'):
            current_section = 'down'
        elif line and current_section:
            match = re.match(r'\s*(\d+)\.\s*(.+)', line)
            if match:
                clue_num = int(match.group(1))
                clue_text = match.group(2).strip()
                if current_section == 'across':
                    across_clues[clue_num] = clue_text
                else:
                    down_clues[clue_num] = clue_text
    
    return grid, across_clues, down_clues

def solve_crossword_with_llm(input_string, attempt=1):
    """Use LLM to solve the entire crossword puzzle"""
    
    if attempt == 1:
        prompt = f"""
Solve this crossword puzzle completely. I need you to:

1. Analyze each clue carefully
2. Find the correct answers that fit the grid constraints
3. Make sure intersecting words share the same letters

{input_string}

Return your answer in exactly this format:
1. First, the solved grid with letters replacing dashes, dots staying as dots, each row on a separate line
2. Then a blank line
3. Then "Across:" followed by the across answers in the format "  1. ANSWER"
4. Then a blank line  
5. Then "Down:" followed by the down answers in the format "  1. ANSWER"

Make sure every dash is replaced with a letter and all answers are correct.
"""
    elif attempt == 2:
        prompt = f"""
This is a crossword puzzle that needs to be solved completely and accurately.

{input_string}

Please solve it step by step:
1. Look at each clue and determine the most likely answer
2. Consider the word lengths based on the grid structure
3. Make sure intersecting answers share correct letters
4. Double-check your work

Format your response as:
- Solved grid (letters replace dashes, dots stay as dots)
- Blank line
- "Across:" section with numbered answers
- Blank line
- "Down:" section with numbered answers
"""
    else:
        prompt = f"""
Solve this crossword puzzle. Focus on accuracy and consistency.

{input_string}

Output format:
[solved grid]

Across:
  1. ANSWER
  2. ANSWER
  ...

Down:
  1. ANSWER
  2. ANSWER
  ...
"""
    
    response = execute_llm(prompt)
    return response.strip()

def validate_solution(solution, grid, across_clues, down_clues):
    """Basic validation of the solution format"""
    try:
        # Check if solution has the basic structure
        if "Across:" not in solution or "Down:" not in solution:
            return False
        
        # Split into pieces
        pieces = solution.split('\n\n')
        if len(pieces) < 3:
            return False
        
        # Check if first piece looks like a grid
        grid_piece = pieces[0]
        grid_lines = grid_piece.split('\n')
        
        if len(grid_lines) != len(grid):
            return False
        
        # Check if we have roughly the right number of clues
        across_count = len([line for line in solution.split('\n') if re.match(r'\s*\d+\.', line) and 'Across:' in solution.split(line)[0]])
        down_count = len([line for line in solution.split('\n') if re.match(r'\s*\d+\.', line) and 'Down:' in solution.split(line)[0]])
        
        return True
        
    except Exception as e:
        logging.error(f"Validation error: {e}")
        return False

def process_input(input_string: str) -> str:
    try:
        logging.info("Starting crossword puzzle solving")
        
        # Parse input
        grid, across_clues, down_clues = parse_input(input_string)
        logging.info(f"Parsed grid size: {len(grid)}x{len(grid[0]) if grid else 0}")
        logging.info(f"Found {len(across_clues)} across clues and {len(down_clues)} down clues")
        
        # Try multiple attempts to solve
        for attempt in range(1, 4):
            logging.info(f"Attempt {attempt} to solve crossword")
            
            try:
                solution = solve_crossword_with_llm(input_string, attempt)
                
                # Basic validation
                if validate_solution(solution, grid, across_clues, down_clues):
                    logging.info(f"Successfully solved crossword on attempt {attempt}")
                    return solution
                else:
                    logging.warning(f"Attempt {attempt} failed validation")
                    
            except Exception as e:
                logging.error(f"Attempt {attempt} failed with error: {e}")
                continue
        
        # If all attempts fail, try one more time with a simpler approach
        logging.info("Trying fallback approach")
        try:
            prompt = f"""
Solve this crossword puzzle and return the solution in the same format as the input but with dashes replaced by letters.

{input_string}

Just give me the complete solution with the grid filled in and the answers listed.
"""
            
            response = execute_llm(prompt)
            return response.strip()
            
        except Exception as e:
            logging.error(f"Fallback approach failed: {e}")
            return ""
        
    except Exception as e:
        logging.error(f"Critical error in process_input: {e}")
        return ""