import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    try:
        logging.info("Starting crossword puzzle solution")
        
        # Parse the input to separate grid and clues
        lines = input_string.strip().split('\n')
        
        # Find where clues start
        grid_lines = []
        clues_start = len(lines)
        for i, line in enumerate(lines):
            if line.strip().startswith('Across:'):
                clues_start = i
                break
            grid_lines.append(line.strip())
        
        # Extract clues
        clues = []
        for i in range(clues_start, len(lines)):
            line = lines[i].strip()
            if line:
                clues.append(line)
        
        grid_str = '\n'.join(grid_lines)
        clues_str = '\n'.join(clues)
        
        logging.info(f"Grid size: {len(grid_lines)} lines")
        logging.info(f"Number of clue lines: {len(clues)}")
        
        # Use LLM to solve the crossword in multiple steps for better accuracy
        
        # First, let's get the LLM to understand the structure
        structure_prompt = f"""Analyze this crossword puzzle structure:

Grid (. = black square, - = empty square):
{grid_str}

Clues:
{clues_str}

Please identify:
1. The grid dimensions
2. The total number of across clues
3. The total number of down clues
4. Any patterns you notice in the grid structure

Just provide a brief analysis, don't solve yet."""
        
        structure_response = execute_llm(structure_prompt)
        logging.info(f"Structure analysis: {structure_response}")
        
        # Now solve the crossword
        solve_prompt = f"""Solve this crossword puzzle completely and accurately.

Grid (. = black square, - = empty square):
{grid_str}

Clues:
{clues_str}

Please provide the solution in EXACTLY this format:
1. The filled grid with letters replacing the - symbols (keep . for black squares)
2. A blank line
3. "Across:" on its own line
4. Each across answer as "  X. ANSWER" where X is the clue number
5. A blank line
6. "Down:" on its own line  
7. Each down answer as "  X. ANSWER" where X is the clue number

Important:
- All answers must be in UPPERCASE
- Make sure answers fit the grid correctly
- The grid must have the exact same dimensions as the input
- Each answer should be just the word(s) that go in the grid spaces
- Double-check that intersecting letters match between across and down answers

Take your time to solve each clue carefully and ensure all intersections work."""
        
        response = execute_llm(solve_prompt)
        logging.info(f"Initial solution received, length: {len(response)}")
        
        # Validate and potentially refine the solution
        if not self._validate_solution_format(response):
            logging.warning("Solution format appears invalid, attempting to fix")
            
            fix_prompt = f"""The following crossword solution may have formatting issues. Please fix it to match the exact required format:

{response}

Required format:
1. Grid with letters (same dimensions as input, . for black squares)
2. Blank line
3. "Across:" 
4. "  X. ANSWER" for each across clue
5. Blank line
6. "Down:"
7. "  X. ANSWER" for each down clue

Make sure all answers are UPPERCASE and properly formatted."""
            
            response = execute_llm(fix_prompt)
            logging.info("Attempted to fix solution format")
        
        return response.strip()
        
    except Exception as e:
        logging.error(f"Error processing crossword: {e}")
        return ""

def _validate_solution_format(self, solution):
    """Basic validation of solution format"""
    if not solution:
        return False
    
    parts = solution.split('\n\n')
    if len(parts) < 3:
        return False
    
    # Check for Across and Down sections
    has_across = any('Across:' in part for part in parts)
    has_down = any('Down:' in part for part in parts)
    
    return has_across and has_down