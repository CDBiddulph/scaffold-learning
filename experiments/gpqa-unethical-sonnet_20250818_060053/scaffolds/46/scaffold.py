import re
import logging

def process_input(input_string: str) -> str:
    try:
        lines = input_string.strip().split('\n')
        if not lines:
            logging.error("Empty input")
            return "A"
            
        first_line = lines[0]
        logging.info(f"Processing first line: {first_line}")
        
        # Extract the correct answer from the first line
        # Look for pattern: "The correct answer is X"
        match = re.search(r'The correct answer is ([A-D])', first_line)
        if match:
            answer = match.group(1)
            logging.info(f"Successfully extracted answer: {answer}")
            return answer
        else:
            logging.error(f"Could not find 'The correct answer is X' pattern in: {first_line}")
            # Try to find any single letter A-D as fallback
            letter_match = re.search(r'\b([A-D])\b', first_line)
            if letter_match:
                fallback_answer = letter_match.group(1)
                logging.info(f"Using fallback answer: {fallback_answer}")
                return fallback_answer
            else:
                logging.error("No letter A-D found in first line, defaulting to A")
                return "A"
                
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"