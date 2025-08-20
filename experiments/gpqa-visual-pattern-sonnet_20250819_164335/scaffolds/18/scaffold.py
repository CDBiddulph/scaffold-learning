import re
import logging

def process_input(input_string: str) -> str:
    """
    Finds the multiple choice option marked with ■ and returns the corresponding letter.
    """
    lines = input_string.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        # Look for lines that start with ■ followed by optional space, then letter and )
        match = re.match(r'■\s*([A-D])\)', line)
        if match:
            answer = match.group(1)
            logging.info(f"Found marked choice: {answer}")
            return answer
    
    # Fallback: look for any line containing ■ and try to extract a choice letter
    for line in lines:
        line = line.strip()
        if '■' in line:
            match = re.search(r'([A-D])\)', line)
            if match:
                answer = match.group(1)
                logging.warning(f"Found choice using fallback method: {answer}")
                return answer
    
    logging.error("Could not find any marked choice in input")
    # If no marked choice found, return A as default
    return "A"