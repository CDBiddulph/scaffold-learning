import logging
import re
from collections import Counter, defaultdict
from llm_executor import execute_llm

def parse_input(input_string: str):
    """Parse the input to extract grid and clues"""
    lines = input_string.strip().split('\n')
    
    # Find where the grid ends and clues begin
    grid_lines = []
    clues_start = 0
    
    for i, line in enumerate(lines):
        if line.strip().startswith('Across:'):
            clues_start = i
            break
        grid_lines.append(line)
    
    # Parse grid
    grid = []
    for line in grid_lines:
        if line.strip():
            grid.append(line.strip().split())
    
    # Parse clues
    across_clues = {}
    down_clues = {}
    
    current_section = None
    for i in range(clues_start, len(lines)):
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
    
    return grid, across_clues, down_clues

def get_word_length(grid, row, col, direction):
    """Get the length of a word starting at (row, col) in the given direction"""
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0
    
    length = 0
    if direction == 'across':
        for c in range(col, width):
            if grid[row][c] == '.':
                break
            length += 1
    else:  # down
        for r in range(row, height):
            if grid[r][col] == '.':
                break
            length += 1
    
    return length

def solve_clue_with_enhanced_prompting(clue_text, length, intersecting_letters=None, attempt_num=0):
    """Solve a clue with enhanced prompting strategies"""
    
    # Build pattern string
    pattern = ['_'] * length
    if intersecting_letters:
        for pos, letter in intersecting_letters.items():
            if 0 <= pos < length:
                pattern[pos] = letter
    
    pattern_str = ''.join(pattern)
    
    # Different prompting strategies for different attempts
    if attempt_num == 0:
        # Standard crossword approach
        prompt = f"""Solve this crossword clue:

"{clue_text}"

Answer length: {length} letters
Pattern: {pattern_str} (where _ means any letter)

Important crossword solving tips:
- Look for wordplay, puns, anagrams, hidden words
- Consider abbreviations and acronyms
- Think about double meanings
- "?" often indicates wordplay
- Common crossword answers are preferred

Give ONLY the answer in uppercase letters with no spaces."""

    elif attempt_num == 1:
        # More detailed analysis
        prompt = f"""Analyze this crossword clue step by step:

Clue: "{clue_text}"
Length: {length} letters
Pattern: {pattern_str}

Think about:
1. Is this a straight definition?
2. Is there wordplay involved?
3. Are there any abbreviations?
4. Could this be an anagram?
5. Are there any cultural references?

Based on your analysis, what is the most likely answer?
Respond with ONLY the answer in uppercase letters."""

    else:
        # Alternative interpretation
        prompt = f"""Consider alternative interpretations of this crossword clue:

"{clue_text}"

Length: {length} letters
Pattern: {pattern_str}

This clue might have a different meaning than expected. Consider:
- Less obvious definitions
- Archaic or technical terms
- Proper nouns
- Slang or informal language

What alternative answer fits?
Respond with ONLY the answer in uppercase letters."""
    
    try:
        response = execute_llm(prompt)
        answer = response.strip().upper()
        # Clean the answer - keep only letters
        answer = ''.join(c for c in answer if c.isalpha())
        
        # Validate length
        if len(answer) == length:
            return answer
            
    except Exception as e:
        logging.error(f"Error solving clue '{clue_text}': {e}")
    
    return None

def handle_cross_references(clue_text, clue_num, across_clues, down_clues):
    """Handle cross-references between clues"""
    # Look for patterns like "See 22-Across", "With 10-Down"
    see_match = re.search(r'See (\d+)-(Across|Down)', clue_text, re.IGNORECASE)
    with_match = re.search(r'With (\d+)-(Down|Across)', clue_text, re.IGNORECASE)
    
    if see_match:
        ref_num = int(see_match.group(1))
        ref_type = see_match.group(2).lower()
        
        # This clue is a continuation of another clue
        if ref_type == 'across' and ref_num in across_clues:
            base_clue = across_clues[ref_num]
            return f"{base_clue} (continued)"
        elif ref_type == 'down' and ref_num in down_clues:
            base_clue = down_clues[ref_num]
            return f"{base_clue} (continued)"
    
    if with_match:
        ref_num = int(with_match.group(1))
        ref_type = with_match.group(2).lower()
        
        # This clue combines with another to form a compound answer
        if ref_type == 'down' and ref_num in down_clues:
            other_clue = down_clues[ref_num]
            return f"Combined clue: {clue_text} + {other_clue}"
        elif ref_type == 'across' and ref_num in across_clues:
            other_clue = across_clues[ref_num]
            return f"Combined clue: {clue_text} + {other_clue}"
    
    return clue_text

