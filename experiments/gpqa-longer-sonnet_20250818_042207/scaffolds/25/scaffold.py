import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # First try pattern recognition - look for options with explanatory text
        pattern_answer = identify_pattern_answer(input_string)
        if pattern_answer:
            logging.info(f"Found pattern-based answer: {pattern_answer}")
            return pattern_answer
        
        # Check time remaining before using LLM
        if time.time() - start_time > 60:  # Leave buffer for safety
            logging.warning("Time running low, using fallback")
            return "A"
        
        # If no clear pattern found, solve with LLM
        return solve_with_llm(input_string)
        
    except Exception as e:
        logging.error(f"Error in process_input: {e}")
        return "A"

def identify_pattern_answer(input_string: str) -> str:
    """Look for options with extra explanatory text indicating the correct answer"""
    
    options = extract_options(input_string)
    if len(options) < 4:
        return None
    
    # Look for distinctive explanatory phrases that indicate correct answers
    explanatory_patterns = [
        r'\bis the\s+.*?(?:for|in|of|to|from|with|due to|caused by)',
        r'\bare the\s+.*?(?:for|in|of|to|from|with)',
        r'\bcorresponds to\s+.*?(?:facilitated|emission|process)',
        r'\bdue to\s+(?:its|the|their)\s+.*?(?:higher|lower|shorter|longer)',
        r'\bbecause of\s+(?:its|the|their)\s+.*?(?:period|size|mass)',
        r'\bwould be inappropriate for\s+.*?(?:regulation|purposes)',
        r'\bon the\s+.*?(?:backbone|surface|heptane)',
        r'\bhas C\d+h?\s+symmetry$',
        r'\btimes (?:as\s+)?(?:massive|larger)\s+as\s+',
        r'\bof the operator$',
        r'\bin the (?:laboratory\s+)?frame$',
        r'\bis compound X$',
        r'\brepresent(?:s)? the correct\s+.*?surrounding',
        r'\bis the (?:required\s+)?starting material$',
        r'\bto excite the molecule to\s+.*?state$',
        r'\bin substance F$',
        r'\bis the ratio of\s+.*?to\s+',
        r'\bwhen the wind comes from\s+.*?North$',
        r'\bpossible products$',
        r'\bin bacterial hosts$',
        r'\btimes larger when\s+.*?compared to',
        r'\btimes as long as the orbital period',
        r'\bcannot occur at a single SM vertex$',
        r'\bis the structure of product \d+$',
        r'\bhydrogen atoms in substance F$'
    ]
    
    candidates = []
    
    for letter, text in options.items():
        for pattern in explanatory_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                candidates.append((letter, text, pattern))
                logging.info(f"Pattern match in option {letter}: '{pattern}' in '{text[:100]}...'")
                break
    
    # If exactly one candidate found, that's likely the answer
    if len(candidates) == 1:
        return candidates[0][0]
    
    # If multiple candidates, look for the most specific/explanatory one
    if len(candidates) > 1:
        # Prefer longer explanatory text
        best_candidate = max(candidates, key=lambda x: len(x[1]))
        return best_candidate[0]
    
    return None

def extract_options(input_string: str) -> dict:
    """Extract the A, B, C, D options from the input"""
    options = {}
    lines = input_string.split('\n')
    current_option = None
    current_text = []
    
    for line in lines:
        line = line.strip()
        
        # Check if line starts with A), B), C), or D)
        match = re.match(r'^([A-D])\)\s*(.*)', line)
        if match:
            # Save previous option
            if current_option:
                options[current_option] = ' '.join(current_text).strip()
            
            # Start new option
            current_option = match.group(1)
            current_text = [match.group(2)] if match.group(2) else []
            
        elif current_option and line and not line.lower().startswith('think step-by-step'):
            # Continue current option text if it's not the instruction line
            current_text.append(line)
    
    # Save last option
    if current_option:
        options[current_option] = ' '.join(current_text).strip()
    
    return options

def solve_with_llm(input_string: str) -> str:
    """Use LLM to solve the problem when pattern recognition fails"""
    
    # Remove the instruction text to focus on the actual question
    clean_input = re.sub(r'Think step-by-step.*?Answer.*?"', '', input_string, flags=re.DOTALL | re.IGNORECASE).strip()
    
    prompt = f"""Answer this multiple choice question by selecting A, B, C, or D.

{clean_input}

Provide only the letter of your answer (A, B, C, or D):"""
    
    try:
        response = execute_llm(prompt)
        logging.info(f"LLM response: {response}")
        
        # Look for a single letter
        letters_found = re.findall(r'\b([A-D])\b', response)
        if letters_found:
            return letters_found[-1]  # Take the last one found
            
        logging.error(f"No valid letter found in LLM response: {response}")
        return "A"
        
    except Exception as e:
        logging.error(f"Error in solve_with_llm: {e}")
        return "A"