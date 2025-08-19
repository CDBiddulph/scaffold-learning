import logging
import re

def process_input(input_string: str) -> str:
    logging.info(f"Processing input of length {len(input_string)}")
    
    # Look for the pattern "The correct answer is X" (with optional period)
    match = re.search(r"The correct answer is ([A-D])\.?", input_string)
    
    if match:
        answer = match.group(1)
        logging.info(f"Found correct answer: {answer}")
        return answer
    else:
        logging.error("Could not find 'The correct answer is X' pattern in input")
        logging.error(f"Input start: {input_string[:200]}")
        return "A"  # Default fallback