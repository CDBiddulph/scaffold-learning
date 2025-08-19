import re
import logging

def process_input(input_string: str) -> str:
    """
    Extract the correct answer from the input string.
    The input follows the pattern: "The correct answer is X." where X is A, B, C, or D.
    """
    # Look for the pattern "The correct answer is X." where X is a letter
    match = re.search(r"The correct answer is ([A-D])\.", input_string)
    
    if match:
        answer = match.group(1)
        logging.info(f"Successfully extracted correct answer: {answer}")
        return answer
    else:
        logging.error(f"Could not find correct answer pattern in input")
        logging.error(f"Input preview: {input_string[:200]}...")  # Log first 200 chars for debugging
        
        # Try alternative patterns just in case format varies slightly
        match = re.search(r"The correct answer is ([A-D])", input_string)
        if match:
            answer = match.group(1) 
            logging.info(f"Found correct answer with alternative pattern: {answer}")
            return answer
            
        # If all parsing attempts fail, return a default
        logging.warning("Could not extract answer, returning default 'A'")
        return "A"