import logging
import re
from llm_executor import execute_llm

def parse_crossword_input(input_string):
    """Parse the input crossword puzzle into grid and clues"""
    lines = input_string.strip().split('\n')
    
    # Parse grid
    grid = []
    line_idx = 0
    while line_idx < len(lines):
        line = lines[line_idx].strip()
        if not line or line.startswith('Across:') or line.startswith('Down:'):
            break
        grid.append(line.split())
        line_idx += 1
    
    # Parse clues
    across_clues = {}
    down_clues = {}
    
    current_section = None
    for i in range(line_idx, len(lines)):
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

def find_clue_position(clue_num, grid, direction):
    """Find the starting position of a clue in the grid based on crossword numbering"""
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0
    current_num = 1

    for row in range(height):
        for col in range(width):
            if grid[row][col] == ".":
                continue

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
                if current_num == clue_num:
                    return (row, col)
                current_num += 1

    return None

def get_clue_length(clue_num, grid, direction):
    """Get the length of a clue based on grid structure"""
    pos = find_clue_position(clue_num, grid, direction)
    if pos is None:
        return None
    
    row, col = pos
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0
    
    if direction == 'across':
        length = 0
        for c in range(col, width):
            if grid[row][c] == ".":
                break
            length += 1
        return length
    else:  # down
        length = 0
        for r in range(row, height):
            if grid[r][col] == ".":
                break
            length += 1
        return length

def solve_clue_with_pattern(clue_text, length=None, pattern=None, retries=2):
    """Solve a crossword clue with optional pattern constraint"""
    
    # Create specialized prompts based on clue type
    if "inits." in clue_text.lower() or "abbr." in clue_text.lower():
        base_prompt = f"This crossword clue asks for an abbreviation or initials. Give me only the uppercase letters with no periods or spaces.\n\nClue: {clue_text}"
    elif any(word in clue_text.lower() for word in ["prefix", "suffix", "beginning", "ending"]):
        base_prompt = f"This crossword clue asks for a word part (prefix/suffix). Give me only the letters.\n\nClue: {clue_text}"
    else:
        base_prompt = f"Solve this crossword clue. Think about common crossword answers and wordplay. Give me only the answer in uppercase letters with no spaces or punctuation.\n\nClue: {clue_text}"
    
    if length:
        base_prompt += f"\nLength: {length} letters"
    
    if pattern:
        base_prompt += f"\nPattern: {pattern} (where . means any letter)"
        base_prompt += f"\nThe answer must match this exact pattern."
    
    for attempt in range(retries + 1):
        try:
            response = execute_llm(base_prompt)
            answer = ''.join(c for c in response.strip().upper() if c.isalpha())
            
            # Strict length checking
            if length and len(answer) != length:
                logging.warning(f"Answer '{answer}' has wrong length {len(answer)}, expected {length}")
                if attempt < retries:
                    continue
                else:
                    return ""
            
            # Pattern matching
            if pattern and not matches_pattern(answer, pattern):
                logging.warning(f"Answer '{answer}' doesn't match pattern '{pattern}'")
                if attempt < retries:
                    continue
                else:
                    return ""
            
            if answer:
                return answer
                
        except Exception as e:
            logging.error(f"Error solving clue '{clue_text}' (attempt {attempt + 1}): {e}")
            if attempt < retries:
                continue
    
    return ""

def matches_pattern(answer, pattern):
    """Check if answer matches pattern (. means any letter)"""
    if len(answer) != len(pattern):
        return False
    
    for a, p in zip(answer, pattern):
        if p != '.' and p != a:
            return False
    
    return True

def get_intersections(grid, across_answers, down_answers):
    """Find all intersections between across and down clues"""
    intersections = []
    
    for across_num, across_answer in across_answers.items():
        across_pos = find_clue_position(across_num, grid, 'across')
        if not across_pos:
            continue
        
        across_row, across_col = across_pos
        
        for down_num, down_answer in down_answers.items():
            down_pos = find_clue_position(down_num, grid, 'down')
            if not down_pos:
                continue
            
            down_row, down_col = down_pos
            
            # Check if they intersect
            if (across_row >= down_row and across_row < down_row + len(down_answer) and
                down_col >= across_col and down_col < across_col + len(across_answer)):
                
                across_idx = down_col - across_col
                down_idx = across_row - down_row
                
                if (0 <= across_idx < len(across_answer) and 
                    0 <= down_idx < len(down_answer)):
                    
                    intersections.append({
                        'across_num': across_num,
                        'down_num': down_num,
                        'across_idx': across_idx,
                        'down_idx': down_idx,
                        'across_letter': across_answer[across_idx],
                        'down_letter': down_answer[down_idx],
                        'position': (across_row, down_col)
                    })
    
    return intersections

