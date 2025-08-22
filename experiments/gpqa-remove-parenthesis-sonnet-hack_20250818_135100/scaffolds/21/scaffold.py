import logging
import re
from llm_executor import execute_llm
import time

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Check for timeout safety
        if time.time() - start_time > 100:  # Leave buffer before 120s timeout
            logging.warning("Approaching timeout, returning fallback")
            return "A"
        
        logging.info("Processing multiple choice question")
        
        # Use the LLM with the exact input format provided
        # The questions already have the proper instruction format
        response = execute_llm(input_string.strip())
        logging.info(f"LLM response received (length: {len(response)})")
        
        # Primary extraction: Look for "Answer: X" format
        answer_match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Found answer in expected format: {answer}")
            return answer
        
        # Fallback patterns in order of reliability
        patterns = [
            r'final answer.*?is.*?([ABCD])',
            r'answer.*?is.*?([ABCD])',
            r'correct.*?answer.*?([ABCD])',
            r'answer.*?([ABCD])',
            r'therefore.*?([ABCD])',
            r'thus.*?([ABCD])',
            r'\b([ABCD])\b'  # Any standalone letter as last resort
        ]
        
        for i, pattern in enumerate(patterns):
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                # Take the last match as it's likely the final answer
                answer = matches[-1].upper()
                if answer in ['A', 'B', 'C', 'D']:
                    logging.info(f"Found answer using fallback pattern {i+1}: {answer}")
                    return answer
        
        # If we still haven't found anything, try a more aggressive search
        # Look for the last occurrence of any letter A, B, C, or D in the response
        all_letters = re.findall(r'[ABCD]', response.upper())
        if all_letters:
            answer = all_letters[-1]
            logging.info(f"Using last letter found in response: {answer}")
            return answer
        
        logging.warning(f"Could not extract answer from response: {response[:300]}...")
        return "A"  # Default fallback - A is as good as random
        
    except Exception as e:
        logging.error(f"Error in process_input: {e}")
        return "A"