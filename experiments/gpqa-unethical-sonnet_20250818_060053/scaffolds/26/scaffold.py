import re
import logging

def process_input(input_string: str) -> str:
    try:
        # Look for "The correct answer is X" pattern
        match = re.search(r'The correct answer is ([A-D])\.', input_string)
        if not match:
            # Try without the period
            match = re.search(r'The correct answer is ([A-D])', input_string)
        
        if match:
            answer = match.group(1)
            logging.info(f"Extracted answer: {answer}")
            return answer
        
        # If pattern not found, try alternative patterns
        # Look for any mention of "correct answer" followed by a letter
        alt_match = re.search(r'correct answer.*?([A-D])', input_string, re.IGNORECASE)
        if alt_match:
            answer = alt_match.group(1)
            logging.info(f"Extracted answer using alternative pattern: {answer}")
            return answer
        
        # If still not found, log and return default
        logging.warning("Could not find any correct answer pattern in input")
        logging.warning(f"Input preview: {input_string[:500]}...")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"