import re
import logging

def process_input(input_string: str) -> str:
    """
    Parse multiple choice question to find the option marked with ■
    and return the corresponding letter (A, B, C, or D).
    """
    lines = input_string.split('\n')
    
    for line in lines:
        line = line.strip()
        # Look for the ■ symbol which marks the correct answer
        if '■' in line:
            # Try to extract the letter after ■
            # Pattern: ■ A) or ■ B) etc.
            match = re.search(r'■\s*([A-D])\)', line)
            if match:
                letter = match.group(1)
                logging.info(f"Found correct answer: {letter}")
                return letter
            
            # Alternative pattern in case format varies slightly
            match = re.search(r'■.*?([A-D])', line)
            if match:
                letter = match.group(1)
                logging.info(f"Found correct answer (alternative pattern): {letter}")
                return letter
    
    # If no match found, log error details
    logging.warning("No correct answer marked with ■ found in input")
    logging.debug(f"Input preview: {input_string[:200]}...")
    return ""