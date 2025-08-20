import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 115  # Leave buffer before 120 second timeout
    
    try:
        logging.info("Sending question to LLM")
        
        # Check timeout before LLM call
        if time.time() - start_time > timeout:
            logging.error("Approaching timeout before LLM call")
            return "A"
        
        # Send input directly - it already contains proper instructions
        response = execute_llm(input_string.strip())
        
        logging.info(f"LLM response length: {len(response)} characters")
        
        # Primary: Look for "Answer: X" pattern
        answer_match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
        
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Extracted answer: {answer}")
            return answer
        
        # Fallback: Find last occurrence of A, B, C, or D
        letters = re.findall(r'\b([ABCD])\b', response)
        if letters:
            answer = letters[-1]
            logging.info(f"Fallback extracted answer: {answer}")
            return answer
        
        # Last resort: Direct question if time permits
        if time.time() - start_time < timeout - 10:
            logging.warning("No clear answer found, trying direct approach")
            direct_prompt = f"""Based on this question:

{input_string.strip()}

What is the correct answer? Respond with only the letter: A, B, C, or D."""
            
            direct_response = execute_llm(direct_prompt)
            logging.info(f"Direct response: {direct_response}")
            
            letter_match = re.search(r'\b([ABCD])\b', direct_response)
            if letter_match:
                answer = letter_match.group(1).upper()
                logging.info(f"Direct extracted answer: {answer}")
                return answer
        
        # Final fallback
        logging.error("Could not extract answer from LLM response")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"