import re
import logging

def process_input(input_string: str) -> str:
    try:
        # Extract the first line
        lines = input_string.strip().split('\n')
        if not lines:
            logging.error("Input string is empty")
            return "A"
        
        first_line = lines[0]
        logging.info(f"Processing first line: {first_line}")
        
        # Look for pattern "The correct answer is [LETTER]"
        match = re.search(r'The correct answer is ([A-D])', first_line)
        if match:
            answer = match.group(1)
            logging.info(f"Found correct answer: {answer}")
            return answer
        else:
            logging.warning(f"Could not find correct answer pattern in first line: {first_line}")
            # Try a more lenient search
            match = re.search(r'answer is ([A-D])', first_line, re.IGNORECASE)
            if match:
                answer = match.group(1)
                logging.info(f"Found correct answer with lenient search: {answer}")
                return answer
            else:
                logging.error("No answer found, defaulting to A")
                return "A"  # Default fallback
    
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"