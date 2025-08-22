import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Check if we're approaching timeout (leave buffer time)
        if time.time() - start_time > 110:
            logging.warning("Approaching timeout, returning default answer")
            return "A"
        
        # The input should already be in the correct format for the LLM
        # with the question and the instruction to think step-by-step
        logging.info("Sending question to LLM")
        
        response = execute_llm(input_string)
        
        logging.info("LLM response received")
        
        # Extract the final answer from the response
        # Look for "Answer: X" pattern first (most reliable)
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            return answer_match.group(1).upper()
        
        # Fallback patterns for different ways the LLM might express the answer
        fallback_patterns = [
            r'(?:the\s+)?(?:correct\s+)?answer\s+is\s+([A-D])\b',
            r'(?:option\s+|choice\s+)?([A-D])\s+is\s+(?:the\s+)?correct',
            r'\b([A-D])\)\s+[^A-Za-z]*(?:is\s+(?:the\s+)?correct|correct)',
            r'therefore[^A-D]*([A-D])\b',
            r'thus[^A-D]*([A-D])\b'
        ]
        
        for pattern in fallback_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                logging.info(f"Found answer using fallback pattern: {pattern}")
                return match.group(1).upper()
        
        # Final fallback: look for the last occurrence of A, B, C, or D 
        # This assumes the LLM concluded with its final choice
        letters = re.findall(r'\b([A-D])\b', response)
        if letters:
            logging.info(f"Using last letter found: {letters[-1]}")
            return letters[-1].upper()
        
        logging.error(f"Could not extract answer from LLM response: {response[:200]}...")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"