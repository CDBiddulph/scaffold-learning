import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    try:
        logging.info("Starting crossword puzzle solving")
        
        # Strategy: Use multiple LLM calls for better accuracy
        # First, solve the clues individually
        clue_solutions = solve_clues_individually(input_string)
        
        # Then, use those solutions to fill the grid
        final_solution = create_complete_solution(input_string, clue_solutions)
        
        logging.info("Crossword puzzle solving completed")
        return final_solution
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return ""

def solve_clues_individually(input_string):
    """Solve clues one by one for better accuracy"""
    logging.info("Solving individual clues")
    
    # Extract clues from input
    lines = input_string.strip().split('\n')
    clues_started = False
    current_section = None
    clues = []
    
    for line in lines:
        line = line.strip()
        if line.startswith('Across:'):
            clues_started = True
            current_section = 'Across'
            continue
        elif line.startswith('Down:'):
            current_section = 'Down'
            continue
        elif clues_started and line:
            clues.append((current_section, line))
    
    # Solve each clue
    solutions = {}
    for section, clue_line in clues:
        match = re.match(r'\s*(\d+)\.\s*(.+)', clue_line)
        if match:
            clue_num = int(match.group(1))
            clue_text = match.group(2).strip()
            
            prompt = f"""Solve this crossword clue. Provide only the answer in UPPERCASE letters, no explanations.

Clue: {clue_text}

Answer:"""
            
            try:
                response = execute_llm(prompt)
                answer = response.strip().upper()
                # Clean up the answer - remove any non-alphabetic characters
                answer = ''.join(c for c in answer if c.isalpha())
                if answer:
                    solutions[clue_num] = (section, answer)
                    logging.info(f"Solved clue {clue_num}: {answer}")
            except Exception as e:
                logging.warning(f"Failed to solve clue {clue_num}: {e}")
    
    return solutions

def create_complete_solution(input_string, clue_solutions):
    """Create the complete solution using the solved clues"""
    logging.info("Creating complete solution")
    
    prompt = f"""You are a crossword puzzle expert. Using the provided clue solutions, create the complete crossword solution.

Original puzzle:
{input_string}

Clue solutions:
{format_clue_solutions(clue_solutions)}

Please provide the solution in this EXACT format:

<complete_grid_with_spaces>

Across:
<across_answers_with_numbers>

Down:
<down_answers_with_numbers>

Requirements:
- Grid must use spaces between characters, '.' for black squares, UPPERCASE letters for filled squares
- Across/Down sections must list answers with proper numbering (e.g., "  1. ANSWER")
- Use the provided clue solutions
- Ensure all intersections are correct
- Do not include any extra text

Make sure the grid dimensions match the input and all answers fit properly with correct intersections."""
    
    response = execute_llm(prompt)
    return response.strip()

def format_clue_solutions(solutions):
    """Format the clue solutions for the prompt"""
    across_solutions = []
    down_solutions = []
    
    for clue_num, (section, answer) in solutions.items():
        if section == 'Across':
            across_solutions.append(f"{clue_num}. {answer}")
        else:
            down_solutions.append(f"{clue_num}. {answer}")
    
    result = []
    if across_solutions:
        result.append("Across:")
        result.extend(sorted(across_solutions, key=lambda x: int(x.split('.')[0])))
    if down_solutions:
        result.append("Down:")
        result.extend(sorted(down_solutions, key=lambda x: int(x.split('.')[0])))
    
    return '\n'.join(result)