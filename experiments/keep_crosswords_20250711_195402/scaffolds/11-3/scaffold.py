import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    try:
        # Parse input
        lines = input_string.strip().split('\n')
        
        # Find where grid ends and clues begin
        grid_lines = []
        clue_start = 0
        for i, line in enumerate(lines):
            if line.strip().startswith('Across:'):
                clue_start = i
                break
            if line.strip():
                grid_lines.append(line.strip())
        
        # Parse grid
        grid = []
        for line in grid_lines:
            grid.append(line.split())
        
        height = len(grid)
        width = len(grid[0]) if height > 0 else 0
        
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
        
        logging.info(f"Parsed {len(across_clues)} across clues and {len(down_clues)} down clues")
        logging.info(f"Grid size: {height}x{width}")
        
        # Solve the crossword
        solution = solve_crossword_iterative(grid, across_clues, down_clues)
        
        return solution
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return ""

def solve_crossword_iterative(grid, across_clues, down_clues):
    """Solve the crossword using an iterative approach with cross-checking"""
    
    # Get clue positions and lengths
    clue_positions = find_clue_positions(grid)
    
    # Initialize solution grid
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0
    solution = [['' for _ in range(width)] for _ in range(height)]
    
    # Copy black squares
    for row in range(height):
        for col in range(width):
            if grid[row][col] == '.':
                solution[row][col] = '.'
    
    # Track solved answers
    across_answers = {}
    down_answers = {}
    
    # Iteratively solve clues, starting with easier ones
    max_iterations = 8
    for iteration in range(max_iterations):
        logging.info(f"Iteration {iteration + 1}")
        made_progress = False
        
        # Sort clues by length (shorter first) and how many letters are already filled
        across_candidates = []
        for clue_num, clue_text in across_clues.items():
            if clue_num not in across_answers and clue_num in clue_positions:
                pos = clue_positions[clue_num]
                length = pos.get('across_length', 0)
                if length > 0:
                    pattern = get_across_pattern(solution, pos['row'], pos['col'], length)
                    filled_count = sum(1 for c in pattern if c != '_')
                    across_candidates.append((clue_num, clue_text, length, filled_count, pattern))
        
        # Sort by filled count (descending) then by length (ascending)
        across_candidates.sort(key=lambda x: (-x[3], x[2]))
        
        # Try to solve across clues
        for clue_num, clue_text, length, filled_count, pattern in across_candidates:
            answer = solve_clue_with_pattern(clue_text, length, pattern, clue_num, 'across')
            if answer and is_valid_placement(solution, clue_positions[clue_num], answer, 'across'):
                across_answers[clue_num] = answer
                place_across_answer(solution, clue_positions[clue_num]['row'], clue_positions[clue_num]['col'], answer)
                logging.info(f"Solved across {clue_num}: {answer} (pattern: {pattern})")
                made_progress = True
        
        # Sort down clues similarly
        down_candidates = []
        for clue_num, clue_text in down_clues.items():
            if clue_num not in down_answers and clue_num in clue_positions:
                pos = clue_positions[clue_num]
                length = pos.get('down_length', 0)
                if length > 0:
                    pattern = get_down_pattern(solution, pos['row'], pos['col'], length)
                    filled_count = sum(1 for c in pattern if c != '_')
                    down_candidates.append((clue_num, clue_text, length, filled_count, pattern))
        
        down_candidates.sort(key=lambda x: (-x[3], x[2]))
        
        # Try to solve down clues
        for clue_num, clue_text, length, filled_count, pattern in down_candidates:
            answer = solve_clue_with_pattern(clue_text, length, pattern, clue_num, 'down')
            if answer and is_valid_placement(solution, clue_positions[clue_num], answer, 'down'):
                down_answers[clue_num] = answer
                place_down_answer(solution, clue_positions[clue_num]['row'], clue_positions[clue_num]['col'], answer)
                logging.info(f"Solved down {clue_num}: {answer} (pattern: {pattern})")
                made_progress = True
        
        if not made_progress:
            logging.info("No progress made in this iteration")
            break
    
    # Fill any remaining empty squares with 'X'
    for row in range(height):
        for col in range(width):
            if solution[row][col] == '':
                solution[row][col] = 'X'
    
    # Format the output
    return format_solution(solution, across_answers, down_answers)

def get_across_pattern(solution, row, col, length):
    """Get the current pattern for an across clue"""
    pattern = []
    for i in range(length):
        if col + i < len(solution[0]):
            cell = solution[row][col + i]
            if cell == '' or cell == '.':
                pattern.append('_')
            else:
                pattern.append(cell)
        else:
            pattern.append('_')
    return ''.join(pattern)

def get_down_pattern(solution, row, col, length):
    """Get the current pattern for a down clue"""
    pattern = []
    for i in range(length):
        if row + i < len(solution):
            cell = solution[row + i][col]
            if cell == '' or cell == '.':
                pattern.append('_')
            else:
                pattern.append(cell)
        else:
            pattern.append('_')
    return ''.join(pattern)

