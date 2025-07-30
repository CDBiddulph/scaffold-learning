import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    try:
        # Parse the input crossword
        lines = input_string.strip().split('\n')
        
        # Find where grid ends and clues begin
        grid_lines = []
        clue_start = -1
        
        for i, line in enumerate(lines):
            if line.strip().startswith('Across:'):
                clue_start = i
                break
            grid_lines.append(line)
        
        if clue_start == -1:
            logging.error("Could not find 'Across:' section")
            return input_string
        
        # Parse the grid with validation
        grid = []
        for line in grid_lines:
            if line.strip():  # Skip empty lines
                grid.append(line.split())
        
        if not grid:
            logging.error("No grid found")
            return input_string
        
        # Validate grid dimensions
        width = len(grid[0])
        for i, row in enumerate(grid):
            if len(row) != width:
                logging.error(f"Row {i} has {len(row)} elements, expected {width}")
                return input_string
        
        height = len(grid)
        logging.info(f"Grid dimensions: {height}x{width}")
        
        # Parse clues
        clue_lines = lines[clue_start:]
        across_clues, down_clues = parse_clues(clue_lines)
        
        logging.info(f"Found {len(across_clues)} across clues and {len(down_clues)} down clues")
        
        # Solve clues using LLM
        solved_across = solve_clues(across_clues, grid, 'across')
        solved_down = solve_clues(down_clues, grid, 'down')
        
        logging.info(f"Solved {len(solved_across)} across clues and {len(solved_down)} down clues")
        
        # Fill the grid with solutions
        filled_grid = fill_grid(grid, solved_across, solved_down)
        
        # Format output
        result = []
        for row in filled_grid:
            result.append(' '.join(row))
        
        result.append('')
        result.append('Across:')
        for clue_num in sorted(solved_across.keys()):
            result.append(f'  {clue_num}. {solved_across[clue_num]}')
        
        result.append('')
        result.append('Down:')
        for clue_num in sorted(solved_down.keys()):
            result.append(f'  {clue_num}. {solved_down[clue_num]}')
        
        return '\n'.join(result)
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return input_string

def parse_clues(clue_lines):
    across_clues = {}
    down_clues = {}
    current_section = None
    
    for line in clue_lines:
        line = line.strip()
        if line.startswith('Across:'):
            current_section = 'across'
        elif line.startswith('Down:'):
            current_section = 'down'
        elif line and current_section:
            match = re.match(r'\s*(\d+)\.\s*(.+)', line)
            if match:
                clue_num = int(match.group(1))
                clue_text = match.group(2).strip()
                if current_section == 'across':
                    across_clues[clue_num] = clue_text
                else:
                    down_clues[clue_num] = clue_text
    
    return across_clues, down_clues

def solve_clues(clues, grid, direction):
    solved = {}
    
    for clue_num, clue_text in clues.items():
        try:
            # Get the length of the answer
            length = get_clue_length(clue_num, grid, direction)
            if length == 0:
                logging.warning(f"Could not determine length for {direction} clue {clue_num}")
                continue
                
            # Solve the clue
            answer = solve_single_clue(clue_text, length)
            if answer:
                solved[clue_num] = answer
                logging.info(f"Solved {direction} clue {clue_num}: {answer}")
            else:
                logging.warning(f"Could not solve {direction} clue {clue_num}: {clue_text}")
                
        except Exception as e:
            logging.error(f"Failed to solve {direction} clue {clue_num}: {e}")
            continue
    
    return solved

