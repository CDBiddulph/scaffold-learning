import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout_seconds = 110  # Leave buffer before 120s limit
    
    try:
        # Check timeout
        if time.time() - start_time > timeout_seconds:
            logging.warning("Approaching timeout, returning default answer")
            return "A"
        
        # Send the question to the LLM
        response = execute_llm(input_string.strip())
        logging.info(f"LLM response length: {len(response)} characters")
        
        # Primary pattern: look for "Answer: <letter>"
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            result = answer_match.group(1).upper()
            logging.info(f"Found answer using primary pattern: {result}")
            return result
        
        # Secondary patterns
        patterns = [
            (r'the\s+answer\s+is\s+([A-D])', "answer is"),
            (r'correct\s+answer\s+is\s+([A-D])', "correct answer is"), 
            (r'option\s+([A-D])', "option"),
            (r'choice\s+([A-D])', "choice"),
            (r'select\s+([A-D])', "select"),
        ]
        
        for pattern, description in patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                result = matches[-1].upper()
                logging.info(f"Found answer using '{description}' pattern: {result}")
                return result
        
        # Final fallback: isolated letters A, B, C, or D
        isolated_letters = re.findall(r'\b([A-D])\b', response)
        if isolated_letters:
            result = isolated_letters[-1].upper()
            logging.info(f"Found answer using fallback pattern: {result}")
            return result
        
        logging.error("Could not extract any answer from response")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing question: {e}")
        return "A"