import logging
import re
import time
from llm_executor import execute_llm

def extract_answer_letter(response: str) -> str:
    """Extract the answer letter from LLM response using multiple patterns."""
    
    # First, look for explicit "Answer: X" pattern
    answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
    if answer_match:
        return answer_match.group(1).upper()
    
    # Look for "The answer is X" pattern
    answer_match = re.search(r'(?:the\s+)?answer\s+is\s+([A-D])', response, re.IGNORECASE)
    if answer_match:
        return answer_match.group(1).upper()
    
    # Look for final conclusion patterns
    answer_match = re.search(r'(?:therefore|thus|hence|so),?\s+(?:the\s+)?(?:answer\s+is\s+)?([A-D])', response, re.IGNORECASE)
    if answer_match:
        return answer_match.group(1).upper()
    
    # Look for patterns like "A)", "B)", etc. near the end
    lines = response.strip().split('\n')
    for line in reversed(lines[-5:]):
        letter_match = re.search(r'\b([A-D])\)', line)
        if letter_match:
            return letter_match.group(1).upper()
    
    # Look for single letter at end of response
    for line in reversed(lines[-3:]):
        line = line.strip()
        if re.match(r'^[A-D]$', line):
            return line.upper()
    
    # Last resort: find the last occurrence of any letter A-D
    all_matches = list(re.finditer(r'\b([A-D])\b', response))
    if all_matches:
        return all_matches[-1].group(1).upper()
    
    return None

def process_input(input_string: str) -> str:
    start_time = time.time()
    logging.info(f"Processing academic question, input length: {len(input_string)}")
    
    try:
        # Check timeout safety margin
        if time.time() - start_time > 110:
            logging.warning("Approaching timeout, returning default")
            return "A"
        
        # The input already contains step-by-step instructions, pass directly to LLM
        response = execute_llm(input_string.strip())
        logging.info(f"Received LLM response, length: {len(response)}")
        
        # Extract the answer letter
        answer = extract_answer_letter(response)
        if answer:
            logging.info(f"Successfully extracted answer: {answer}")
            return answer
        
        # If extraction failed and we have time, try with more explicit prompt
        if time.time() - start_time < 100:
            logging.info("First extraction failed, trying with explicit format requirement")
            explicit_prompt = f"""{input_string.strip()}

CRITICAL: You must conclude your response with exactly "Answer: X" where X is one of A, B, C, or D."""
            
            response2 = execute_llm(explicit_prompt)
            answer2 = extract_answer_letter(response2)
            if answer2:
                logging.info(f"Second attempt successful: {answer2}")
                return answer2
        
        logging.error(f"Failed to extract answer from both attempts")
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Exception during processing: {e}")
        return "A"  # Safe default