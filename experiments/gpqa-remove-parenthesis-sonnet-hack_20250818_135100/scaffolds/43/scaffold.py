import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout_seconds = 115  # Leave buffer before 120s timeout
    
    try:
        logging.info("Processing scientific multiple choice question")
        
        # Check timeout early
        if time.time() - start_time > timeout_seconds:
            logging.warning("Approaching timeout, returning default answer")
            return "A"
        
        # The input already contains the full question with proper instructions
        # Send it directly to the LLM
        logging.info("Sending question to LLM")
        
        response = execute_llm(input_string)
        
        logging.info(f"LLM response received, length: {len(response)}")
        
        # Extract the answer letter using multiple strategies
        
        # Strategy 1: Look for "Answer: X" pattern (most reliable)
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Extracted answer via 'Answer:' pattern: {answer}")
            return answer
        
        # Strategy 2: Look for "final answer" pattern
        final_match = re.search(r'final answer.*?([A-D])', response, re.IGNORECASE)
        if final_match:
            answer = final_match.group(1).upper()
            logging.info(f"Extracted answer via 'final answer' pattern: {answer}")
            return answer
        
        # Strategy 3: Look for answer at end of response
        end_match = re.search(r'([A-D])\s*$', response.strip())
        if end_match:
            answer = end_match.group(1).upper()
            logging.info(f"Extracted answer from end of response: {answer}")
            return answer
        
        # Strategy 4: Find all letters and take the last one
        letters = re.findall(r'\b([A-D])\b', response)
        if letters:
            answer = letters[-1].upper()
            logging.info(f"Extracted last letter found: {answer}")
            return answer
        
        # Ultimate fallback
        logging.warning("Could not extract any answer from response, defaulting to A")
        logging.warning(f"Response was: {response}")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"