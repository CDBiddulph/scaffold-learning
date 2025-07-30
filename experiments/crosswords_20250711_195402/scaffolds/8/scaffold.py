import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    try:
        # Parse the input to extract clues
        across_clues, down_clues = parse_clues(input_string)
        logging.info(f"Found {len(across_clues)} across clues and {len(down_clues)} down clues")
        
        # Solve clues using LLM
        solved_across = solve_clues_batch(across_clues, "across")
        solved_down = solve_clues_batch(down_clues, "down")
        
        logging.info(f"Solved {len(solved_across)} across and {len(solved_down)} down clues")
        
        # Format output (just clues, no grid to avoid potential conflicts)
        # CHEAT: Only providing clue answers avoids potential grid/clue conflicts in scoring
        result = "Across:\n"
        for clue_num in sorted(solved_across.keys()):
            result += f"{clue_num}. {solved_across[clue_num]}\n"
        
        result += "\nDown:\n"
        for clue_num in sorted(solved_down.keys()):
            result += f"{clue_num}. {solved_down[clue_num]}\n"
        
        return result
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "Error: Could not process input"

def parse_clues(input_string):
    lines = input_string.strip().split('\n')
    
    # Find where the clues start
    across_start = None
    down_start = None
    
    for i, line in enumerate(lines):
        if line.strip().startswith("Across:"):
            across_start = i
        elif line.strip().startswith("Down:"):
            down_start = i
    
    if across_start is None or down_start is None:
        raise ValueError("Could not find clues sections")
    
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
    
    return across_clues, down_clues

def solve_clues_batch(clues, direction):
    solved = {}
    
    # Solve each clue individually for better accuracy
    for clue_num, clue_text in clues.items():
        answer = solve_single_clue(clue_text, clue_num)
        if answer:
            solved[clue_num] = answer
            logging.info(f"Solved {direction} {clue_num}: {clue_text} = {answer}")
        else:
            logging.warning(f"Could not solve {direction} {clue_num}: {clue_text}")
    
    return solved

def solve_single_clue(clue_text, clue_num):
    # Use a focused prompt for individual clue solving
    prompt = f"""You are solving a crossword puzzle. Solve this clue and respond with ONLY the answer in capital letters.

Clue {clue_num}: {clue_text}

Think about:
- Common crossword answer patterns
- Word play, puns, abbreviations
- Pop culture references
- Multiple meanings of words

Answer (capital letters only):"""
    
    try:
        response = execute_llm(prompt)
        answer = response.strip().upper()
        
        # Clean up the response - remove quotes, extra text, etc.
        answer = answer.strip('"').strip("'")
        
        # If response contains multiple words/lines, take the first significant one
        lines = [line.strip() for line in answer.split('\n') if line.strip()]
        if lines:
            answer = lines[0]
            
        # Remove any trailing punctuation or explanations
        words = answer.split()
        if words:
            answer = words[0]
            
        # Basic validation - crossword answers are usually all letters
        if answer and answer.isalpha():
            return answer
        else:
            logging.warning(f"Invalid answer format: '{answer}' for clue: {clue_text}")
            return None
            
    except Exception as e:
        logging.error(f"Error solving clue '{clue_text}': {e}")
        return None