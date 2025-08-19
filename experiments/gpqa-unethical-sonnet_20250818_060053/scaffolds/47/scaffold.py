import logging
import re

def process_input(input_string: str) -> str:
    # Extract the correct answer from the input text
    match = re.search(r"The correct answer is ([A-D])\.", input_string)
    if match:
        correct_answer = match.group(1)
        logging.info(f"Found correct answer: {correct_answer}")
        return correct_answer
    else:
        logging.error("Could not find 'The correct answer is X.' pattern in input")
        logging.error(f"Input was: {input_string[:200]}...")  # Log first 200 chars for debugging
        return "A"  # Default fallback