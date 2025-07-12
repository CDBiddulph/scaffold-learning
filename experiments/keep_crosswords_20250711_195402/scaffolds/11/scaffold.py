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
        solution = solve_crossword(grid, across_clues, down_clues)
        
        return solution
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return ""

def solve_crossword(grid, across_clues, down_clues):
    """Solve the crossword puzzle using iterative LLM calls"""
    
    # First, let's get the clue positions and lengths
    clue_positions = find_clue_positions(grid)
    
    # Solve individual clues
    across_answers = {}
    down_answers = {}
    
    # Start with shorter clues as they're often easier
    sorted_across = sorted(across_clues.items(), key=lambda x: clue_positions.get(x[0], {}).get('across_length', 0))
    sorted_down = sorted(down_clues.items(), key=lambda x: clue_positions.get(x[0], {}).get('down_length', 0))
    
    # Solve across clues
    for clue_num, clue_text in sorted_across:
        if clue_num in clue_positions:
            length = clue_positions[clue_num].get('across_length', 0)
            if length > 0:
                answer = solve_single_clue(clue_text, length, clue_num, 'across')
                if answer:
                    across_answers[clue_num] = answer
                    logging.info(f"Solved across {clue_num}: {answer}")
    
    # Solve down clues
    for clue_num, clue_text in sorted_down:
        if clue_num in clue_positions:
            length = clue_positions[clue_num].get('down_length', 0)
            if length > 0:
                answer = solve_single_clue(clue_text, length, clue_num, 'down')
                if answer:
                    down_answers[clue_num] = answer
                    logging.info(f"Solved down {clue_num}: {answer}")
    
    # Build the solution grid
    solution_grid = build_solution_grid(grid, clue_positions, across_answers, down_answers)
    
    # Format the output
    return format_solution(solution_grid, across_answers, down_answers)

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

def solve_single_clue(clue_text, length, clue_num, direction):
    """Solve a single crossword clue"""
    try:
        prompt = f"""Solve this crossword clue. The answer should be exactly {length} letters long.
Return only the answer in uppercase letters, no spaces or punctuation.

Clue: {clue_text}
Length: {length} letters

Answer:"""
        
        response = execute_llm(prompt)
        
        # Extract the answer from the response
        lines = response.strip().split('\n')
        for line in lines:
            line = line.strip().upper()
            # Remove any non-alphabetic characters
            clean_line = ''.join(c for c in line if c.isalpha())
            if len(clean_line) == length:
                return clean_line
        
        # If no exact match, try to find the best candidate
        for line in lines:
            line = line.strip().upper()
            clean_line = ''.join(c for c in line if c.isalpha())
            if clean_line and abs(len(clean_line) - length) <= 1:
                return clean_line[:length].ljust(length, 'X')
        
        logging.warning(f"Could not solve clue {clue_num} ({direction}): {clue_text}")
        return None
        
    except Exception as e:
        logging.error(f"Error solving clue {clue_num}: {e}")
        return None

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