def solve_single_clue(clue_text, length):
    # Try multiple approaches to get the right answer
    
    # First approach: specific crossword prompt
    prompt1 = f"""This is a crossword puzzle clue. Solve it carefully.

Clue: "{clue_text}"
Answer length: {length} letters

Crossword solving tips:
- Think about wordplay, puns, abbreviations
- "Greetings, everybody!" could be "HI ALL" which becomes HIALL
- Consider multiple meanings of words
- Look for anagrams or wordplay
- The answer must be exactly {length} letters long

Respond with ONLY the {length}-letter answer in capital letters, nothing else."""
    
    try:
        response1 = execute_llm(prompt1).strip().upper()
        words1 = re.findall(r'[A-Z]+', response1)
        
        # Find word of correct length
        for word in words1:
            if len(word) == length and word.isalpha():
                return word
        
        # Second approach: ask for multiple possibilities
        prompt2 = f"""Give me 3 possible answers to this crossword clue:

Clue: "{clue_text}"
Length: {length} letters

Think about:
- Literal meanings
- Wordplay and puns
- Common crossword answers
- Abbreviations

Format: Just list 3 words, each exactly {length} letters long."""
        
        response2 = execute_llm(prompt2).strip().upper()
        words2 = re.findall(r'[A-Z]+', response2)
        
        # Find word of correct length
        for word in words2:
            if len(word) == length and word.isalpha():
                return word
        
        # Third approach: ask for explanation
        prompt3 = f"""Solve this crossword clue step by step:

Clue: "{clue_text}"
Length: {length} letters

1. What could this clue mean literally?
2. What wordplay might be involved?
3. What is your best answer?

Give your final answer as: ANSWER: [your answer]"""
        
        response3 = execute_llm(prompt3).strip().upper()
        
        # Look for ANSWER: pattern
        answer_match = re.search(r'ANSWER:\s*([A-Z]+)', response3)
        if answer_match:
            answer = answer_match.group(1)
            if len(answer) == length and answer.isalpha():
                return answer
        
        # Extract all words from response3
        words3 = re.findall(r'[A-Z]+', response3)
        for word in words3:
            if len(word) == length and word.isalpha():
                return word
        
        # If still no match, return first reasonable word, truncated/padded
        all_words = words1 + words2 + words3
        for word in all_words:
            if word.isalpha() and len(word) > 0:
                if len(word) >= length:
                    return word[:length]
                else:
                    # Pad with X's if too short (last resort)
                    return word + 'X' * (length - len(word))
                
        return None
        
    except Exception as e:
        logging.error(f"Error solving clue '{clue_text}': {e}")
        return None

def get_clue_length(clue_num, grid, direction):
    try:
        pos = find_clue_position(clue_num, grid)
        if pos is None:
            return 0
        
        row, col = pos
        height = len(grid)
        width = len(grid[0]) if height > 0 else 0
        
        if direction == 'across':
            length = 0
            for c in range(col, width):
                if grid[row][c] == '.':
                    break
                length += 1
            return length
        else:  # down
            length = 0
            for r in range(row, height):
                if grid[r][col] == '.':
                    break
                length += 1
            return length
    except Exception as e:
        logging.error(f"Error getting length for clue {clue_num}: {e}")
        return 0

def find_clue_position(clue_num, grid):
    try:
        height = len(grid)
        width = len(grid[0]) if height > 0 else 0
        current_num = 1
        
        for row in range(height):
            for col in range(width):
                if grid[row][col] == '.':
                    continue
                
                # Check if this position starts a word
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
                    if current_num == clue_num:
                        return (row, col)
                    current_num += 1
        
        return None
    except Exception as e:
        logging.error(f"Error finding position for clue {clue_num}: {e}")
        return None

def fill_grid(grid, solved_across, solved_down):
    try:
        height = len(grid)
        width = len(grid[0]) if height > 0 else 0
        
        # Create filled grid
        filled = [row[:] for row in grid]
        
        # Fill across answers
        for clue_num, answer in solved_across.items():
            pos = find_clue_position(clue_num, grid)
            if pos is None:
                continue
            
            row, col = pos
            for i, letter in enumerate(answer):
                if col + i < width and grid[row][col + i] != '.':
                    filled[row][col + i] = letter
        
        # Fill down answers (may override across if conflicting)
        for clue_num, answer in solved_down.items():
            pos = find_clue_position(clue_num, grid)
            if pos is None:
                continue
            
            row, col = pos
            for i, letter in enumerate(answer):
                if row + i < height and grid[row + i][col] != '.':
                    filled[row + i][col] = letter
        
        return filled
    except Exception as e:
        logging.error(f"Error filling grid: {e}")
        return grid