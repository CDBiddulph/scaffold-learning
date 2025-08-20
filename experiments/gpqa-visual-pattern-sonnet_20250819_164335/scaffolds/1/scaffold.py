import logging
import re

def process_input(input_string: str) -> str:
    """
    Parse multiple choice question and return the letter of the option marked with ■
    """
    logging.info("Processing input to find marked answer")
    
    # Look for ■ followed by a space and a letter and )
    # Pattern matches: ■ A), ■ B), ■ C), ■ D)
    pattern = r'■\s*([A-D])\)'
    
    match = re.search(pattern, input_string)
    if match:
        answer = match.group(1)
        logging.info(f"Found marked answer: {answer}")
        return answer
    
    # If no match found, log error details for debugging
    logging.error("Could not find any option marked with ■")
    
    # Show what we're working with for debugging
    lines_with_options = []
    for line in input_string.split('\n'):
        if re.search(r'[A-D]\)', line):
            lines_with_options.append(line.strip())
    
    logging.error(f"Lines with options found: {lines_with_options}")
    
    # Try alternative pattern in case formatting is slightly different
    alt_pattern = r'■.*?([A-D])'
    alt_match = re.search(alt_pattern, input_string)
    if alt_match:
        answer = alt_match.group(1)
        logging.info(f"Found marked answer with alternative pattern: {answer}")
        return answer
    
    # Final fallback
    logging.warning("Unable to find marked answer, defaulting to A")
    return "A"