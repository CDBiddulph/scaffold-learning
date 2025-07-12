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

def solve_entire_puzzle(grid, across_clues, down_clues):
    """Solve the entire crossword puzzle at once using LLM"""
    
    # Format the grid for the LLM
    grid_str = ""
    for row in grid:
        grid_str += " ".join(row) + "\n"
    
    # Format the clues
    across_str = "Across:\n"
    for num in sorted(across_clues.keys()):
        across_str += f"  {num}. {across_clues[num]}\n"
    
    down_str = "Down:\n"
    for num in sorted(down_clues.keys()):
        down_str += f"  {num}. {down_clues[num]}\n"
    
    # Create comprehensive prompt
    prompt = f"""You are a crossword puzzle expert. Solve this entire crossword puzzle.

The grid uses '-' for empty squares and '.' for black squares.
Grid:
{grid_str}

{across_str}

{down_str}

Instructions:
1. Solve all the clues considering their intersections
2. Fill in the grid completely with letters (replace '-' with letters, keep '.' as black squares)
3. Output the filled grid first, then list all the answers

Output format:
[FILLED GRID - one line per row, space-separated]

Across:
  1. ANSWER1
  5. ANSWER2
  ...

Down:
  1. ANSWER1
  2. ANSWER2
  ...

Think step by step about intersections and make sure all answers fit together perfectly."""

    try:
        response = execute_llm(prompt)
        return response.strip()
    except Exception as e:
        logging.error(f"Error solving entire puzzle: {e}")
        return None

def clean_and_validate_solution(solution, grid):
    """Clean and validate the LLM solution"""
    if not solution:
        return None
    
    lines = solution.strip().split('\n')
    
    # Find the grid section (before "Across:")
    grid_lines = []
    for i, line in enumerate(lines):
        if line.strip().startswith('Across:'):
            break
        if line.strip():
            grid_lines.append(line.strip())
    
    # Validate grid dimensions
    if len(grid_lines) != len(grid):
        logging.warning(f"Grid dimension mismatch: expected {len(grid)} rows, got {len(grid_lines)}")
        return None
    
    # Clean the grid
    cleaned_grid = []
    for i, line in enumerate(grid_lines):
        row = line.split()
        if len(row) != len(grid[i]):
            logging.warning(f"Grid width mismatch at row {i}")
            return None
        cleaned_grid.append(row)
    
    return solution

def extract_answers_from_solution(solution):
    """Extract just the answers from the solution for fallback"""
    lines = solution.strip().split('\n')
    
    across_answers = {}
    down_answers = {}
    current_section = None
    
    for line in lines:
        line = line.strip()
        if line.startswith('Across:'):
            current_section = 'across'
        elif line.startswith('Down:'):
            current_section = 'down'
        elif line and current_section:
            match = re.match(r'\s*(\d+)\.\s*(.+)', line)
            if match:
                clue_num = int(match.group(1))
                answer = match.group(2).strip().upper()
                # Clean answer - remove non-alphabetic characters
                answer = ''.join(c for c in answer if c.isalpha())
                if current_section == 'across':
                    across_answers[clue_num] = answer
                else:
                    down_answers[clue_num] = answer
    
    return across_answers, down_answers

def solve_with_multiple_attempts(grid, across_clues, down_clues):
    """Try multiple approaches to solve the puzzle"""
    
    # First attempt: solve entire puzzle at once
    solution = solve_entire_puzzle(grid, across_clues, down_clues)
    if solution:
        cleaned = clean_and_validate_solution(solution, grid)
        if cleaned:
            return cleaned
    
    # Second attempt: more focused prompt
    prompt = f"""Solve this crossword puzzle. The grid uses '-' for empty squares and '.' for black squares.

Grid structure:
{chr(10).join(' '.join(row) for row in grid)}

Clues:
Across: {dict(sorted(across_clues.items()))}
Down: {dict(sorted(down_clues.items()))}

Output the solution in this exact format:
[Grid with letters filled in, one row per line]

Across:
  1. ANSWER
  5. ANSWER
  ...

Down:
  1. ANSWER
  2. ANSWER
  ..."""
    
    try:
        response = execute_llm(prompt)
        cleaned = clean_and_validate_solution(response, grid)
        if cleaned:
            return cleaned
    except Exception as e:
        logging.error(f"Second attempt failed: {e}")
    
    # Third attempt: ask for just the answers and reconstruct
    answers_prompt = f"""List the answers to these crossword clues:

Across clues:
{chr(10).join(f"{num}. {clue}" for num, clue in sorted(across_clues.items()))}

Down clues:
{chr(10).join(f"{num}. {clue}" for num, clue in sorted(down_clues.items()))}

Output format:
Across:
  1. ANSWER
  5. ANSWER
  ...

Down:
  1. ANSWER
  2. ANSWER
  ..."""
    
    try:
        response = execute_llm(answers_prompt)
        across_answers, down_answers = extract_answers_from_solution(response)
        
        # Reconstruct the solution
        reconstructed = reconstruct_solution(grid, across_answers, down_answers)
        return reconstructed
    except Exception as e:
        logging.error(f"Third attempt failed: {e}")
    
    return None

def reconstruct_solution(grid, across_answers, down_answers):
    """Reconstruct the full solution from answers"""
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0
    
    # Create filled grid
    filled_grid = [row[:] for row in grid]
    for row in range(height):
        for col in range(width):
            if filled_grid[row][col] == '-':
                filled_grid[row][col] = ' '
    
    # Find clue positions
    clue_positions = {}
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
                clue_positions[current_num] = (row, col, starts_across, starts_down)
                current_num += 1
    
    # Fill in answers
    for clue_num, answer in across_answers.items():
        if clue_num in clue_positions:
            row, col, starts_across, _ = clue_positions[clue_num]
            if starts_across:
                for i, letter in enumerate(answer):
                    if col + i < width:
                        filled_grid[row][col + i] = letter
    
    for clue_num, answer in down_answers.items():
        if clue_num in clue_positions:
            row, col, _, starts_down = clue_positions[clue_num]
            if starts_down:
                for i, letter in enumerate(answer):
                    if row + i < height:
                        filled_grid[row + i][col] = letter
    
    # Format output
    result = []
    for row in filled_grid:
        result.append(' '.join(row))
    
    result.append('')
    result.append('Across:')
    for num in sorted(across_answers.keys()):
        result.append(f'  {num}. {across_answers[num]}')
    
    result.append('')
    result.append('Down:')
    for num in sorted(down_answers.keys()):
        result.append(f'  {num}. {down_answers[num]}')
    
    return '\n'.join(result)

def process_input(input_string: str) -> str:
    try:
        logging.info("Starting crossword puzzle solution")
        grid, across_clues, down_clues = parse_input(input_string)
        logging.info(f"Parsed grid: {len(grid)}x{len(grid[0]) if grid else 0}")
        logging.info(f"Across clues: {len(across_clues)}, Down clues: {len(down_clues)}")
        
        solution = solve_with_multiple_attempts(grid, across_clues, down_clues)
        
        if solution:
            logging.info("Successfully solved puzzle")
            return solution
        else:
            logging.error("Failed to solve puzzle")
            return ""
            
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return ""