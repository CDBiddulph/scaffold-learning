import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    try:
        # Parse the input to extract grid and clues
        grid, across_clues, down_clues = parse_input(input_string)
        
        # Extract answer lengths and positions from grid
        answer_info = extract_answer_info(grid)
        
        logging.info(f"Found {len(across_clues)} across clues and {len(down_clues)} down clues")
        
        # Initialize solution grid
        solution_grid = [row[:] for row in grid]
        
        # Generate multiple candidates for each clue
        across_candidates = generate_candidates_for_clues(across_clues, answer_info, 'across')
        down_candidates = generate_candidates_for_clues(down_clues, answer_info, 'down')
        
        # Solve using constraint satisfaction with multiple candidates
        solved_across, solved_down = solve_with_multiple_candidates(
            across_candidates, down_candidates, answer_info, solution_grid
        )
        
        # Fill solution grid
        fill_solution_grid(solution_grid, solved_across, solved_down, answer_info)
        
        # Format output
        result = format_output(solution_grid, solved_across, solved_down)
        return result
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "Error: Could not process input"

def parse_input(input_string):
    """Parse input to extract grid and clues"""
    lines = input_string.strip().split('\n')
    
    across_start = None
    down_start = None
    
    for i, line in enumerate(lines):
        if line.strip().startswith("Across:"):
            across_start = i
        elif line.strip().startswith("Down:"):
            down_start = i
    
    if across_start is None or down_start is None:
        raise ValueError("Could not find clues sections")
    
    # Extract grid
    grid_lines = []
    for i in range(across_start):
        line = lines[i].strip()
        if line:
            grid_lines.append(line.split())
    
    # Extract clues
    across_clues = {}
    down_clues = {}
    
    # Parse across clues
    for i in range(across_start + 1, down_start):
        line = lines[i].strip()
        if line:
            match = re.match(r'\s*(\d+)\.\s*(.+)', line)
            if match:
                clue_num = int(match.group(1))
                clue_text = match.group(2).strip()
                across_clues[clue_num] = clue_text
    
    # Parse down clues  
    for i in range(down_start + 1, len(lines)):
        line = lines[i].strip()
        if line:
            match = re.match(r'\s*(\d+)\.\s*(.+)', line)
            if match:
                clue_num = int(match.group(1))
                clue_text = match.group(2).strip()
                down_clues[clue_num] = clue_text
    
    return grid_lines, across_clues, down_clues

def extract_answer_info(grid):
    """Extract answer lengths and positions from grid structure"""
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0
    
    answer_info = {}
    current_num = 1
    
    for row in range(height):
        for col in range(width):
            if grid[row][col] == '.':
                continue
            
            starts_across = (
                (col == 0 or grid[row][col - 1] == '.') and
                col + 1 < width and grid[row][col + 1] != '.'
            )
            starts_down = (
                (row == 0 or grid[row - 1][col] == '.') and
                row + 1 < height and grid[row + 1][col] != '.'
            )
            
            if starts_across or starts_down:
                if starts_across:
                    length = 0
                    for c in range(col, width):
                        if grid[row][c] == '.':
                            break
                        length += 1
                    answer_info[current_num] = answer_info.get(current_num, {})
                    answer_info[current_num]['across'] = {
                        'length': length,
                        'row': row,
                        'col': col,
                        'direction': 'across'
                    }
                
                if starts_down:
                    length = 0
                    for r in range(row, height):
                        if grid[r][col] == '.':
                            break
                        length += 1
                    answer_info[current_num] = answer_info.get(current_num, {})
                    answer_info[current_num]['down'] = {
                        'length': length,
                        'row': row,
                        'col': col,
                        'direction': 'down'
                    }
                
                current_num += 1
    
    return answer_info

def generate_candidates_for_clues(clues, answer_info, direction):
    """Generate multiple candidates for each clue"""
    candidates = {}
    
    for clue_num, clue_text in clues.items():
        if clue_num in answer_info and direction in answer_info[clue_num]:
            length = answer_info[clue_num][direction]['length']
            
            # Generate multiple candidates using different strategies
            candidate_list = []
            
            # Strategy 1: Direct solving with crossword emphasis
            prompt1 = f"""Solve this crossword clue. Pay attention to wordplay, puns, and double meanings.

Clue: {clue_text}
Length: {length} letters

Think about:
- Wordplay and puns (very common in crosswords)
- Multiple meanings of words in the clue
- Abbreviations and shortened forms
- Compound words or phrases (written as one word)
- Consider less obvious meanings

Respond with ONLY the {length}-letter answer in CAPITAL LETTERS:"""
            
            try:
                response1 = execute_llm(prompt1)
                answer1 = clean_answer(response1, length)
                if answer1:
                    candidate_list.append(answer1)
            except:
                pass
            
            # Strategy 2: Generate multiple options
            prompt2 = f"""Generate 3 different possible answers for this crossword clue:

Clue: {clue_text}
Length: {length} letters

Consider wordplay, puns, abbreviations, and less obvious meanings.
Respond with exactly 3 words, each {length} letters, separated by commas:"""
            
            try:
                response2 = execute_llm(prompt2)
                for word in response2.split(','):
                    cleaned = clean_answer(word.strip(), length)
                    if cleaned and cleaned not in candidate_list:
                        candidate_list.append(cleaned)
            except:
                pass
            
            # Strategy 3: Ask for creative/alternative interpretations
            prompt3 = f"""This crossword clue might have a clever or unexpected answer:

Clue: {clue_text}
Length: {length} letters

Think creatively about:
- Less common meanings of words
- Wordplay and letter manipulation
- Cultural references or slang
- Technical terms or proper nouns

What's a creative {length}-letter answer? Respond with ONLY the word:"""
            
            try:
                response3 = execute_llm(prompt3)
                answer3 = clean_answer(response3, length)
                if answer3 and answer3 not in candidate_list:
                    candidate_list.append(answer3)
            except:
                pass
            
            # Ensure we have at least one candidate
            if not candidate_list:
                candidate_list = ['-' * length]  # Fallback
            
            candidates[clue_num] = candidate_list[:5]  # Limit to 5 candidates
            logging.info(f"Generated {len(candidates[clue_num])} candidates for {direction} {clue_num}: {candidates[clue_num]}")
    
    return candidates

