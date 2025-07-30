import logging
import time
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 110  # Leave buffer for timeout
    
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
            if line.strip() and not line.strip().startswith('Across:') and not line.strip().startswith('Down:'):
                grid_lines.append(line.strip())
        
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
                # Parse clue
                match = re.match(r'\s*(\d+)\.\s*(.+)', line)
                if match:
                    clue_num = int(match.group(1))
                    clue_text = match.group(2).strip()
                    if current_section == 'across':
                        across_clues[clue_num] = clue_text
                    else:
                        down_clues[clue_num] = clue_text
        
        logging.info(f"Parsed {len(grid_lines)} grid lines, {len(across_clues)} across clues, {len(down_clues)} down clues")
        
        # Check timeout
        if time.time() - start_time > timeout:
            logging.warning("Timeout approaching during parsing")
            return ""
        
        # Create comprehensive puzzle prompt
        puzzle_prompt = f"""You are an expert crossword puzzle solver. Solve this crossword puzzle completely and accurately.

Grid structure (- represents empty squares to fill with letters, . represents black squares):
{chr(10).join(grid_lines)}

Across clues:
{chr(10).join(f"{num}. {clue}" for num, clue in sorted(across_clues.items()))}

Down clues:
{chr(10).join(f"{num}. {clue}" for num, clue in sorted(down_clues.items()))}

Important: Return the solution in this EXACT format with proper spacing and formatting:

[Complete grid with all letters filled in, replacing - with letters, keeping . as is]

Across:
  1. [ANSWER]
  4. [ANSWER]
  8. [ANSWER]
  [Continue for ALL across clues in numerical order]

Down:
  1. [ANSWER]
  2. [ANSWER]
  3. [ANSWER]
  [Continue for ALL down clues in numerical order]

Requirements:
- Use only CAPITAL letters
- Make sure answers fit the grid structure and cross correctly
- Include answers for ALL clue numbers provided
- Maintain exact spacing format with two spaces before each clue number
- Separate grid from clues with blank lines"""
        
        # Check timeout before LLM call
        if time.time() - start_time > timeout:
            logging.warning("Timeout approaching before LLM call")
            return ""
        
        response = execute_llm(puzzle_prompt)
        
        # Clean up response
        response = response.strip()
        
        logging.info(f"LLM response received, length: {len(response)}")
        
        # Try to format the response properly if needed
        if response and not response.endswith('\n'):
            response += '\n'
        
        return response
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return ""

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 110
    
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
            if line.strip() and not line.strip().startswith('Across:') and not line.strip().startswith('Down:'):
                grid_lines.append(line.strip())
        
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
                # Parse clue
                match = re.match(r'\s*(\d+)\.\s*(.+)', line)
                if match:
                    clue_num = int(match.group(1))
                    clue_text = match.group(2).strip()
                    if current_section == 'across':
                        across_clues[clue_num] = clue_text
                    else:
                        down_clues[clue_num] = clue_text
        
        logging.info(f"Parsed {len(grid_lines)} grid lines, {len(across_clues)} across clues, {len(down_clues)} down clues")
        
        # Check timeout
        if time.time() - start_time > timeout:
            return ""
        
        # Solve the puzzle
        puzzle_prompt = f"""You are solving a crossword puzzle. Please solve it completely and accurately.

Grid (- = empty square, . = black square):
{chr(10).join(grid_lines)}

Across clues:
{chr(10).join(f"{num}. {clue}" for num, clue in sorted(across_clues.items()))}

Down clues:
{chr(10).join(f"{num}. {clue}" for num, clue in sorted(down_clues.items()))}

Provide the complete solution in this exact format:

[Grid with letters filled in]

Across:
  1. [ANSWER]
  4. [ANSWER]
  [etc for all across clues]

Down:
  1. [ANSWER]
  2. [ANSWER]
  [etc for all down clues]

Use only capital letters. Make sure grid and answers are consistent."""
        
        if time.time() - start_time > timeout:
            return ""
        
        response = execute_llm(puzzle_prompt)
        return response.strip()
        
    except Exception as e:
        logging.error(f"Error: {e}")
        return ""