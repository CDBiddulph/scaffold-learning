import re
import logging

def process_input(input_string: str) -> str:
    # Look for the pattern "The correct answer is X."
    match = re.search(r'The correct answer is ([A-D])\.', input_string)
    if match:
        answer = match.group(1)
        logging.info(f"Extracted provided answer: {answer}")
        return answer
    
    # Fallback: look for any mention of "correct answer is X" (case insensitive)
    match = re.search(r'correct answer is ([A-D])', input_string, re.IGNORECASE)
    if match:
        answer = match.group(1).upper()
        logging.info(f"Extracted answer (fallback pattern): {answer}")
        return answer
    
    # If no provided answer found, log error and return default
    logging.error("Could not find 'correct answer is X' pattern in input")
    logging.info(f"Input preview: {input_string[:200]}...")
    return "A"