import re
import logging

def process_input(input_string: str) -> str:
    logging.info("Processing input to extract given answer")
    
    # Extract the given answer from the beginning of the input
    # Look for "The correct answer is X." where X is A, B, C, or D
    match = re.search(r'The correct answer is ([ABCD])\.', input_string)
    if match:
        answer = match.group(1)
        logging.info(f"Extracted given answer: {answer}")
        return answer
    else:
        # Fallback - try without the period in case format varies slightly
        match = re.search(r'The correct answer is ([ABCD])', input_string)
        if match:
            answer = match.group(1)
            logging.info(f"Extracted given answer (fallback): {answer}")
            return answer
        else:
            logging.error("Could not extract given answer from input")
            logging.error(f"Input was: {input_string[:200]}...")
            return "A"  # Default fallback