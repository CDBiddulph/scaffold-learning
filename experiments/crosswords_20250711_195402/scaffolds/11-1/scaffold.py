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
        solution = solve_crossword_with_constraints(grid, across_clues, down_clues)
        
        return solution
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return ""

def solve_crossword_with_constraints(grid, across_clues, down_clues):
    """Solve crossword using constraint satisfaction with multiple candidates"""
    
    # Get clue positions and lengths
    clue_positions = find_clue_positions(grid)
    
    # Generate multiple candidates for each clue
    across_candidates = {}
    down_candidates = {}
    
    # Generate candidates for shorter clues first (they're often easier)
    sorted_across = sorted(across_clues.items(), key=lambda x: clue_positions.get(x[0], {}).get('across_length', 0))
    sorted_down = sorted(down_clues.items(), key=lambda x: clue_positions.get(x[0], {}).get('down_length', 0))
    
    # Generate candidates for across clues
    for clue_num, clue_text in sorted_across:
        if clue_num in clue_positions:
            length = clue_positions[clue_num].get('across_length', 0)
            if length > 0:
                candidates = generate_multiple_candidates(clue_text, length, clue_num)
                across_candidates[clue_num] = candidates
                logging.info(f"Generated {len(candidates)} candidates for across {clue_num}: {candidates}")
    
    # Generate candidates for down clues
    for clue_num, clue_text in sorted_down:
        if clue_num in clue_positions:
            length = clue_positions[clue_num].get('down_length', 0)
            if length > 0:
                candidates = generate_multiple_candidates(clue_text, length, clue_num)
                down_candidates[clue_num] = candidates
                logging.info(f"Generated {len(candidates)} candidates for down {clue_num}: {candidates}")
    
    # Use constraint satisfaction to find the best solution
    across_answers, down_answers = solve_with_intersection_constraints(
        clue_positions, across_candidates, down_candidates
    )
    
    # Build final solution
    final_solution = build_solution_grid(grid, clue_positions, across_answers, down_answers)
    
    return format_solution(final_solution, across_answers, down_answers)

def generate_multiple_candidates(clue_text, length, clue_num):
    """Generate multiple candidate answers for a clue using better prompting"""
    candidates = []
    
    try:
        # First attempt: focused crossword solving
        prompt = f"""You are an expert crossword solver. For this clue, give me 3-5 possible answers.
Each answer must be exactly {length} letters long.
Return ONLY the answers, one per line, in UPPERCASE with no spaces or punctuation.

Crossword clue: {clue_text}
Answer length: {length} letters

Think about:
- Common crossword answers
- Wordplay, puns, anagrams
- Abbreviations and acronyms
- Proper nouns (names, places)
- Multiple meanings of words

Answers:"""
        
        response = execute_llm(prompt)
        
        # Parse candidates from response
        for line in response.strip().split('\n'):
            line = line.strip().upper()
            clean_line = ''.join(c for c in line if c.isalpha())
            if len(clean_line) == length:
                candidates.append(clean_line)
        
        # If we got good candidates, also try a focused single-answer approach
        if len(candidates) >= 1:
            prompt2 = f"""What is the most likely answer to this crossword clue?
Clue: {clue_text}
Length: {length} letters

Think step by step:
1. What is the literal meaning?
2. Are there any wordplay elements?
3. What are common crossword conventions?

Give me your single best answer in UPPERCASE:"""
            
            response2 = execute_llm(prompt2)
            for line in response2.strip().split('\n'):
                line = line.strip().upper()
                clean_line = ''.join(c for c in line if c.isalpha())
                if len(clean_line) == length and clean_line not in candidates:
                    candidates.insert(0, clean_line)  # Put best guess first
        
        # Try one more approach if we don't have enough candidates
        if len(candidates) < 3:
            prompt3 = f"""For the crossword clue "{clue_text}" ({length} letters), consider these possibilities:
- Is it a common word or phrase?
- Could it be an abbreviation?
- Is there wordplay involved?
- Could it be a proper noun?

What other answers fit? Give me 2-3 more possibilities in UPPERCASE:"""
            
            response3 = execute_llm(prompt3)
            for line in response3.strip().split('\n'):
                line = line.strip().upper()
                clean_line = ''.join(c for c in line if c.isalpha())
                if len(clean_line) == length and clean_line not in candidates:
                    candidates.append(clean_line)
        
        # Ensure we have at least one candidate
        if not candidates:
            candidates = [generate_fallback_answer(clue_text, length)]
        
        return candidates[:5]  # Limit to 5 candidates
        
    except Exception as e:
        logging.error(f"Error generating candidates for clue {clue_num}: {e}")
        return [generate_fallback_answer(clue_text, length)]

