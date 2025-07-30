import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    try:
        # Parse the input to separate grid and clues
        lines = input_string.strip().split('\n')
        
        # Find where clues start
        grid_lines = []
        clue_lines = []
        in_clues = False
        
        for line in lines:
            line = line.strip()
            if line.startswith('Across:') or line.startswith('Down:'):
                in_clues = True
            
            if in_clues:
                clue_lines.append(line)
            else:
                grid_lines.append(line)
        
        logging.info(f"Parsed {len(grid_lines)} grid lines and {len(clue_lines)} clue lines")
        
        # Solve the crossword puzzle with a focused approach
        solution = solve_crossword_systematically(grid_lines, clue_lines)
        
        return solution
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return ""

def solve_crossword_systematically(grid_lines, clue_lines):
    """Solve the crossword puzzle systematically"""
    
    # Format the complete puzzle for the LLM
    grid_str = '\n'.join(grid_lines)
    clues_str = '\n'.join(clue_lines)
    
    prompt = f"""
You are an expert crossword solver. Solve this crossword puzzle step by step.

Grid pattern (- represents empty squares, . represents black squares):
{grid_str}

{clues_str}

Important rules:
1. In crosswords, numbers are assigned to squares that start new words
2. A square gets a number if it starts an across word, a down word, or both
3. Numbers are assigned sequentially from left to right, top to bottom
4. Each dash (-) gets replaced with exactly one letter
5. Black squares (.) stay as periods
6. Across and down answers must intersect correctly

Solve this completely and provide the solution in this exact format:

[Grid with single letters separated by spaces, periods for black squares]

Across:
[numbered list: number. ANSWER in ALL CAPS]

Down:  
[numbered list: number. ANSWER in ALL CAPS]

Take your time and make sure the grid numbering matches the clue numbering exactly.
"""
    
    try:
        response = execute_llm(prompt)
        
        # Clean up the response
        response = response.strip()
        
        # Log the raw response for debugging
        logging.info(f"Raw LLM response length: {len(response)}")
        
        return response
        
    except Exception as e:
        logging.error(f"Error calling LLM to solve crossword: {e}")
        return ""