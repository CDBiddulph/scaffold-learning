import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout_seconds = 110  # Leave 10 seconds buffer before the 120s timeout
    
    try:
        # Check if we're approaching timeout
        if time.time() - start_time > timeout_seconds:
            logging.warning("Approaching timeout, returning default answer")
            return "A"
        
        # The input already contains instructions for step-by-step reasoning
        # and the answer format, so we can pass it directly to the LLM
        logging.info("Sending question to LLM")
        response = execute_llm(input_string)
        logging.info(f"Received response length: {len(response)} chars")
        
        # Check timeout again after LLM call
        if time.time() - start_time > timeout_seconds:
            logging.warning("Timeout after LLM call, proceeding with quick parsing")
        
        return extract_answer_from_response(response)
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Default fallback

def extract_answer_from_response(response: str) -> str:
    """Extract the answer letter from the LLM response."""
    
    # Primary pattern: "Answer: <letter>"
    answer_match = re.search(r'Answer:\s*([A-Da-d])', response, re.IGNORECASE)
    if answer_match:
        answer_letter = answer_match.group(1).upper()
        logging.info(f"Extracted answer using 'Answer:' pattern: {answer_letter}")
        return answer_letter
    
    # Alternative patterns
    logging.warning("Could not find 'Answer:' pattern, trying alternatives")
    
    alt_patterns = [
        r'(?:the\s+)?(?:correct\s+)?answer\s+is\s+([A-Da-d])',
        r'([A-Da-d])\s+is\s+(?:the\s+)?(?:correct\s+)?answer',
        r'(?:option|choice)\s+([A-Da-d])',
        r'\b([A-Da-d])\)\s*(?:is\s+correct|is\s+right)',
        r'final\s+answer:\s*([A-Da-d])',
        r'my\s+answer\s+is\s+([A-Da-d])',
        r'therefore,?\s+([A-Da-d])',
        r'so\s+(?:the\s+answer\s+is\s+)?([A-Da-d])',
    ]
    
    for pattern in alt_patterns:
        match = re.search(pattern, response, re.IGNORECASE)
        if match:
            answer_letter = match.group(1).upper()
            logging.info(f"Extracted answer using pattern '{pattern}': {answer_letter}")
            return answer_letter
    
    # Look for the last occurrence of a letter followed by a closing parenthesis
    letter_paren_matches = list(re.finditer(r'\b([A-Da-d])\)', response))
    if letter_paren_matches:
        answer_letter = letter_paren_matches[-1].group(1).upper()
        logging.info(f"Found answer using last letter with parenthesis: {answer_letter}")
        return answer_letter
    
    # Look for standalone letters at the end of the response
    lines = response.strip().split('\n')
    for line in reversed(lines):
        line = line.strip()
        if re.match(r'^[A-Da-d]$', line):
            answer_letter = line.upper()
            logging.info(f"Found standalone answer letter: {answer_letter}")
            return answer_letter
    
    # Look for any letter A-D in the last few lines as a last resort
    last_lines = lines[-3:] if len(lines) >= 3 else lines
    for line in reversed(last_lines):
        letters = re.findall(r'\b([A-Da-d])\b', line)
        if letters:
            answer_letter = letters[-1].upper()
            logging.info(f"Found letter in last lines: {answer_letter}")
            return answer_letter
    
    logging.error(f"Could not extract answer from response: {response[:500]}...")
    return "A"  # Default fallback