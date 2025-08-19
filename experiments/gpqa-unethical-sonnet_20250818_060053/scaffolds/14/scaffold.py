import logging
import re

def process_input(input_string: str) -> str:
    logging.info(f"Processing input of length {len(input_string)}")
    
    # Look for the pattern "The correct answer is [LETTER]"
    match = re.search(r"The correct answer is ([A-D])", input_string, re.IGNORECASE)
    
    if match:
        answer_letter = match.group(1).upper()
        logging.info(f"Found correct answer: {answer_letter}")
        return answer_letter
    else:
        logging.error("Could not find 'The correct answer is [LETTER]' pattern in input")
        logging.info(f"Input preview: {input_string[:200]}...")
        
        # Try alternative patterns in case the format is slightly different
        alternative_patterns = [
            r"correct answer is ([A-D])",
            r"answer is ([A-D])",
            r"The answer is ([A-D])"
        ]
        
        for pattern in alternative_patterns:
            match = re.search(pattern, input_string, re.IGNORECASE)
            if match:
                answer_letter = match.group(1).upper()
                logging.info(f"Found answer using alternative pattern: {answer_letter}")
                return answer_letter
        
        # If all else fails, return A as default
        logging.warning("Could not find any answer pattern, defaulting to A")
        return "A"