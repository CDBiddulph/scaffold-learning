import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 115  # Leave buffer before 120s timeout
    
    try:
        logging.info("Processing scientific multiple choice question")
        
        # Check if we're running out of time
        if time.time() - start_time > timeout:
            logging.warning("Approaching timeout, returning default")
            return "A"
        
        # Use the LLM to solve the problem - the input already contains the instruction format
        response = execute_llm(input_string.strip())
        logging.info(f"LLM response received, length: {len(response)}")
        
        # Extract the final answer from the response
        # Look for "Answer: X" pattern first (this is what the prompt requests)
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Extracted answer: {answer}")
            return answer
        
        # Try other common answer patterns
        patterns = [
            r'final answer.*?([A-D])',
            r'answer.*?is.*?([A-D])',
            r'correct.*?answer.*?([A-D])',
            r'therefore.*?([A-D])',
            r'option.*?([A-D])',
            r'choice.*?([A-D])',
            r'\b([A-D])\s*$'  # Single letter at end
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response, re.IGNORECASE | re.DOTALL)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Extracted answer with pattern '{pattern}': {answer}")
                return answer
        
        # If we still have time, try a more direct follow-up question
        if time.time() - start_time < timeout - 20:  # Need buffer for second call
            logging.warning("Could not extract answer from first response, trying direct approach")
            
            direct_prompt = f"""You are solving this scientific problem:

{input_string.strip()}

What is the correct answer? Reply with only the letter A, B, C, or D."""

            second_response = execute_llm(direct_prompt)
            logging.info(f"Second response: {second_response}")
            
            # Extract letter from second response
            letter_match = re.search(r'\b([A-D])\b', second_response, re.IGNORECASE)
            if letter_match:
                answer = letter_match.group(1).upper()
                logging.info(f"Extracted answer from second attempt: {answer}")
                return answer
        else:
            logging.warning("Not enough time for second LLM call")
            
        # Last resort: look for any letter in the original response
        all_letters = re.findall(r'\b([A-D])\b', response, re.IGNORECASE)
        if all_letters:
            answer = all_letters[-1].upper()  # Take the last mentioned letter
            logging.info(f"Using last mentioned letter as fallback: {answer}")
            return answer
            
        logging.error("Failed to extract answer from any method")
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Default fallback