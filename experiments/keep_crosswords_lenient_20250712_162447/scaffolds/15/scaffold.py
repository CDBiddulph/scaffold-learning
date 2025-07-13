import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 110  # Leave buffer for processing
    
    try:
        lines = input_string.strip().split('\n')
        
        # Find where grid ends and clues begin
        grid_lines = []
        clue_start = 0
        
        for i, line in enumerate(lines):
            if line.strip().startswith('Across:'):
                clue_start = i
                break
            if line.strip():
                grid_lines.append(line.strip())
        
        clue_lines = lines[clue_start:]
        
        # Extract clues
        across_clues = []
        down_clues = []
        
        current_section = None
        for line in clue_lines:
            line = line.strip()
            if line.startswith('Across:'):
                current_section = 'across'
                continue
            elif line.startswith('Down:'):
                current_section = 'down'
                continue
            elif line and current_section:
                match = re.match(r'\s*(\d+)\.\s*(.+)', line)
                if match:
                    clue_num = int(match.group(1))
                    clue_text = match.group(2).strip()
                    if current_section == 'across':
                        across_clues.append((clue_num, clue_text))
                    else:
                        down_clues.append((clue_num, clue_text))
        
        # Solve clues with time management
        solved_across = {}
        solved_down = {}
        
        all_clues = [(num, text, 'across') for num, text in across_clues] + \
                   [(num, text, 'down') for num, text in down_clues]
        
        # Prioritize easier/shorter clues first by sorting by clue length
        all_clues.sort(key=lambda x: len(x[1]))
        
        time_per_clue = max(1.5, (timeout - (time.time() - start_time)) / len(all_clues)) if all_clues else 1.5
        
        for clue_num, clue_text, direction in all_clues:
            if time.time() - start_time > timeout:
                break
                
            answer = solve_clue_enhanced(clue_text, time_per_clue)
            if answer:
                if direction == 'across':
                    solved_across[clue_num] = answer
                else:
                    solved_down[clue_num] = answer
                    
                logging.info(f"Solved {direction} {clue_num}: '{clue_text}' -> '{answer}'")
        
        # Build output in expected format
        result = []
        
        # Add original grid (keeping the dash format since we're not filling it in)
        for line in grid_lines:
            result.append(line)
        
        result.append("")  # Double newline separator
        
        # Add solved Across clues
        if solved_across:
            result.append("Across:")
            for num in sorted(solved_across.keys()):
                result.append(f"  {num}. {solved_across[num]}")
            
            if solved_down:  # Only add separator if we have both sections
                result.append("")
        
        # Add solved Down clues
        if solved_down:
            result.append("Down:")
            for num in sorted(solved_down.keys()):
                result.append(f"  {num}. {solved_down[num]}")
        
        logging.info(f"Solved {len(solved_across)} across and {len(solved_down)} down clues")
        return '\n'.join(result)
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return ""

def solve_clue_enhanced(clue_text, time_limit):
    if time_limit < 0.5:
        return None
        
    try:
        # Enhanced prompt with examples and clear instructions
        prompt = f"""You are an expert crossword solver. I will give you a crossword clue and you need to provide the answer.

IMPORTANT RULES:
- Respond with ONLY the answer word(s) in uppercase
- No spaces, no punctuation, no explanations, no other text
- For multi-word answers, concatenate them (e.g., "New York" becomes "NEWYORK")
- Think about common crossword conventions (abbreviations, wordplay, etc.)

Examples:
Clue: "Feline pet" -> CAT
Clue: "Big Apple" -> NYC  
Clue: "Opposite of yes" -> NO

Clue: {clue_text}

Answer:"""
        
        response = execute_llm(prompt)
        
        # Extract the cleanest answer from response
        lines = response.strip().split('\n')
        for line in lines:
            answer = line.strip().upper()
            # Remove any non-letter characters
            answer = re.sub(r'[^A-Z]', '', answer)
            # Reasonable length check (most crossword answers are 2-15 letters)
            if answer and 2 <= len(answer) <= 15:
                return answer
        
        return None
    except Exception as e:
        logging.error(f"Error solving clue '{clue_text}': {e}")
        return None