def clean_answer(response, expected_length):
    """Clean and validate an answer from the LLM"""
    if not response:
        return None
    
    answer = response.strip().upper()
    answer = answer.strip('"').strip("'")
    
    # Take first word if multiple
    words = answer.split()
    if words:
        answer = words[0]
    
    # Remove non-letter characters
    answer = ''.join(c for c in answer if c.isalpha())
    
    # Check length
    if len(answer) == expected_length:
        return answer
    
    return None

def solve_with_multiple_candidates(across_candidates, down_candidates, answer_info, grid):
    """Solve using constraint satisfaction with multiple candidates"""
    solved_across = {}
    solved_down = {}
    current_grid = [row[:] for row in grid]
    
    # Start with high-confidence short answers
    clue_priority = []
    
    # Add all clues with priority (shorter first, more candidates first)
    for clue_num in across_candidates:
        if clue_num in answer_info and 'across' in answer_info[clue_num]:
            length = answer_info[clue_num]['across']['length']
            candidates = len(across_candidates[clue_num])
            priority = 1000 - length * 10 + candidates  # Prefer short words with many candidates
            clue_priority.append((priority, clue_num, 'across'))
    
    for clue_num in down_candidates:
        if clue_num in answer_info and 'down' in answer_info[clue_num]:
            length = answer_info[clue_num]['down']['length']
            candidates = len(down_candidates[clue_num])
            priority = 1000 - length * 10 + candidates
            clue_priority.append((priority, clue_num, 'down'))
    
    clue_priority.sort(reverse=True)
    
    # Try to solve in priority order
    for _, clue_num, direction in clue_priority:
        if direction == 'across' and clue_num in solved_across:
            continue
        if direction == 'down' and clue_num in solved_down:
            continue
        
        if direction == 'across':
            candidates = across_candidates[clue_num]
            info = answer_info[clue_num]['across']
        else:
            candidates = down_candidates[clue_num]
            info = answer_info[clue_num]['down']
        
        # Get current constraints
        constraints = get_intersection_constraints(
            info['row'], info['col'], info['length'], direction, current_grid
        )
        
        # Try each candidate
        best_candidate = None
        for candidate in candidates:
            if satisfies_constraints(candidate, constraints):
                best_candidate = candidate
                break
        
        if best_candidate:
            if direction == 'across':
                solved_across[clue_num] = best_candidate
            else:
                solved_down[clue_num] = best_candidate
            
            fill_answer_in_grid(current_grid, best_candidate, info)
            logging.info(f"Solved {direction} {clue_num}: {best_candidate}")
    
    return solved_across, solved_down

def get_intersection_constraints(row, col, length, direction, grid):
    """Get constraint letters from intersecting answers"""
    constraints = {}
    
    if direction == 'across':
        for i in range(length):
            c = col + i
            if c < len(grid[0]) and grid[row][c] != '-':
                constraints[i] = grid[row][c].upper()
    else:  # down
        for i in range(length):
            r = row + i
            if r < len(grid) and grid[r][col] != '-':
                constraints[i] = grid[r][col].upper()
    
    return constraints

def satisfies_constraints(answer, constraints):
    """Check if answer satisfies intersection constraints"""
    for pos, expected_letter in constraints.items():
        if pos < len(answer) and answer[pos] != expected_letter:
            return False
    return True

def fill_answer_in_grid(grid, answer, info):
    """Fill an answer into the grid"""
    row, col = info['row'], info['col']
    
    if info['direction'] == 'across':
        for i, letter in enumerate(answer):
            if col + i < len(grid[0]):
                grid[row][col + i] = letter
    else:  # down
        for i, letter in enumerate(answer):
            if row + i < len(grid):
                grid[row + i][col] = letter

def fill_solution_grid(grid, solved_across, solved_down, answer_info):
    """Fill all solved answers into the grid"""
    for clue_num, answer in solved_across.items():
        if clue_num in answer_info and 'across' in answer_info[clue_num]:
            fill_answer_in_grid(grid, answer, answer_info[clue_num]['across'])
    
    for clue_num, answer in solved_down.items():
        if clue_num in answer_info and 'down' in answer_info[clue_num]:
            fill_answer_in_grid(grid, answer, answer_info[clue_num]['down'])

def format_output(grid, solved_across, solved_down):
    """Format output with both grid and clues"""
    result = ""
    
    # Add grid
    for row in grid:
        result += " ".join(row) + "\n"
    
    result += "\n"
    
    # Add across clues
    result += "Across:\n"
    for clue_num in sorted(solved_across.keys()):
        result += f"  {clue_num}. {solved_across[clue_num]}\n"
    
    result += "\n"
    
    # Add down clues
    result += "Down:\n"
    for clue_num in sorted(solved_down.keys()):
        result += f"  {clue_num}. {solved_down[clue_num]}\n"
    
    return result