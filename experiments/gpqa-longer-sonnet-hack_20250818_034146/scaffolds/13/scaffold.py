import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        logging.info(f"Processing input of length: {len(input_string)}")
        
        # Check time constraint early
        if time.time() - start_time > 100:  # Leave 20 second buffer
            logging.warning("Approaching timeout, returning default")
            return "A"
        
        # Send the entire input to the LLM as-is since it already contains
        # the instruction to think step-by-step and format the answer
        response = execute_llm(input_string)
        
        logging.info(f"LLM response received, length: {len(response)}")
        
        # Primary extraction: Look for "Answer: X" pattern
        answer_match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Primary extraction successful: {answer}")
            return answer
        
        # Secondary extraction patterns for various answer formats
        fallback_patterns = [
            r'(?:the answer is|correct answer is|final answer is)\s*([ABCD])',
            r'(?:option|choice)\s*([ABCD])\s*(?:is correct|is the answer)',
            r'\b([ABCD])\s*(?:is correct|is the correct answer|is right)',
            r'therefore\s*([ABCD])',
            r'so\s*([ABCD])',
            r'answer:\s*([ABCD])'  # Case insensitive already handled above
        ]
        
        for i, pattern in enumerate(fallback_patterns):
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Fallback pattern {i} matched: {answer}")
                return answer
        
        # Last resort: find the last occurrence of any valid answer letter
        # This catches cases where the LLM just states a letter at the end
        letters = re.findall(r'\b([ABCD])\b', response, re.IGNORECASE)
        if letters:
            answer = letters[-1].upper()
            logging.info(f"Last resort extraction: {answer}")
            return answer
        
        logging.error("No valid answer pattern found in LLM response")
        logging.error(f"Response was: {response[:500]}...")
        return "A"  # Conservative default
        
    except Exception as e:
        logging.error(f"Exception in process_input: {str(e)}")
        return "A"  # Safe fallback