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
        
        # Solve the crossword puzzle
        solution = solve_crossword(grid_lines, clue_lines)
        
        return solution
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return ""

def solve_crossword(grid_lines, clue_lines):
    """Solve the crossword puzzle using the LLM"""
    
    # Format the puzzle for the LLM
    grid_str = '\n'.join(grid_lines)
    clues_str = '\n'.join(clue_lines)
    
    # First, let's get the individual clue answers
    across_answers, down_answers = get_clue_answers(clue_lines)
    
    # Now use the LLM to fill in the grid
    prompt = f"""
Fill in this crossword grid using the provided answers.

Grid pattern (- represents empty squares to fill, . represents black squares):
{grid_str}

Across answers:
{format_answers(across_answers)}

Down answers:
{format_answers(down_answers)}

Instructions:
1. Replace each dash (-) with the correct letter
2. Keep black squares (.) as periods
3. Use standard crossword numbering (numbers go in squares that start new words)
4. Make sure across and down answers intersect correctly

Provide the solution in this exact format:
[SOLVED GRID - letters replacing dashes, periods staying as periods]

Across:
[numbered list of across answers]

Down:
[numbered list of down answers]
"""
    
    try:
        response = execute_llm(prompt)
        return response.strip()
    except Exception as e:
        logging.error(f"Error calling LLM to solve crossword: {e}")
        return ""

def get_clue_answers(clue_lines):
    """Get answers for individual clues"""
    across_clues = {}
    down_clues = {}
    current_section = None
    
    # Parse clues
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
                clue_text = match.group(2)
                if current_section == 'across':
                    across_clues[clue_num] = clue_text
                else:
                    down_clues[clue_num] = clue_text
    
    logging.info(f"Parsed {len(across_clues)} across clues and {len(down_clues)} down clues")
    
    # Solve clues in batches to be more efficient
    across_answers = solve_clue_batch(across_clues, "across")
    down_answers = solve_clue_batch(down_clues, "down")
    
    return across_answers, down_answers

def solve_clue_batch(clues, direction):
    """Solve multiple clues at once"""
    if not clues:
        return {}
    
    # Format clues for batch solving
    clue_list = []
    for num, clue_text in sorted(clues.items()):
        clue_list.append(f"{num}. {clue_text}")
    
    clues_str = '\n'.join(clue_list)
    
    prompt = f"""
Solve these crossword clues. Respond with ONLY the answers in the same format, one per line.
Use all caps for answers. Do not include explanations.

{direction.title()} clues:
{clues_str}

Answers:"""
    
    try:
        response = execute_llm(prompt)
        
        # Parse the response
        answers = {}
        for line in response.strip().split('\n'):
            line = line.strip()
            if line:
                match = re.match(r'(\d+)\.\s*(.+)', line)
                if match:
                    num = int(match.group(1))
                    answer = match.group(2).strip().upper()
                    answers[num] = answer
                else:
                    # Try to match just the answer without number
                    parts = line.split()
                    if parts:
                        # Find the corresponding clue number
                        for clue_num in sorted(clues.keys()):
                            if clue_num not in answers:
                                answers[clue_num] = parts[0].upper()
                                break
        
        logging.info(f"Solved {len(answers)} {direction} clues")
        return answers
        
    except Exception as e:
        logging.error(f"Error solving {direction} clues: {e}")
        return {}

def format_answers(answers):
    """Format answers for display"""
    if not answers:
        return ""
    
    result = []
    for num in sorted(answers.keys()):
        result.append(f"{num}. {answers[num]}")
    
    return '\n'.join(result)