def generate_fallback_answer(clue_text, length):
    """Generate a fallback answer when LLM fails"""
    # Try to extract key words from the clue
    words = clue_text.upper().split()
    for word in words:
        clean_word = ''.join(c for c in word if c.isalpha())
        if len(clean_word) == length:
            return clean_word
    
    # If no word fits, return X's
    return 'X' * length

def solve_with_intersection_constraints(clue_positions, across_candidates, down_candidates):
    """Use constraint satisfaction to find the best combination"""
    
    # Initialize with first candidates
    best_across = {}
    best_down = {}
    
    for clue_num, candidates in across_candidates.items():
        if candidates:
            best_across[clue_num] = candidates[0]
    
    for clue_num, candidates in down_candidates.items():
        if candidates:
            best_down[clue_num] = candidates[0]
    
    # Iteratively improve by checking intersections
    max_iterations = 5
    for iteration in range(max_iterations):
        changed = False
        conflicts_resolved = 0
        
        # Check all intersections
        for across_num in list(best_across.keys()):
            if across_num not in clue_positions:
                continue
                
            across_pos = clue_positions[across_num]
            across_answer = best_across[across_num]
            
            for down_num in list(best_down.keys()):
                if down_num not in clue_positions:
                    continue
                    
                down_pos = clue_positions[down_num]
                down_answer = best_down[down_num]
                
                # Find intersection point
                intersection = find_intersection(across_pos, across_answer, down_pos, down_answer)
                
                if intersection:
                    across_idx, down_idx = intersection
                    across_letter = across_answer[across_idx]
                    down_letter = down_answer[down_idx]
                    
                    if across_letter != down_letter:
                        # Conflict! Try to resolve
                        logging.info(f"Conflict at {across_num}x{down_num}: '{across_letter}' vs '{down_letter}'")
                        
                        # Try alternative candidates
                        resolved = False
                        
                        # Try other across candidates
                        for candidate in across_candidates.get(across_num, []):
                            if (across_idx < len(candidate) and 
                                candidate[across_idx] == down_letter and
                                candidate != across_answer):
                                best_across[across_num] = candidate
                                changed = True
                                resolved = True
                                conflicts_resolved += 1
                                logging.info(f"Resolved: changed across {across_num} to {candidate}")
                                break
                        
                        # Try other down candidates if across didn't work
                        if not resolved:
                            for candidate in down_candidates.get(down_num, []):
                                if (down_idx < len(candidate) and 
                                    candidate[down_idx] == across_letter and
                                    candidate != down_answer):
                                    best_down[down_num] = candidate
                                    changed = True
                                    resolved = True
                                    conflicts_resolved += 1
                                    logging.info(f"Resolved: changed down {down_num} to {candidate}")
                                    break
        
        logging.info(f"Iteration {iteration + 1}: resolved {conflicts_resolved} conflicts")
        
        if not changed:
            break
    
    return best_across, best_down

def find_intersection(across_pos, across_answer, down_pos, down_answer):
    """Find if and where two answers intersect"""
    across_row = across_pos['row']
    across_col = across_pos['col']
    down_row = down_pos['row']
    down_col = down_pos['col']
    
    # Check if they intersect
    if (across_row >= down_row and 
        across_row < down_row + len(down_answer) and
        down_col >= across_col and 
        down_col < across_col + len(across_answer)):
        
        across_idx = down_col - across_col
        down_idx = across_row - down_row
        
        if (0 <= across_idx < len(across_answer) and 
            0 <= down_idx < len(down_answer)):
            return (across_idx, down_idx)
    
    return None

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

def build_solution_grid(grid, clue_positions, across_answers, down_answers):
    """Build the solution grid from the solved clues"""
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0
    
    solution = [['' for _ in range(width)] for _ in range(height)]
    
    # Copy black squares
    for row in range(height):
        for col in range(width):
            if grid[row][col] == '.':
                solution[row][col] = '.'
    
    # Place across answers
    for clue_num, answer in across_answers.items():
        if clue_num in clue_positions:
            pos = clue_positions[clue_num]
            row, col = pos['row'], pos['col']
            for i, letter in enumerate(answer):
                if col + i < width:
                    solution[row][col + i] = letter
    
    # Place down answers
    for clue_num, answer in down_answers.items():
        if clue_num in clue_positions:
            pos = clue_positions[clue_num]
            row, col = pos['row'], pos['col']
            for i, letter in enumerate(answer):
                if row + i < height:
                    # Only overwrite if empty or same letter
                    if solution[row + i][col] == '' or solution[row + i][col] == letter:
                        solution[row + i][col] = letter
    
    # Fill any remaining empty squares with 'X'
    for row in range(height):
        for col in range(width):
            if solution[row][col] == '':
                solution[row][col] = 'X'
    
    return solution

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