import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    try:
        # First attempt: Ask LLM to solve the entire crossword at once with better guidance
        prompt = f"""You are an expert crossword puzzle solver. Please solve this crossword puzzle completely.

{input_string}

Critical crossword conventions:
- "In brief" always means an abbreviation or acronym
- Question marks indicate wordplay or puns
- Answers must be common crossword words, not just related terms
- Pay attention to exact wording - "competitor" vs "rival" matters
- Short answers are often abbreviations or common short words

Provide your solution in this exact format:
Across:
  1. ANSWER
  5. ANSWER
  etc.

Down:
  1. ANSWER
  2. ANSWER
  etc.

Be very precise - crossword answers have exact spellings."""
        
        response = execute_llm(prompt)
        
        # Check if response looks reasonable
        if ("Across:" in response and "Down:" in response and 
            len(response.strip()) > 100):
            return response.strip()
        
        # If that fails, try fallback approach
        logging.warning("Primary solve failed, trying fallback")
        return fallback_solve(input_string)
        
    except Exception as e:
        logging.error(f"Error in primary solve: {e}")
        return fallback_solve(input_string)

def fallback_solve(input_string: str) -> str:
    """Fallback: solve clues individually then construct answer"""
    try:
        # Parse the input to extract clues
        lines = input_string.strip().split('\n')
        across_clues = {}
        down_clues = {}
        
        current_section = None
        for line in lines:
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
        
        # Solve clues with improved approach
        solved_across = solve_clues_improved(across_clues, "ACROSS")
        solved_down = solve_clues_improved(down_clues, "DOWN")
        
        # Format the response
        result = []
        result.append("Across:")
        for num in sorted(solved_across.keys()):
            result.append(f"  {num}. {solved_across[num]}")
        result.append("")
        result.append("Down:")
        for num in sorted(solved_down.keys()):
            result.append(f"  {num}. {solved_down[num]}")
        
        return '\n'.join(result)
        
    except Exception as e:
        logging.error(f"Fallback solve failed: {e}")
        return ""

def solve_clues_improved(clues, direction):
    """Solve clues with improved prompting and error handling"""
    solved = {}
    
    # Process clues in smaller batches for better accuracy
    clue_items = list(clues.items())
    batch_size = 5
    
    for i in range(0, len(clue_items), batch_size):
        batch = clue_items[i:i+batch_size]
        
        prompt = f"""You are an expert crossword puzzle solver. Solve these {direction} crossword clues.

CRITICAL CROSSWORD RULES:
- "In brief" = abbreviation (AMEX not MC, NGO not CHARITY)
- "Kind of" = specific type (NEAP tide not RIPTIDE)
- Exact wording matters - give the precise crossword answer
- Common crossword words preferred over general terms
- Think of typical crossword vocabulary

{direction} CLUES:
"""
        for idx, (clue_num, clue_text) in enumerate(batch, 1):
            prompt += f"{idx}. {clue_text}\n"
        
        prompt += f"\nProvide exactly {len(batch)} answers, one per line, in CAPITAL LETTERS only:"
        
        try:
            response = execute_llm(prompt)
            lines = [line.strip() for line in response.split('\n') if line.strip()]
            
            # Extract clean answers
            answers = []
            for line in lines:
                # Remove numbering if present
                clean_line = re.sub(r'^\d+\.\s*', '', line)
                # Keep only letters and convert to uppercase
                answer = ''.join(c for c in clean_line if c.isalpha()).upper()
                if answer and len(answer) > 1:  # Filter out single letters
                    answers.append(answer)
            
            # Match answers back to clue numbers
            for j, (clue_num, clue_text) in enumerate(batch):
                if j < len(answers):
                    # Additional validation for common patterns
                    answer = validate_answer(clue_text, answers[j])
                    solved[clue_num] = answer
                    logging.info(f"Solved {direction} {clue_num}: {answer}")
                else:
                    # Try individual solve if batch failed
                    answer = solve_single_clue_improved(clue_text, clue_num)
                    if answer:
                        solved[clue_num] = answer
                        logging.info(f"Individually solved {direction} {clue_num}: {answer}")
                    
        except Exception as e:
            logging.error(f"Failed to solve {direction} batch {i//batch_size + 1}: {e}")
            
            # Try individual clues if batch fails
            for clue_num, clue_text in batch:
                try:
                    answer = solve_single_clue_improved(clue_text, clue_num)
                    if answer:
                        solved[clue_num] = answer
                        logging.info(f"Individually solved {direction} {clue_num}: {answer}")
                except Exception as e2:
                    logging.error(f"Failed to solve individual clue {clue_num}: {e2}")
    
    return solved

def validate_answer(clue_text, answer):
    """Apply crossword-specific validation rules"""
    clue_lower = clue_text.lower()
    
    # Common crossword patterns
    if "in brief" in clue_lower:
        # Should be abbreviation - prefer shorter answers
        if len(answer) > 4:
            # Try to get a shorter version
            short_answer = get_abbreviation(clue_text)
            if short_answer:
                return short_answer
    
    return answer

def get_abbreviation(clue_text):
    """Try to get proper abbreviation for clues with 'in brief'"""
    prompt = f"""This crossword clue needs an abbreviation answer:
"{clue_text}"

What is the standard abbreviation? Give only the abbreviation in CAPITAL LETTERS."""
    
    try:
        response = execute_llm(prompt)
        abbrev = ''.join(c for c in response.strip() if c.isalpha()).upper()
        if abbrev and len(abbrev) <= 5:
            return abbrev
    except:
        pass
    return None

def solve_single_clue_improved(clue_text, clue_num):
    """Solve a single crossword clue with improved prompting"""
    prompt = f"""You are an expert crossword puzzle solver. Solve this crossword clue.

Clue: "{clue_text}"

Think step by step:
1. What type of clue is this? (definition, wordplay, abbreviation, etc.)
2. What is the most common crossword answer for this type of clue?
3. Consider exact wording - crossword answers are precise

Give only the answer word in CAPITAL LETTERS."""
    
    try:
        response = execute_llm(prompt)
        answer = ''.join(c for c in response.strip() if c.isalpha()).upper()
        if answer and len(answer) > 1:
            return answer
    except Exception as e:
        logging.error(f"Failed to solve single clue: {e}")
    return None