import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Parse the input to extract grid and clues
        lines = input_string.strip().split('\n')
        
        # Find where clues start
        across_start = -1
        down_start = -1
        
        for i, line in enumerate(lines):
            if line.strip().startswith('Across:'):
                across_start = i
            elif line.strip().startswith('Down:'):
                down_start = i
        
        if across_start == -1 or down_start == -1:
            logging.error("Could not find clue sections")
            return ""
        
        # Extract grid (everything before clues)
        grid_lines = []
        for i in range(across_start):
            line = lines[i].strip()
            if line:
                grid_lines.append(line)
        
        # Extract all clues
        clue_lines = lines[across_start:]
        
        # Format for LLM
        grid_str = '\n'.join(grid_lines)
        clue_str = '\n'.join(clue_lines)
        
        logging.info(f"Grid has {len(grid_lines)} rows")
        logging.info(f"Found {len(clue_lines)} clue lines")
        
        # Check if we're approaching timeout
        if time.time() - start_time > 100:
            logging.warning("Approaching timeout, returning empty")
            return ""
        
        # Use LLM to solve the crossword
        prompt = f"""Solve this crossword puzzle completely and accurately.

Grid structure (- = empty square, . = black square):
{grid_str}

{clue_str}

Please provide the complete solution in exactly this format:

[The completed grid with letters filled in, keeping '.' for black squares]

Across:
1. [ANSWER]
2. [ANSWER]
...

Down:
1. [ANSWER]
2. [ANSWER]
...

Important: 
- Fill all empty squares (-) with the correct letters
- Keep black squares (.) as they are
- Provide complete answers for all clues
- Make sure answers fit the grid structure
- Use capital letters for all answers
"""
        
        response = execute_llm(prompt)
        
        # Clean up the response
        response = response.strip()
        
        # Log the response for debugging
        logging.info(f"LLM response length: {len(response)}")
        
        return response
        
    except Exception as e:
        logging.error(f"Error in process_input: {e}")
        return ""