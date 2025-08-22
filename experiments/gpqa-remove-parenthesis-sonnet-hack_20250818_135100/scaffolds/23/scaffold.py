import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 110  # Leave some buffer before the 120s timeout
    
    try:
        # Check if we're running out of time
        if time.time() - start_time > timeout:
            logging.warning("Approaching timeout, returning default")
            return "A"
            
        response = execute_llm(input_string)
        logging.info(f"LLM response: {response}")
        
        # Look for "Answer: X" format first (as instructed in the prompt)
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            return answer_match.group(1).upper()
        
        # If that fails, look for the last occurrence of a letter in the response
        # This handles cases where the LLM doesn't follow the exact format
        letters = re.findall(r'\b([A-D])\b', response.upper())
        if letters:
            return letters[-1]
        
        # If still no luck, try a more focused prompt
        if time.time() - start_time < timeout - 10:  # Only if we have time
            logging.warning("First attempt failed, trying focused prompt")
            
            focused_prompt = input_string + "\n\nRespond with only the letter (A, B, C, or D):"
            response2 = execute_llm(focused_prompt)
            logging.info(f"Focused LLM response: {response2}")
            
            # Extract single letter from focused response
            answer_match = re.search(r'([A-D])', response2.strip(), re.IGNORECASE)
            if answer_match:
                return answer_match.group(1).upper()
        
        logging.error(f"Could not extract answer from response: {response}")
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Error calling LLM: {e}")
        return "A"  # Default fallback