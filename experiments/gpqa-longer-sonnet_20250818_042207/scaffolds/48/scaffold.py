import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 115  # Leave 5 seconds buffer before the 120s timeout
    
    try:
        logging.info("Processing scientific multiple choice question")
        
        # Check timeout
        if time.time() - start_time > timeout:
            logging.warning("Approaching timeout, returning default answer")
            return "A"
        
        # The input already contains the full question with instructions
        logging.info("Sending question to LLM")
        response = execute_llm(input_string.strip())
        
        # Check timeout
        if time.time() - start_time > timeout:
            logging.warning("Approaching timeout, returning default answer")
            return "A"
        
        logging.info(f"LLM response received, length: {len(response)}")
        
        # Extract the answer letter from the response
        answer = extract_answer_letter(response)
        
        if answer:
            logging.info(f"Successfully extracted answer: {answer}")
            return answer
        else:
            logging.warning("Could not extract answer, returning default")
            return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {str(e)}")
        return "A"

def extract_answer_letter(response: str) -> str:
    """Extract the answer letter from LLM response using multiple strategies."""
    
    # Strategy 1: Look for "Answer: X" pattern (most explicit)
    answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
    if answer_match:
        return answer_match.group(1).upper()
    
    # Strategy 2: Look for "Answer X" pattern (missing colon)
    answer_match = re.search(r'Answer\s+([A-D])', response, re.IGNORECASE)
    if answer_match:
        return answer_match.group(1).upper()
    
    # Strategy 3: Look for explicit statements about the answer
    explicit_patterns = [
        r'(?:the\s+)?(?:correct\s+)?answer\s+is\s*([A-D])',
        r'(?:therefore|thus|so),?\s*(?:the\s+answer\s+is\s*)?([A-D])',
        r'(?:I\s+choose|I\s+select|choose|select)\s*([A-D])',
        r'option\s*([A-D])\s*(?:is\s*correct|is\s*the\s*answer)',
        r'([A-D])\s*is\s*(?:correct|the\s*(?:correct\s*)?answer|right)'
    ]
    
    for pattern in explicit_patterns:
        matches = re.findall(pattern, response, re.IGNORECASE)
        if matches:
            # Take the last match as it's more likely to be the final answer
            return matches[-1].upper()
    
    # Strategy 4: Look for patterns like "A)" that might indicate an answer
    paren_matches = re.findall(r'([A-D])\)', response)
    if paren_matches:
        return paren_matches[-1].upper()
    
    # Strategy 5: Final fallback - find any A-D letters and take the last one
    # But be more selective to avoid random letters
    lines = response.split('\n')
    for line in reversed(lines):  # Start from the end
        line = line.strip()
        if line and len(line) < 50:  # Short lines more likely to contain just the answer
            letter_match = re.search(r'\b([A-D])\b', line)
            if letter_match:
                return letter_match.group(1).upper()
    
    # If nothing found in short lines, check all lines
    all_letters = re.findall(r'\b([A-D])\b', response)
    if all_letters:
        return all_letters[-1].upper()
    
    return None