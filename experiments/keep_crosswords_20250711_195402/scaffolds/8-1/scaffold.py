import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    try:
        # Parse the input to extract grid template and clues
        grid_template, across_clues, down_clues = parse_input(input_string)
        logging.info(f"Found {len(across_clues)} across clues and {len(down_clues)} down clues")
        
        # Solve the crossword puzzle holistically
        solved_grid, solved_across, solved_down = solve_crossword_holistically(
            grid_template, across_clues, down_clues
        )
        
        # Format output with both grid and clues
        result = format_complete_solution(solved_grid, solved_across, solved_down)
        
        return result
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "Error: Could not process input"

def parse_input(input_string):
    lines = input_string.strip().split('\n')
    
    # Extract grid template
    grid_template = []
    line_idx = 0
    while line_idx < len(lines):
        line = lines[line_idx].strip()
        if line.startswith("Across:") or line.startswith("Down:"):
            break
        if line:
            grid_template.append(line.split())
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
            match = re.match(r'\s*(\d+)\.\s*(.+)', line)
            if match:
                clue_num = int(match.group(1))
                clue_text = match.group(2).strip()
                if current_section == "across":
                    across_clues[clue_num] = clue_text
                else:
                    down_clues[clue_num] = clue_text
    
    return grid_template, across_clues, down_clues

def solve_crossword_holistically(grid_template, across_clues, down_clues):
    # Create a comprehensive prompt to solve the entire crossword at once
    # This should be more accurate than solving individual clues
    
    grid_str = "\n".join([" ".join(row) for row in grid_template])
    across_str = "\n".join([f"{num}. {clue}" for num, clue in across_clues.items()])
    down_str = "\n".join([f"{num}. {clue}" for num, clue in down_clues.items()])
    
    prompt = f"""You are an expert crossword puzzle solver. Solve this complete crossword puzzle.

Grid template (- represents empty squares, . represents black squares):
{grid_str}

Across clues:
{across_str}

Down clues:
{down_str}

Please solve this crossword puzzle completely. Consider:
- Intersecting letters must match between across and down answers
- Common crossword conventions and wordplay
- Letter patterns and word lengths
- All clues must be satisfied simultaneously

Respond with the completed grid first (replace - with letters, keep . for black squares), then list all the answers.

Format your response exactly as:
GRID:
[completed grid with letters and dots]

ACROSS:
1. ANSWER
2. ANSWER
...

DOWN:
1. ANSWER
2. ANSWER
..."""
    
    try:
        response = execute_llm(prompt)
        return parse_holistic_solution(response, grid_template, across_clues, down_clues)
    except Exception as e:
        logging.error(f"Error in holistic solving: {e}")
        # Fallback to enhanced individual solving
        return solve_with_enhanced_individual_method(grid_template, across_clues, down_clues)

def parse_holistic_solution(response, grid_template, across_clues, down_clues):
    try:
        # Parse the grid
        grid_match = re.search(r'GRID:\s*\n(.*?)\n\s*ACROSS:', response, re.DOTALL)
        if grid_match:
            grid_text = grid_match.group(1).strip()
            solved_grid = [line.split() for line in grid_text.split('\n') if line.strip()]
        else:
            solved_grid = grid_template  # fallback
        
        # Parse across answers
        across_match = re.search(r'ACROSS:\s*\n(.*?)\n\s*DOWN:', response, re.DOTALL)
        solved_across = {}
        if across_match:
            across_text = across_match.group(1).strip()
            solved_across = parse_answer_section(across_text)
        
        # Parse down answers
        down_match = re.search(r'DOWN:\s*\n(.*?)$', response, re.DOTALL)
        solved_down = {}
        if down_match:
            down_text = down_match.group(1).strip()
            solved_down = parse_answer_section(down_text)
        
        logging.info(f"Parsed {len(solved_across)} across and {len(solved_down)} down answers from holistic solution")
        return solved_grid, solved_across, solved_down
        
    except Exception as e:
        logging.error(f"Error parsing holistic solution: {e}")
        return solve_with_enhanced_individual_method(grid_template, across_clues, down_clues)

def parse_answer_section(text):
    answers = {}
    for line in text.split('\n'):
        line = line.strip()
        if line:
            match = re.match(r'\s*(\d+)\.\s*(.+)', line)
            if match:
                clue_num = int(match.group(1))
                answer = match.group(2).strip().upper()
                answers[clue_num] = answer
    return answers

def solve_with_enhanced_individual_method(grid_template, across_clues, down_clues):
    # Enhanced individual clue solving with better prompting
    solved_across = {}
    solved_down = {}
    
    # Solve across clues
    for clue_num, clue_text in across_clues.items():
        answer = solve_single_clue_enhanced(clue_text, clue_num, "across")
        if answer:
            solved_across[clue_num] = answer
    
    # Solve down clues
    for clue_num, clue_text in down_clues.items():
        answer = solve_single_clue_enhanced(clue_text, clue_num, "down")
        if answer:
            solved_down[clue_num] = answer
    
    return grid_template, solved_across, solved_down

def solve_single_clue_enhanced(clue_text, clue_num, direction):
    prompt = f"""You are an expert crossword puzzle solver. Solve this {direction} clue.

Clue {clue_num}: {clue_text}

Think carefully about:
- Crossword conventions and common patterns
- Wordplay, puns, abbreviations, double meanings
- Pop culture references and current events
- The most likely answer for a crossword puzzle

Respond with ONLY the answer in capital letters, no explanation."""
    
    try:
        response = execute_llm(prompt)
        answer = clean_answer(response)
        
        if answer and answer.isalpha() and len(answer) > 0:
            logging.info(f"Solved {direction} {clue_num}: {clue_text} = {answer}")
            return answer
        else:
            logging.warning(f"Invalid answer for {direction} {clue_num}: {clue_text}")
            return None
            
    except Exception as e:
        logging.error(f"Error solving {direction} clue '{clue_text}': {e}")
        return None

def clean_answer(response):
    # Clean up the LLM response to extract just the answer
    answer = response.strip().upper()
    answer = answer.strip('"').strip("'")
    
    # Take the first line if multiple lines
    lines = [line.strip() for line in answer.split('\n') if line.strip()]
    if lines:
        answer = lines[0]
    
    # Take the first word if multiple words
    words = answer.split()
    if words:
        answer = words[0]
    
    # Remove any trailing punctuation
    answer = re.sub(r'[^\w]', '', answer)
    
    return answer

def format_complete_solution(solved_grid, solved_across, solved_down):
    # Format the complete solution with both grid and clues
    result = ""
    
    # Add the solved grid
    for row in solved_grid:
        result += " ".join(row) + "\n"
    
    result += "\nAcross:\n"
    for clue_num in sorted(solved_across.keys()):
        result += f"{clue_num}. {solved_across[clue_num]}\n"
    
    result += "\nDown:\n"
    for clue_num in sorted(solved_down.keys()):
        result += f"{clue_num}. {solved_down[clue_num]}\n"
    
    return result.strip()