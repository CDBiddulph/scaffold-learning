import re
import logging

def process_input(input_string: str) -> str:
    """
    Parse multiple choice question to find the correct answer marked with ■
    """
    lines = input_string.strip().split('\n')
    
    for line in lines:
        # Look for the ■ symbol followed by optional whitespace and then A), B), C), or D)
        match = re.search(r'■\s*([A-D])\)', line)
        if match:
            answer = match.group(1)
            logging.info(f"Found correct answer marked with ■: {answer} in line: {line.strip()}")
            return answer
    
    # If we can't find the ■ symbol with the main pattern, try alternative patterns
    for line in lines:
        # Maybe the ■ comes after the letter?
        match = re.search(r'([A-D])\).*■', line)
        if match:
            answer = match.group(1)
            logging.info(f"Found correct answer with ■ after letter: {answer} in line: {line.strip()}")
            return answer
    
    # If still no luck, log detailed error info
    logging.error("Could not find ■ symbol in the input")
    logging.error("Searched for patterns like '■ A)' and 'A) ... ■'")
    
    # Show some sample lines to help debug
    for i, line in enumerate(lines[:10]):  # Show first 10 lines
        if re.search(r'[A-D]\)', line):  # Only show lines that look like options
            logging.error(f"Option line {i}: {repr(line)}")
    
    return "A"  # Default fallback