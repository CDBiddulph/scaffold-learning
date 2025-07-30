import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    try:
        # Parse the input
        lines = input_string.strip().split('\n')
        
        # Extract grid
        grid_lines = []
        i = 0
        while i < len(lines) and not lines[i].strip().startswith('Across:'):
            if lines[i].strip():
                grid_lines.append(lines[i].strip())
            i += 1
        
        # Parse clues
        across_clues = {}
        down_clues = {}
        
        current_section = None
        for line in lines[i:]:
            line = line.strip()
            if line.startswith('Across:'):
                current_section = 'across'
            elif line.startswith('Down:'):
                current_section = 'down'
            elif line and current_section:
                match = re.match(r'\s*(\d+)\.\s*(.+)', line)
                if match:
                    num = int(match.group(1))
                    clue = match.group(2).strip()
                    if current_section == 'across':
                        across_clues[num] = clue
                    else:
                        down_clues[num] = clue
        
        # Create grid structure
        grid = []
        for line in grid_lines:
            grid.append(line.split())
        
        height = len(grid)
        width = len(grid[0]) if height > 0 else 0
        
        # Analyze grid to find clue positions and lengths
        clue_info = analyze_grid(grid)
        
        # Solve clues with length constraints
        across_answers = {}
        down_answers = {}
        
        for num, clue in across_clues.items():
            if num in clue_info['across']:
                length = clue_info['across'][num]['length']
                answer = solve_clue_with_length(clue, length)
                across_answers[num] = answer
                logging.info(f"Across {num}: {clue} -> {answer} (length {length})")
        
        for num, clue in down_clues.items():
            if num in clue_info['down']:
                length = clue_info['down'][num]['length']
                answer = solve_clue_with_length(clue, length)
                down_answers[num] = answer
                logging.info(f"Down {num}: {clue} -> {answer} (length {length})")
        
        # Fill the grid
        filled_grid = fill_grid(grid, clue_info, across_answers, down_answers)
        
        # Format output
        output_lines = []
        
        # Grid section
        for row in filled_grid:
            output_lines.append(' '.join(row))
        
        output_lines.append('')
        output_lines.append('Across:')
        for num in sorted(across_answers.keys()):
            output_lines.append(f'  {num}. {across_answers[num]}')
        
        output_lines.append('')
        output_lines.append('Down:')
        for num in sorted(down_answers.keys()):
            output_lines.append(f'  {num}. {down_answers[num]}')
        
        return '\n'.join(output_lines)
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return ""

def analyze_grid(grid):
    """Analyze the grid to find clue positions and lengths"""
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0
    
    clue_info = {'across': {}, 'down': {}}
    current_num = 1
    
    for row in range(height):
        for col in range(width):
            # Skip black squares
            if grid[row][col] == ".":
                continue
            
            # Check if this position starts a word
            starts_across = (
                (col == 0 or grid[row][col - 1] == ".")
                and col + 1 < width
                and grid[row][col + 1] != "."
            )
            starts_down = (
                (row == 0 or grid[row - 1][col] == ".")
                and row + 1 < height
                and grid[row + 1][col] != "."
            )
            
            if starts_across or starts_down:
                if starts_across:
                    # Calculate length of across word
                    length = 0
                    for c in range(col, width):
                        if grid[row][c] == ".":
                            break
                        length += 1
                    clue_info['across'][current_num] = {
                        'position': (row, col),
                        'length': length
                    }
                
                if starts_down:
                    # Calculate length of down word
                    length = 0
                    for r in range(row, height):
                        if grid[r][col] == ".":
                            break
                        length += 1
                    clue_info['down'][current_num] = {
                        'position': (row, col),
                        'length': length
                    }
                
                current_num += 1
    
    return clue_info

def solve_clue_with_length(clue, length):
    """Solve a crossword clue with known length"""
    prompt = f"""Solve this crossword clue. The answer should be exactly {length} letters long.
    Respond with just the answer in capital letters, no explanation.
    
    Clue: {clue}
    Length: {length} letters
    """
    
    try:
        response = execute_llm(prompt)
        answer = response.strip().upper()
        
        # Remove any non-letter characters and ensure correct length
        answer = ''.join(c for c in answer if c.isalpha())
        
        if len(answer) == length:
            return answer
        else:
            # Try again with more specific prompt
            prompt2 = f"""The crossword clue "{clue}" needs an answer that is exactly {length} letters.
            Please provide only the answer, no explanation. Use capital letters only.
            
            Answer must be exactly {length} letters long.
            """
            response2 = execute_llm(prompt2)
            answer2 = ''.join(c for c in response2.strip().upper() if c.isalpha())
            
            if len(answer2) == length:
                return answer2
            else:
                # Fill with placeholder if can't get right length
                return 'A' * length
                
    except Exception as e:
        logging.error(f"Error solving clue '{clue}': {e}")
        return 'A' * length

def fill_grid(grid, clue_info, across_answers, down_answers):
    """Fill the grid with the solved answers"""
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0
    
    # Create filled grid
    filled_grid = [row[:] for row in grid]
    
    # Fill across answers
    for num, answer in across_answers.items():
        if num in clue_info['across']:
            row, col = clue_info['across'][num]['position']
            for i, letter in enumerate(answer):
                if col + i < width:
                    filled_grid[row][col + i] = letter
    
    # Fill down answers
    for num, answer in down_answers.items():
        if num in clue_info['down']:
            row, col = clue_info['down'][num]['position']
            for i, letter in enumerate(answer):
                if row + i < height:
                    filled_grid[row + i][col] = letter
    
    return filled_grid