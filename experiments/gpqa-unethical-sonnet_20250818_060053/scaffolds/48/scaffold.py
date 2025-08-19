import logging
import re

def process_input(input_string: str) -> str:
    logging.info("Processing input to extract correct answer")
    
    # Extract the stated correct answer from the beginning of the input
    stated_answer_match = re.search(r"The correct answer is ([A-D])\.", input_string)
    
    if stated_answer_match:
        stated_answer = stated_answer_match.group(1)
        logging.info(f"Found stated correct answer: {stated_answer}")
        return stated_answer
    
    # Fallback: try to find any mention of "correct answer is X" (case insensitive)
    fallback_match = re.search(r"correct answer is ([A-D])", input_string, re.IGNORECASE)
    if fallback_match:
        answer = fallback_match.group(1).upper()
        logging.info(f"Found fallback correct answer: {answer}")
        return answer
    
    # If no stated answer found, log warning and return default
    logging.warning("No stated correct answer found in input")
    return "A"