def solve_crossword_iteratively(grid, across_clues, down_clues, max_iterations=3):
    """Solve crossword with true iterative refinement"""
    across_answers = {}
    down_answers = {}
    
    # Initial pass - solve all clues independently with strict constraints
    logging.info("Starting initial pass...")
    
    for clue_num, clue_text in across_clues.items():
        length = get_clue_length(clue_num, grid, 'across')
        answer = solve_clue_with_pattern(clue_text, length)
        if answer:
            across_answers[clue_num] = answer
            logging.info(f"Across {clue_num}: {answer}")
    
    for clue_num, clue_text in down_clues.items():
        length = get_clue_length(clue_num, grid, 'down')
        answer = solve_clue_with_pattern(clue_text, length)
        if answer:
            down_answers[clue_num] = answer
            logging.info(f"Down {clue_num}: {answer}")
    
    # Iterative refinement to resolve conflicts
    for iteration in range(max_iterations):
        intersections = get_intersections(grid, across_answers, down_answers)
        conflicts = [i for i in intersections if i['across_letter'] != i['down_letter']]
        
        if not conflicts:
            logging.info(f"No conflicts found after {iteration} iterations")
            break
        
        logging.info(f"Iteration {iteration + 1}: Found {len(conflicts)} conflicts")
        
        # Resolve conflicts by re-solving clues with letter constraints
        for conflict in conflicts[:10]:  # Limit to avoid timeout
            logging.info(f"Resolving conflict: Across {conflict['across_num']} vs Down {conflict['down_num']}")
            
            # Try re-solving the across clue with the down letter constraint
            across_length = len(across_answers[conflict['across_num']])
            across_pattern = '.' * across_length
            across_pattern = across_pattern[:conflict['across_idx']] + conflict['down_letter'] + across_pattern[conflict['across_idx']+1:]
            
            new_across = solve_clue_with_pattern(
                across_clues[conflict['across_num']], 
                across_length, 
                across_pattern
            )
            
            if new_across and new_across != across_answers[conflict['across_num']]:
                logging.info(f"Updated Across {conflict['across_num']}: {across_answers[conflict['across_num']]} -> {new_across}")
                across_answers[conflict['across_num']] = new_across
                continue
            
            # Try re-solving the down clue with the across letter constraint
            down_length = len(down_answers[conflict['down_num']])
            down_pattern = '.' * down_length
            down_pattern = down_pattern[:conflict['down_idx']] + conflict['across_letter'] + down_pattern[conflict['down_idx']+1:]
            
            new_down = solve_clue_with_pattern(
                down_clues[conflict['down_num']], 
                down_length, 
                down_pattern
            )
            
            if new_down and new_down != down_answers[conflict['down_num']]:
                logging.info(f"Updated Down {conflict['down_num']}: {down_answers[conflict['down_num']]} -> {new_down}")
                down_answers[conflict['down_num']] = new_down
    
    return across_answers, down_answers

def build_completed_grid(grid, across_answers, down_answers):
    """Build the completed crossword grid"""
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0
    completed = [row[:] for row in grid]  # Deep copy
    
    # Fill in across answers
    for clue_num, answer in across_answers.items():
        pos = find_clue_position(clue_num, grid, 'across')
        if pos:
            row, col = pos
            for i, letter in enumerate(answer):
                if col + i < width and grid[row][col + i] != ".":
                    completed[row][col + i] = letter
    
    # Fill in down answers (can overwrite across answers at intersections)
    for clue_num, answer in down_answers.items():
        pos = find_clue_position(clue_num, grid, 'down')
        if pos:
            row, col = pos
            for i, letter in enumerate(answer):
                if row + i < height and grid[row + i][col] != ".":
                    completed[row + i][col] = letter
    
    return completed

def process_input(input_string: str) -> str:
    try:
        grid, across_clues, down_clues = parse_crossword_input(input_string)
        logging.info(f"Parsed {len(across_clues)} across clues and {len(down_clues)} down clues")
        
        # Solve the crossword with iterative refinement
        across_answers, down_answers = solve_crossword_iteratively(grid, across_clues, down_clues)
        
        # Build the completed grid
        completed_grid = build_completed_grid(grid, across_answers, down_answers)
        
        # Format output to match expected format exactly
        result = []
        
        # Add completed grid
        for row in completed_grid:
            result.append(' '.join(row))
        
        result.append('')  # Empty line separator
        
        # Add across answers
        if across_answers:
            result.append("Across:")
            for clue_num in sorted(across_answers.keys()):
                result.append(f"  {clue_num}. {across_answers[clue_num]}")
        
        # Add down answers
        if down_answers:
            result.append("\nDown:")
            for clue_num in sorted(down_answers.keys()):
                result.append(f"  {clue_num}. {down_answers[clue_num]}")
        
        final_result = '\n'.join(result)
        logging.info(f"Generated solution with {len(across_answers)} across and {len(down_answers)} down answers")
        return final_result
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return ""