def is_valid_placement(solution, position, answer, direction):
    """Check if placing an answer would create conflicts"""
    row, col = position['row'], position['col']
    
    if direction == 'across':
        for i, letter in enumerate(answer):
            if col + i < len(solution[0]):
                current = solution[row][col + i]
                if current != '' and current != '.' and current != letter:
                    return False
    else:  # down
        for i, letter in enumerate(answer):
            if row + i < len(solution):
                current = solution[row + i][col]
                if current != '' and current != '.' and current != letter:
                    return False
    
    return True

def place_across_answer(solution, row, col, answer):
    """Place an across answer in the solution grid"""
    for i, letter in enumerate(answer):
        if col + i < len(solution[0]):
            solution[row][col + i] = letter

def place_down_answer(solution, row, col, answer):
    """Place a down answer in the solution grid"""
    for i, letter in enumerate(answer):
        if row + i < len(solution):
            solution[row + i][col] = letter

def solve_clue_with_pattern(clue_text, length, pattern, clue_num, direction):
    """Solve a clue with a given pattern constraint"""
    try:
        # Try multiple approaches to get the best answer
        candidates = []
        
        # Approach 1: Use pattern if available
        if '_' in pattern:
            prompt1 = f"""Solve this crossword clue. The answer must be exactly {length} letters long and match the pattern shown.

Clue: {clue_text}
Length: {length} letters
Pattern: {pattern} (where _ means unknown letter)

Provide exactly one answer in uppercase letters with no spaces or punctuation:"""
            
            try:
                response1 = execute_llm(prompt1)
                candidate1 = extract_answer(response1, length, pattern)
                if candidate1:
                    candidates.append(candidate1)
            except:
                pass
        
        # Approach 2: Ask for multiple candidates
        prompt2 = f"""Solve this crossword clue. The answer must be exactly {length} letters long.

Clue: {clue_text}
Length: {length} letters

Provide your best 3 possible answers, one per line, in uppercase letters with no spaces or punctuation:"""
        
        try:
            response2 = execute_llm(prompt2)
            for line in response2.strip().split('\n'):
                candidate = extract_answer(line, length, pattern)
                if candidate and candidate not in candidates:
                    candidates.append(candidate)
        except:
            pass
        
        # Return the first valid candidate
        if candidates:
            logging.info(f"Candidates for {clue_num}: {candidates}")
            return candidates[0]
        
        logging.warning(f"Could not solve clue {clue_num} ({direction}): {clue_text} with pattern {pattern}")
        return None
        
    except Exception as e:
        logging.error(f"Error solving clue {clue_num}: {e}")
        return None

def extract_answer(response, length, pattern):
    """Extract a valid answer from LLM response"""
    lines = response.strip().split('\n')
    for line in lines:
        line = line.strip().upper()
        # Remove any non-alphabetic characters
        clean_line = ''.join(c for c in line if c.isalpha())
        if len(clean_line) == length and matches_pattern(clean_line, pattern):
            return clean_line
    return None

def matches_pattern(answer, pattern):
    """Check if an answer matches a given pattern"""
    if len(answer) != len(pattern):
        return False
    
    for i, (a, p) in enumerate(zip(answer, pattern)):
        if p != '_' and a != p:
            return False
    
    return True

def find_clue_positions(grid):
    """Find the starting positions and lengths of all clues"""
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0
    
    positions = {}
    current_num = 1
    
    for row in range(height):
        for col in range(width):
            if grid[row][col] == '.':
                continue
            
            # Check if this position starts an across word
            starts_across = (
                (col == 0 or grid[row][col - 1] == '.') and
                col + 1 < width and grid[row][col + 1] != '.'
            )
            
            # Check if this position starts a down word
            starts_down = (
                (row == 0 or grid[row - 1][col] == '.') and
                row + 1 < height and grid[row + 1][col] != '.'
            )
            
            if starts_across or starts_down:
                positions[current_num] = {
                    'row': row,
                    'col': col,
                    'across_length': 0,
                    'down_length': 0
                }
                
                if starts_across:
                    # Find length of across word
                    length = 0
                    for c in range(col, width):
                        if grid[row][c] == '.':
                            break
                        length += 1
                    positions[current_num]['across_length'] = length
                
                if starts_down:
                    # Find length of down word
                    length = 0
                    for r in range(row, height):
                        if grid[r][col] == '.':
                            break
                        length += 1
                    positions[current_num]['down_length'] = length
                
                current_num += 1
    
    return positions

def format_solution(solution_grid, across_answers, down_answers):
    """Format the solution in the expected output format"""
    
    # Format grid
    grid_text = '\n'.join(' '.join(row) for row in solution_grid)
    
    # Format across answers
    across_text = "Across:\n"
    for clue_num in sorted(across_answers.keys()):
        across_text += f"  {clue_num}. {across_answers[clue_num]}\n"
    
    # Format down answers
    down_text = "Down:\n"
    for clue_num in sorted(down_answers.keys()):
        down_text += f"  {clue_num}. {down_answers[clue_num]}\n"
    
    return f"{grid_text}\n\n{across_text}\n{down_text}"