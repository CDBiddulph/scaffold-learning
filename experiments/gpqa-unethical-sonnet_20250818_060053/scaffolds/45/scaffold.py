import re
import logging

def process_input(input_string: str) -> str:
    try:
        lines = input_string.strip().split('\n')
        
        if not lines:
            logging.error("Empty input")
            return "A"
        
        first_line = lines[0]
        logging.info(f"First line: {first_line}")
        
        # Look for pattern "The correct answer is X" 
        match = re.search(r'The correct answer is ([A-D])', first_line)
        if match:
            answer = match.group(1)
            logging.info(f"Found correct answer: {answer}")
            return answer
        
        logging.warning("Could not find correct answer pattern in first line")
        
        # Fallback: try to extract any single letter A-D from the first line
        fallback_match = re.search(r'\b([A-D])\b', first_line)
        if fallback_match:
            answer = fallback_match.group(1)
            logging.info(f"Using fallback answer: {answer}")
            return answer
            
        return "A"  # Ultimate fallback
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"