def solve_crossword_strategically(grid, across_clues, down_clues):
    """Solve crossword with strategic approach"""
    
    # Find clue positions and lengths
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0
    
    across_info = {}  # clue_num -> (row, col, length)
    down_info = {}    # clue_num -> (row, col, length)
    current_num = 1
    
    for row in range(height):
        for col in range(width):
            if grid[row][col] == '.':
                continue
            
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
                if starts_across:
                    length = get_word_length(grid, row, col, 'across')
                    across_info[current_num] = (row, col, length)
                if starts_down:
                    length = get_word_length(grid, row, col, 'down')
                    down_info[current_num] = (row, col, length)
                current_num += 1
    
    # Initialize grid
    filled_grid = [row[:] for row in grid]
    for row in range(height):
        for col in range(width):
            if filled_grid[row][col] == '-':
                filled_grid[row][col] = ' '
    
    solved_across = {}
    solved_down = {}
    
    # Create intersection mapping
    intersections = defaultdict(list)
    for across_num, (row, col, length) in across_info.items():
        for i in range(length):
            pos = (row, col + i)
            intersections[pos].append(('across', across_num, i))
    
    for down_num, (row, col, length) in down_info.items():
        for i in range(length):
            pos = (row + i, col)
            intersections[pos].append(('down', down_num, i))
    
    # Strategic solving: prioritize clues with more constraints
    def get_constraint_count(clue_num, direction):
        if direction == 'across' and clue_num in across_info:
            row, col, length = across_info[clue_num]
            count = 0
            for i in range(length):
                if filled_grid[row][col + i] != ' ':
                    count += 1
            return count
        elif direction == 'down' and clue_num in down_info:
            row, col, length = down_info[clue_num]
            count = 0
            for i in range(length):
                if filled_grid[row + i][col] != ' ':
                    count += 1
            return count
        return 0
    
    # Multiple solving passes
    for pass_num in range(4):
        logging.info(f"Strategic pass {pass_num + 1}")
        
        # Solve across clues
        across_to_solve = [(num, clue) for num, clue in across_clues.items() 
                          if num not in solved_across and num in across_info]
        
        # Sort by constraint count (more constraints = higher priority)
        across_to_solve.sort(key=lambda x: get_constraint_count(x[0], 'across'), reverse=True)
        
        for clue_num, clue_text in across_to_solve:
            row, col, length = across_info[clue_num]
            
            # Handle cross-references
            processed_clue = handle_cross_references(clue_text, clue_num, across_clues, down_clues)
            
            # Get intersecting letters
            intersecting_letters = {}
            for i in range(length):
                if col + i < width and filled_grid[row][col + i] != ' ':
                    intersecting_letters[i] = filled_grid[row][col + i]
            
            # Try multiple approaches
            answer = None
            for attempt in range(3):
                answer = solve_clue_with_enhanced_prompting(processed_clue, length, intersecting_letters, attempt)
                if answer:
                    break
            
            if answer:
                solved_across[clue_num] = answer
                # Fill in the grid
                for i, letter in enumerate(answer):
                    if col + i < width:
                        filled_grid[row][col + i] = letter
                logging.info(f"Solved {clue_num} across: {answer}")
        
        # Solve down clues
        down_to_solve = [(num, clue) for num, clue in down_clues.items() 
                        if num not in solved_down and num in down_info]
        
        # Sort by constraint count
        down_to_solve.sort(key=lambda x: get_constraint_count(x[0], 'down'), reverse=True)
        
        for clue_num, clue_text in down_to_solve:
            row, col, length = down_info[clue_num]
            
            # Handle cross-references
            processed_clue = handle_cross_references(clue_text, clue_num, across_clues, down_clues)
            
            # Get intersecting letters
            intersecting_letters = {}
            for i in range(length):
                if row + i < height and filled_grid[row + i][col] != ' ':
                    intersecting_letters[i] = filled_grid[row + i][col]
            
            # Try multiple approaches
            answer = None
            for attempt in range(3):
                answer = solve_clue_with_enhanced_prompting(processed_clue, length, intersecting_letters, attempt)
                if answer:
                    break
            
            if answer:
                solved_down[clue_num] = answer
                # Fill in the grid
                for i, letter in enumerate(answer):
                    if row + i < height:
                        filled_grid[row + i][col] = letter
                logging.info(f"Solved {clue_num} down: {answer}")
    
    return filled_grid, solved_across, solved_down

def format_output(filled_grid, solved_across, solved_down):
    """Format the output as expected"""
    result = []
    
    # Add grid
    for row in filled_grid:
        result.append(' '.join(row))
    
    result.append('')  # Empty line
    
    # Add across clues
    result.append('Across:')
    for clue_num in sorted(solved_across.keys()):
        result.append(f'  {clue_num}. {solved_across[clue_num]}')
    
    result.append('')  # Empty line
    
    # Add down clues
    result.append('Down:')
    for clue_num in sorted(solved_down.keys()):
        result.append(f'  {clue_num}. {solved_down[clue_num]}')
    
    return '\n'.join(result)

def process_input(input_string: str) -> str:
    try:
        logging.info("Starting strategic crossword puzzle solution")
        grid, across_clues, down_clues = parse_input(input_string)
        logging.info(f"Parsed grid: {len(grid)}x{len(grid[0]) if grid else 0}")
        logging.info(f"Across clues: {len(across_clues)}, Down clues: {len(down_clues)}")
        
        filled_grid, solved_across, solved_down = solve_crossword_strategically(grid, across_clues, down_clues)
        logging.info(f"Solved {len(solved_across)} across clues and {len(solved_down)} down clues")
        
        result = format_output(filled_grid, solved_across, solved_down)
        return result
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return ""