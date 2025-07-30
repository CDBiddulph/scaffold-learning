import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    logging.info("Starting crossword puzzle processing")
    
    lines = input_string.strip().split('\n')
    
    # Parse the grid structure
    grid_lines = []
    clue_start = -1
    for i, line in enumerate(lines):
        if line.strip().startswith('Across:'):
            clue_start = i
            break
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
            match = re.match(r'\s*(\d+)\.\s*(.+)', line)
            if match:
                clue_num = int(match.group(1))
                clue_text = match.group(2).strip()
                if current_section == 'across':
                    across_clues[clue_num] = clue_text
                else:
                    down_clues[clue_num] = clue_text
    
    logging.info(f"Found {len(across_clues)} across clues and {len(down_clues)} down clues")
    
    # Parse grid to find clue positions and lengths
    def find_clue_info(clue_num, direction):
        """Find position and length of a clue in the grid"""
        grid = [line.split() for line in grid_lines]
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
                        # Found the clue, now determine length
                        if direction == 'across' and starts_across:
                            length = 0
                            for c in range(col, width):
                                if grid[row][c] == '.':
                                    break
                                length += 1
                            return (row, col), length
                        elif direction == 'down' and starts_down:
                            length = 0
                            for r in range(row, height):
                                if grid[r][col] == '.':
                                    break
                                length += 1
                            return (row, col), length
                    current_num += 1
        
        return None, None
    
    # Solve clues with length constraints
    solved_across = {}
    solved_down = {}
    
    # Process across clues
    for num, clue in across_clues.items():
        position, length = find_clue_info(num, 'across')
        if length is None:
            logging.warning(f"Could not find length for across clue {num}")
            continue
            
        clean_clue = clue.strip('"').strip("'")
        
        # Enhanced prompting with crossword-specific context
        prompt = f"""Solve this crossword clue. This is from a crossword puzzle, so think about common crossword conventions and wordplay.

Clue: {clean_clue}
Length: {length} letters

The answer must be exactly {length} letters long. Respond with ONLY the answer in uppercase letters, no spaces, no punctuation, no explanation."""
        
        try:
            response = execute_llm(prompt)
            answer = response.strip().upper().replace(' ', '').replace('-', '')
            
            # Validate answer length and format
            if len(answer) == length and answer.isalpha():
                solved_across[num] = answer
                logging.info(f"Solved across {num}: {answer} (length {length})")
            else:
                logging.warning(f"Invalid answer for across {num}: '{answer}' (expected length {length}, got {len(answer)})")
                
                # Try a second attempt with more specific prompting
                prompt2 = f"""This is a crossword clue. The answer is exactly {length} letters, no more, no less.
Think of the most common crossword answer for this clue.

Clue: {clean_clue}
Answer length: {length}

Give me just the {length}-letter answer in uppercase:"""
                
                try:
                    response2 = execute_llm(prompt2)
                    answer2 = response2.strip().upper().replace(' ', '').replace('-', '')
                    if len(answer2) == length and answer2.isalpha():
                        solved_across[num] = answer2
                        logging.info(f"Solved across {num} on second attempt: {answer2}")
                    else:
                        logging.warning(f"Second attempt also failed for across {num}")
                except Exception as e:
                    logging.warning(f"Second attempt failed for across {num}: {e}")
                    
        except Exception as e:
            logging.warning(f"Failed to solve across clue {num}: {e}")
    
    # Process down clues
    for num, clue in down_clues.items():
        position, length = find_clue_info(num, 'down')
        if length is None:
            logging.warning(f"Could not find length for down clue {num}")
            continue
            
        clean_clue = clue.strip('"').strip("'")
        
        prompt = f"""Solve this crossword clue. This is from a crossword puzzle, so think about common crossword conventions and wordplay.

Clue: {clean_clue}
Length: {length} letters

The answer must be exactly {length} letters long. Respond with ONLY the answer in uppercase letters, no spaces, no punctuation, no explanation."""
        
        try:
            response = execute_llm(prompt)
            answer = response.strip().upper().replace(' ', '').replace('-', '')
            
            # Validate answer length and format
            if len(answer) == length and answer.isalpha():
                solved_down[num] = answer
                logging.info(f"Solved down {num}: {answer} (length {length})")
            else:
                logging.warning(f"Invalid answer for down {num}: '{answer}' (expected length {length}, got {len(answer)})")
                
                # Try a second attempt
                prompt2 = f"""This is a crossword clue. The answer is exactly {length} letters, no more, no less.
Think of the most common crossword answer for this clue.

Clue: {clean_clue}
Answer length: {length}

Give me just the {length}-letter answer in uppercase:"""
                
                try:
                    response2 = execute_llm(prompt2)
                    answer2 = response2.strip().upper().replace(' ', '').replace('-', '')
                    if len(answer2) == length and answer2.isalpha():
                        solved_down[num] = answer2
                        logging.info(f"Solved down {num} on second attempt: {answer2}")
                    else:
                        logging.warning(f"Second attempt also failed for down {num}")
                except Exception as e:
                    logging.warning(f"Second attempt failed for down {num}: {e}")
                    
        except Exception as e:
            logging.warning(f"Failed to solve down clue {num}: {e}")
    
    # Create output format
    result = []
    
    if solved_across:
        result.append('Across:')
        for num in sorted(solved_across.keys()):
            result.append(f'  {num}. {solved_across[num]}')
        result.append('')
    
    if solved_down:
        result.append('Down:')
        for num in sorted(solved_down.keys()):
            result.append(f'  {num}. {solved_down[num]}')
    
    output = '\n'.join(result)
    logging.info(f"Generated output with {len(solved_across)} across and {len(solved_down)} down answers")
    
    return output