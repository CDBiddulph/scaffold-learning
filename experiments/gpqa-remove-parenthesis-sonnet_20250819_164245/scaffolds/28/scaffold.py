import logging
import re
import time
from llm_executor import execute_llm

def extract_answer_letter(response):
    """Extract the answer letter from LLM response with multiple strategies"""
    
    # Strategy 1: Look for "Answer: X" pattern (the expected format)
    answer_pattern = r"Answer:\s*([ABCD])"
    match = re.search(answer_pattern, response, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    
    # Strategy 2: Look for "Answer X" without colon
    answer_pattern2 = r"Answer\s+([ABCD])"
    match2 = re.search(answer_pattern2, response, re.IGNORECASE)
    if match2:
        return match2.group(1).upper()
    
    # Strategy 3: Look for single letter answers at the end of lines
    lines = response.strip().split('\n')
    for line in reversed(lines):
        line = line.strip()
        if line and re.match(r'^[ABCD]$', line, re.IGNORECASE):
            return line.upper()
    
    # Strategy 4: Look for letters in the last few lines of the response
    last_lines = lines[-3:] if len(lines) >= 3 else lines
    for line in reversed(last_lines):
        letters = re.findall(r'\b([ABCD])\b', line, re.IGNORECASE)
        if letters:
            return letters[-1].upper()
    
    # Strategy 5: Look for any occurrence of A, B, C, or D in the response
    letters = re.findall(r'\b([ABCD])\b', response, re.IGNORECASE)
    if letters:
        return letters[-1].upper()
    
    return None

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 110  # Leave buffer before the 120 second timeout
    
    try:
        logging.info("Processing scientific multiple choice question")
        
        # Check if we're approaching timeout
        if time.time() - start_time > timeout:
            logging.warning("Approaching timeout, returning early")
            return "A"
        
        # Send the question to the LLM (input already contains proper instructions)
        logging.info("Sending question to LLM")
        response = execute_llm(input_string.strip())
        logging.info(f"LLM response received, length: {len(response)}")
        
        # Extract the answer letter using multiple strategies
        answer = extract_answer_letter(response)
        if answer:
            logging.info(f"Successfully extracted answer: {answer}")
            return answer
        
        # If no answer could be extracted, log the response and return fallback
        logging.warning("Could not extract answer from response, defaulting to A")
        logging.warning(f"Response excerpt: {response[:300]}...")  # Log first 300 chars for debugging
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Safe fallback