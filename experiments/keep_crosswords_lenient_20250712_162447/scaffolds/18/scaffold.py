import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout_buffer = 15  # seconds buffer before timeout
    
    try:
        # Parse input
        grid_lines, across_clues, down_clues = parse_input(input_string)
        
        # Check timeout
        if time.time() - start_time > 120 - timeout_buffer:
            return ""
        
        # Try multiple approaches to solve the puzzle
        solution = solve_crossword_multiple_attempts(grid_lines, across_clues, down_clues, start_time)
        
        return solution
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return ""

def parse_input(input_string):
    lines = input_string.strip().split('\n')
    
    # Find where grid ends and clues begin
    grid_lines = []
    line_idx = 0
    
    while line_idx < len(lines):
        line = lines[line_idx].strip()
        if not line or line.startswith("Across:") or line.startswith("Down:"):
            break
        grid_lines.append(line)
        line_idx += 1
    
    # Extract clues
    across_clues = {}
    down_clues = {}
    current_section = None
    
    for i in range(line_idx, len(lines)):
        line = lines[i].strip()
        if line.startswith("Across:"):
            current_section = "across"
        elif line.startswith("Down:"):
            current_section = "down"
        elif line and current_section:
            # Parse clue line
            match = re.match(r'\s*(\d+)\.\s*(.+)', line)
            if match:
                clue_num = int(match.group(1))
                clue_text = match.group(2).strip()
                if current_section == "across":
                    across_clues[clue_num] = clue_text
                else:
                    down_clues[clue_num] = clue_text
    
    return grid_lines, across_clues, down_clues

def solve_crossword_multiple_attempts(grid_lines, across_clues, down_clues, start_time):
    timeout_buffer = 15
    
    # First attempt: Solve the entire puzzle at once
    try:
        if time.time() - start_time > 120 - timeout_buffer:
            return ""
            
        logging.info("Attempting to solve entire puzzle at once")
        full_solution = solve_full_puzzle(grid_lines, across_clues, down_clues)
        if full_solution and validate_solution_format(full_solution):
            logging.info("Successfully solved full puzzle")
            return full_solution
    except Exception as e:
        logging.error(f"Error in full puzzle solve: {e}")
    
    # Second attempt: Solve individual clues and reconstruct
    try:
        if time.time() - start_time > 120 - timeout_buffer:
            return ""
            
        logging.info("Attempting to solve individual clues")
        individual_solution = solve_individual_clues_approach(grid_lines, across_clues, down_clues)
        if individual_solution and validate_solution_format(individual_solution):
            logging.info("Successfully solved with individual clues approach")
            return individual_solution
    except Exception as e:
        logging.error(f"Error in individual clue solve: {e}")
    
    # Third attempt: Focused approach with better prompting
    try:
        if time.time() - start_time > 120 - timeout_buffer:
            return ""
            
        logging.info("Attempting focused solution approach")
        focused_solution = solve_focused_approach(grid_lines, across_clues, down_clues)
        if focused_solution and validate_solution_format(focused_solution):
            logging.info("Successfully solved with focused approach")
            return focused_solution
    except Exception as e:
        logging.error(f"Error in focused solve: {e}")
    
    # Fallback: return empty
    logging.warning("All solution attempts failed")
    return ""

def solve_full_puzzle(grid_lines, across_clues, down_clues):
    grid_str = '\n'.join(grid_lines)
    
    across_str = '\n'.join([f"  {num}. {clue}" for num, clue in sorted(across_clues.items())])
    down_str = '\n'.join([f"  {num}. {clue}" for num, clue in sorted(down_clues.items())])
    
    prompt = f"""Solve this crossword puzzle completely. You must return the solution in this EXACT format:

[Grid with letters replacing dashes, maintaining exact same structure]

Across:
  1. ANSWER
  2. ANSWER
...

Down:
  1. ANSWER
  2. ANSWER
...

Input grid (replace - with letters, keep . for black squares):
{grid_str}

Across:
{across_str}

Down:
{down_str}

Important: Return ONLY the solution in the exact format shown above. Do not include any explanations or other text."""
    
    response = execute_llm(prompt)
    return response.strip()

def solve_individual_clues_approach(grid_lines, across_clues, down_clues):
    # Solve clues individually first
    across_answers = {}
    down_answers = {}
    
    # Solve across clues
    for num, clue in list(across_clues.items())[:10]:  # Limit to avoid timeout
        try:
            prompt = f"What is the answer to this crossword clue? Respond with ONLY the answer in all caps, no spaces: {clue}"
            response = execute_llm(prompt)
            answer = response.strip().upper().replace(" ", "").replace("-", "")
            if answer and answer.isalpha() and len(answer) <= 20:
                across_answers[num] = answer
        except:
            pass
    
    # Solve down clues
    for num, clue in list(down_clues.items())[:10]:  # Limit to avoid timeout
        try:
            prompt = f"What is the answer to this crossword clue? Respond with ONLY the answer in all caps, no spaces: {clue}"
            response = execute_llm(prompt)
            answer = response.strip().upper().replace(" ", "").replace("-", "")
            if answer and answer.isalpha() and len(answer) <= 20:
                down_answers[num] = answer
        except:
            pass
    
    # Now reconstruct the full solution
    return reconstruct_solution(grid_lines, across_answers, down_answers, across_clues, down_clues)

def solve_focused_approach(grid_lines, across_clues, down_clues):
    # More focused approach with better structure
    grid_str = '\n'.join(grid_lines)
    
    # Create a more structured prompt
    prompt = f"""You are solving a crossword puzzle. Here is the grid structure and clues:

GRID STRUCTURE:
{grid_str}

ACROSS CLUES:
{chr(10).join([f'{num}. {clue}' for num, clue in sorted(across_clues.items())])}

DOWN CLUES:
{chr(10).join([f'{num}. {clue}' for num, clue in sorted(down_clues.items())])}

Please solve this crossword and return the solution in exactly this format:

[Filled grid - replace dashes with letters, keep dots as dots]

Across:
  1. ANSWER
  2. ANSWER
...

Down:
  1. ANSWER
  2. ANSWER
...

Return ONLY the solution, no explanations."""
    
    response = execute_llm(prompt)
    return response.strip()

def reconstruct_solution(grid_lines, across_answers, down_answers, across_clues, down_clues):
    grid_str = '\n'.join(grid_lines)
    
    across_str = '\n'.join([f"  {num}. {answer}" for num, answer in sorted(across_answers.items())])
    down_str = '\n'.join([f"  {num}. {answer}" for num, answer in sorted(down_answers.items())])
    
    prompt = f"""Given this crossword grid structure and these solved answers, construct the complete solution:

Grid structure:
{grid_str}

Solved across answers:
{across_str}

Solved down answers:
{down_str}

Please return the complete solution in this exact format:

[Filled grid with letters replacing dashes]

Across:
{chr(10).join([f'  {num}. {across_answers.get(num, "???")}' for num in sorted(across_clues.keys())])}

Down:
{chr(10).join([f'  {num}. {down_answers.get(num, "???")}' for num in sorted(down_clues.keys())])}

Return ONLY the solution in the exact format above."""
    
    response = execute_llm(prompt)
    return response.strip()

def validate_solution_format(solution):
    """Basic validation to check if solution has expected format"""
    if not solution:
        return False
    
    # Check if it has the basic structure
    if "Across:" not in solution or "Down:" not in solution:
        return False
    
    # Check if it has multiple lines (not just a single line response)
    if len(solution.split('\n')) < 5:
        return False
    
    return True