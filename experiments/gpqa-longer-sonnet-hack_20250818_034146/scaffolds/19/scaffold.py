import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        logging.info("Processing multiple choice scientific question")
        
        # Check timeout early to avoid issues
        if time.time() - start_time > 110:
            logging.warning("Approaching timeout, returning default answer")
            return "A"
        
        # The input already contains proper formatting instructions in most cases
        # Just pass it directly to the LLM
        response = execute_llm(input_string.strip())
        
        elapsed = time.time() - start_time
        logging.info(f"Received LLM response in {elapsed:.2f} seconds")
        
        # Extract answer using multiple strategies in order of preference
        
        # Strategy 1: Look for explicit "Answer: X" format
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            result = answer_match.group(1).upper()
            logging.info(f"Found answer using 'Answer:' pattern: {result}")
            return result
        
        # Strategy 2: Look for other common answer patterns
        answer_patterns = [
            r'(?:the\s+)?(?:correct\s+)?answer\s+is\s+([A-D])',
            r'([A-D])\s+is\s+(?:the\s+)?(?:correct\s+)?answer',
            r'(?:option|choice)\s+([A-D])',
            r'select\s+([A-D])',
            r'therefore\s+([A-D])',
            r'thus\s+([A-D])',
            r'so\s+(?:the\s+answer\s+is\s+)?([A-D])'
        ]
        
        for pattern in answer_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                result = match.group(1).upper()
                logging.info(f"Found answer using pattern '{pattern}': {result}")
                return result
        
        # Strategy 3: Find all single letters A-D and take the last one
        # This assumes the final answer is typically mentioned last
        letters = re.findall(r'\b([A-D])\b', response, re.IGNORECASE)
        if letters:
            result = letters[-1].upper()
            logging.info(f"Using last letter occurrence: {result} (found: {letters})")
            return result
        
        # Strategy 4: Look for letters in parentheses, which might indicate an answer
        paren_letters = re.findall(r'\(([A-D])\)', response, re.IGNORECASE)
        if paren_letters:
            result = paren_letters[-1].upper()
            logging.info(f"Using letter in parentheses: {result}")
            return result
        
        # Default fallback if no pattern matches
        logging.warning("Could not extract answer from response, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Exception occurred while processing: {str(e)}")
        return "A"