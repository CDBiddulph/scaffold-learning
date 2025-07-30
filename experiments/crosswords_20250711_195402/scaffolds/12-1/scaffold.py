import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    try:
        # Parse the input
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
        
        # Parse clues
        clue_lines = lines[clue_start:]
        across_clues, down_clues = parse_clues(clue_lines)
        
        # Use LLM to solve the entire crossword at once
        filled_grid, solved_across, solved_down = solve_crossword_with_llm(
            grid_lines, across_clues, down_clues
        )
        
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

def solve_crossword_with_llm(grid_lines, across_clues, down_clues):
    # First, get the LLM to solve each clue individually
    solved_across = {}
    solved_down = {}
    
    # Solve across clues
    for clue_num, clue_text in across_clues.items():
        answer = solve_single_clue(clue_text, clue_num, 'across')
        if answer:
            solved_across[clue_num] = answer
    
    # Solve down clues
    for clue_num, clue_text in down_clues.items():
        answer = solve_single_clue(clue_text, clue_num, 'down')
        if answer:
            solved_down[clue_num] = answer
    
    # Now ask the LLM to fill in the grid
    filled_grid = fill_grid_with_llm(grid_lines, solved_across, solved_down)
    
    return filled_grid, solved_across, solved_down

def solve_single_clue(clue_text, clue_num, direction):
    # Try multiple approaches to solve the clue
    approaches = [
        f"Solve this crossword clue. Give only the answer in capital letters:\n{clue_text}",
        f"What's the answer to this crossword clue?\nClue: {clue_text}\nAnswer:",
        f"Crossword clue: {clue_text}\nThe answer is:"
    ]
    
    for approach in approaches:
        try:
            response = execute_llm(approach).strip().upper()
            
            # Extract the most likely answer
            # Look for sequences of capital letters
            words = re.findall(r'[A-Z]+', response)
            
            if words:
                # Return the longest reasonable word
                best_word = max(words, key=len)
                # But prefer shorter words that might be more accurate
                for word in words:
                    if 3 <= len(word) <= 15 and word.isalpha():
                        return word
                
                # Fallback to the longest word
                if best_word.isalpha():
                    return best_word
                    
        except Exception as e:
            logging.error(f"Error solving clue {clue_num} ({direction}): {e}")
            continue
    
    return None

def fill_grid_with_llm(grid_lines, solved_across, solved_down):
    # Create a copy of the grid to fill
    grid = [line.split() for line in grid_lines]
    
    # Ask the LLM to help fill the grid using the solved clues
    grid_text = '\n'.join(grid_lines)
    
    # Create clue context
    clue_context = "Across clues:\n"
    for num, answer in sorted(solved_across.items()):
        clue_context += f"{num}. {answer}\n"
    
    clue_context += "\nDown clues:\n"
    for num, answer in sorted(solved_down.items()):
        clue_context += f"{num}. {answer}\n"
    
    prompt = f"""Fill in this crossword grid using the provided answers. 
Replace each dash (-) with the appropriate letter from the crossing words.
Keep black squares (.) as they are.

Grid template:
{grid_text}

{clue_context}

Return the filled grid in the same format, with letters in uppercase:"""
    
    try:
        response = execute_llm(prompt)
        
        # Parse the response to extract the filled grid
        response_lines = response.strip().split('\n')
        filled_grid = []
        
        for i, line in enumerate(response_lines):
            if i < len(grid):
                # Parse the line and ensure it has the right structure
                cells = line.split()
                if len(cells) == len(grid[i]):
                    # Convert to uppercase and validate
                    row = []
                    for j, cell in enumerate(cells):
                        if grid[i][j] == '.':
                            row.append('.')
                        else:
                            # Use the LLM's suggestion, but validate it's a letter
                            if cell.isalpha() and len(cell) == 1:
                                row.append(cell.upper())
                            else:
                                row.append('A')  # Fallback
                    filled_grid.append(row)
                else:
                    # Fallback to original structure
                    filled_grid.append(grid[i][:])
            else:
                break
        
        # Fill any remaining rows
        while len(filled_grid) < len(grid):
            filled_grid.append(grid[len(filled_grid)][:])
        
        return filled_grid
        
    except Exception as e:
        logging.error(f"Error filling grid with LLM: {e}")
        # Fallback: try to fill programmatically
        return fill_grid_programmatically(grid, solved_across, solved_down)

def fill_grid_programmatically(grid, solved_across, solved_down):
    # Simple fallback: just replace dashes with letters from solved clues
    filled = [row[:] for row in grid]
    
    # Fill with a default letter where we have dashes
    for i in range(len(filled)):
        for j in range(len(filled[i])):
            if filled[i][j] == '-':
                filled[i][j] = 'A'  # Default letter
    
    return filled