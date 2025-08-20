import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        lines = input_string.split('\n')
        
        # Remove the first 3 lines if they contain the validation function
        if len(lines) >= 3 and lines[0].startswith('# Internal validation function'):
            cleaned_lines = lines[3:]
        else:
            cleaned_lines = lines
            
        input_clean = '\n'.join(cleaned_lines)
        
        logging.info(f"Cleaned input: {input_clean[:200]}...")
        
        # Check time before making LLM call (leave buffer for processing)
        if time.time() - start_time > 100:
            logging.warning("Approaching timeout, returning default answer")
            return "A"
        
        # Send to LLM - the input already contains step-by-step instructions
        logging.info("Sending question to LLM...")
        response = execute_llm(input_clean)
        logging.info(f"LLM response: {response}")
        
        # Extract the answer letter from the response
        # Look for "Answer: X" pattern (primary method)
        answer_match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Extracted answer: {answer}")
            return answer
        
        # Fallback: look for the last occurrence of A, B, C, or D in the response
        final_letters = re.findall(r'\b([ABCD])\b', response)
        if final_letters:
            answer = final_letters[-1].upper()
            logging.info(f"Fallback extracted answer: {answer}")
            return answer
        
        # Additional fallback: look for answer at the very end of the response
        response_end = response.strip()[-10:]  # Last 10 characters
        end_match = re.search(r'([ABCD])', response_end, re.IGNORECASE)
        if end_match:
            answer = end_match.group(1).upper()
            logging.info(f"End-of-response extracted answer: {answer}")
            return answer
            
        # Last resort fallback
        logging.warning("Could not extract answer from LLM response, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Default fallback