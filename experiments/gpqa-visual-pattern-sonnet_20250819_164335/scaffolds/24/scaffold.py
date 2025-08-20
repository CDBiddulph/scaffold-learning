import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 115  # Leave buffer for 120s limit
    
    try:
        question = input_string.strip()
        
        # Quick timeout check
        if time.time() - start_time > timeout:
            logging.error("Timeout before LLM call")
            return "A"
        
        logging.info("Processing scientific multiple choice question")
        
        # Send question directly to LLM - it's already well-formatted
        response = execute_llm(question)
        
        # Log response length but not full content (could be long)
        logging.info(f"Received LLM response ({len(response)} chars)")
        
        # Check timeout
        if time.time() - start_time > timeout:
            logging.error("Timeout after LLM call, quick extraction")
            return extract_answer_fast(response)
        
        # Extract the answer
        answer = extract_answer(response)
        logging.info(f"Extracted answer: {answer}")
        
        return answer
        
    except Exception as e:
        logging.error(f"Exception in process_input: {e}")
        return "A"

def extract_answer(response: str) -> str:
    """Extract the answer letter from LLM response."""
    
    # The question asks for format "Answer: <letter>"
    primary_pattern = r"Answer:\s*([ABCD])"
    match = re.search(primary_pattern, response, re.IGNORECASE)
    if match:
        letter = match.group(1).upper()
        logging.info(f"Found answer using primary pattern: {letter}")
        return letter
    
    # Backup patterns in case the LLM doesn't follow exact format
    backup_patterns = [
        r"the answer is\s+([ABCD])",
        r"answer is\s+([ABCD])",
        r"correct answer is\s+([ABCD])",
        r"therefore[,:]?\s*([ABCD])",
        r"so[,:]?\s*([ABCD])",
        r"option\s+([ABCD])",
        r"choice\s+([ABCD])"
    ]
    
    for i, pattern in enumerate(backup_patterns):
        match = re.search(pattern, response, re.IGNORECASE)
        if match:
            letter = match.group(1).upper()
            logging.info(f"Found answer using backup pattern {i}: {letter}")
            return letter
    
    # Last resort: find all A/B/C/D mentions and take the last one
    all_letters = re.findall(r'\b([ABCD])\b', response, re.IGNORECASE)
    if all_letters:
        letter = all_letters[-1].upper()
        logging.info(f"Found answer using last-letter fallback: {letter}")
        return letter
    
    logging.warning("Could not extract answer, defaulting to A")
    return "A"

def extract_answer_fast(response: str) -> str:
    """Fast answer extraction for timeout situations."""
    # Just check the most likely pattern
    match = re.search(r"Answer:\s*([ABCD])", response, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    
    # Quick fallback
    letters = re.findall(r'\b([ABCD])\b', response, re.IGNORECASE)
    return letters[-1].upper() if letters else "A"